"""Start Streamlit locally and expose it through the configured Preview port.

The bridge serves the tracked route manifest at /manus-routes.json and proxies
browser HTTP and WebSocket traffic to Streamlit on an internal loopback port.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType, web

ROOT = Path(__file__).resolve().parent
INTERNAL_HOST = "127.0.0.1"
INTERNAL_PORT = 8501
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
    "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


def forwarded_headers(headers: Any) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP and not key.lower().startswith("sec-websocket-")
    }


async def route_manifest(_: web.Request) -> web.FileResponse:
    return web.FileResponse(ROOT / "public" / "manus-routes.json")


async def proxy_request(request: web.Request) -> web.StreamResponse:
    client: ClientSession = request.app["client"]
    target = f"http://{INTERNAL_HOST}:{INTERNAL_PORT}{request.rel_url}"
    if request.headers.get("Upgrade", "").casefold() == "websocket":
        return await proxy_websocket(request, client, target)

    try:
        async with client.request(
            request.method,
            target,
            headers=forwarded_headers(request.headers),
            data=await request.read(),
            allow_redirects=False,
        ) as upstream:
            body = await upstream.read()
            headers = {
                key: value
                for key, value in upstream.headers.items()
                if key.lower() not in HOP_BY_HOP and key.lower() != "content-encoding"
            }
            return web.Response(body=body, status=upstream.status, headers=headers)
    except (ClientError, asyncio.TimeoutError) as exc:
        return web.json_response(
            {"error": "CampusMate's local Streamlit process is not ready.", "detail": str(exc)},
            status=502,
        )


async def proxy_websocket(
    request: web.Request,
    client: ClientSession,
    target: str,
) -> web.WebSocketResponse:
    ws_target = "ws" + target[4:]
    requested_protocols = [
        part.strip()
        for part in request.headers.get("Sec-WebSocket-Protocol", "").split(",")
        if part.strip()
    ]

    try:
        async with client.ws_connect(
            ws_target,
            headers=forwarded_headers(request.headers),
            protocols=requested_protocols,
            autoping=True,
            heartbeat=25,
        ) as upstream_socket:
            selected_protocol = upstream_socket.protocol
            browser_socket = web.WebSocketResponse(
                protocols=[selected_protocol] if selected_protocol else (),
                autoping=True,
                heartbeat=25,
            )
            await browser_socket.prepare(request)

            async def browser_to_upstream() -> None:
                async for message in browser_socket:
                    if message.type == WSMsgType.TEXT:
                        await upstream_socket.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await upstream_socket.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            async def upstream_to_browser() -> None:
                async for message in upstream_socket:
                    if message.type == WSMsgType.TEXT:
                        await browser_socket.send_str(message.data)
                    elif message.type == WSMsgType.BINARY:
                        await browser_socket.send_bytes(message.data)
                    elif message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                        break

            tasks = {
                asyncio.create_task(browser_to_upstream()),
                asyncio.create_task(upstream_to_browser()),
            }
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)
            if not upstream_socket.closed:
                await upstream_socket.close()
            if not browser_socket.closed:
                await browser_socket.close()
            return browser_socket
    except (ClientError, asyncio.TimeoutError, RuntimeError) as exc:
        failed_socket = web.WebSocketResponse()
        await failed_socket.prepare(request)
        await failed_socket.close(message=f"Streamlit websocket unavailable: {exc}".encode()[:120])
        return failed_socket


def start_streamlit() -> subprocess.Popen[bytes]:
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "app.py"),
        f"--server.address={INTERNAL_HOST}",
        f"--server.port={INTERNAL_PORT}",
        "--server.headless=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--browser.gatherUsageStats=false",
    ]
    return subprocess.Popen(command, cwd=ROOT, stdout=sys.stdout, stderr=sys.stderr)


async def wait_for_streamlit(process: subprocess.Popen[bytes], timeout: float = 45.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    async with ClientSession() as session:
        while asyncio.get_running_loop().time() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Streamlit exited before becoming ready.")
            try:
                async with session.get(
                    f"http://{INTERNAL_HOST}:{INTERNAL_PORT}/_stcore/health",
                    timeout=ClientTimeout(total=1),
                ) as response:
                    if response.status == 200:
                        return
            except (ClientError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(0.25)
    raise TimeoutError("Streamlit did not become ready within 45 seconds.")


async def serve() -> None:
    streamlit_process = start_streamlit()
    client: ClientSession | None = None
    runner: web.AppRunner | None = None
    try:
        await wait_for_streamlit(streamlit_process)
        client = ClientSession()
        app = web.Application(client_max_size=8 * 1024 * 1024)
        app["client"] = client
        app.router.add_get("/manus-routes.json", route_manifest)
        app.router.add_route("*", "/{tail:.*}", proxy_request)
        port = int(os.environ.get("PORT", "3000"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()
        print(f"CampusMate Preview bridge listening on 0.0.0.0:{port}", flush=True)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
        await stop.wait()
    finally:
        if runner is not None:
            await runner.cleanup()
        if client is not None:
            await client.close()
        if streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_process.kill()
                streamlit_process.wait(timeout=3)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
