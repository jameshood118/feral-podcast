#!/usr/bin/env python3
"""
Async Telemetry WebSocket Server
Broadcasts captains_log_staging.json events over ws://localhost:8765 to
feed the Matryoshka Holodeck Tauri desktop viewport in real time.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Pure standard library async TCP socket server acting as lightweight WebSocket bridge
async def handle_client(reader, writer):
    # Basic WebSocket Handshake parser
    request = await reader.read(4096)
    request_text = request.decode("utf-8", errors="ignore")

    key = ""
    for line in request_text.split("\r\n"):
        if line.lower().startswith("sec-websocket-key:"):
            key = line.split(":", 1)[1].strip()
            break

    if key:
        import hashlib
        import base64
        guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_val = base64.b64encode(hashlib.sha1((key + guid).encode("utf-8")).digest()).decode("utf-8")
        handshake_resp = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
        )
        writer.write(handshake_resp.encode("utf-8"))
        await writer.drain()

    root = Path(__file__).resolve().parent.parent
    log_file = root / "captains_log_staging.json"
    last_mtime = 0

    try:
        while True:
            if log_file.exists():
                mtime = log_file.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    content = log_file.read_text(encoding="utf-8")
                    msg_bytes = content.encode("utf-8")
                    length = len(msg_bytes)

                    # Encode unmasked server frame
                    if length <= 125:
                        frame = bytes([0x81, length]) + msg_bytes
                    elif length <= 65535:
                        frame = bytes([0x81, 126]) + length.to_bytes(2, "big") + msg_bytes
                    else:
                        frame = bytes([0x81, 127]) + length.to_bytes(8, "big") + msg_bytes

                    writer.write(frame)
                    await writer.drain()

            await asyncio.sleep(1.0)
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    host = "127.0.0.1"
    port = 8765
    server = await asyncio.start_server(handle_client, host, port)
    print(f"[BRIDGE_ONLINE] Golem Telemetry WebSocket listening on ws://{host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[BRIDGE_OFFLINE] WebSocket server terminated.")