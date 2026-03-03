#!/usr/bin/env python3
"""
Local proxy bridge for BrightData residential proxy.

Chromium connects to localhost:18080 (no auth required).
This bridge forwards all requests to BrightData with authentication.

Usage:
    python proxy_bridge.py                  # Start with defaults
    python proxy_bridge.py --port 18080     # Custom local port
    python proxy_bridge.py --test           # Test upstream proxy
"""

import asyncio
import argparse
import base64
import json
import signal
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / ".brightdata_proxy.json"

DEFAULT_CONFIG = {
    "upstream_host": "brd.superproxy.io",
    "upstream_port": 33335,
    "username": "brd-customer-hl_d1aa32d8-zone-residential_proxy1",
    "password": "rr13cecunv81",
    "local_port": 18080,
    "country": "",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        config = {**DEFAULT_CONFIG, **saved}
    else:
        config = DEFAULT_CONFIG.copy()
        save_config(config)
    return config


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_proxy_auth(config: dict) -> str:
    username = config["username"]
    if config.get("country"):
        username += f"-country-{config['country']}"
    creds = f"{username}:{config['password']}"
    return base64.b64encode(creds.encode()).decode()


async def pipe(reader, writer, label=""):
    """Copy data from reader to writer until EOF."""
    try:
        while True:
            data = await asyncio.wait_for(reader.read(65536), timeout=300)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError, OSError):
        pass
    except asyncio.CancelledError:
        pass


async def handle_client(client_reader, client_writer, config):
    """Handle a single client connection."""
    upstream_writer = None
    try:
        # Read the request line
        request_line = await asyncio.wait_for(client_reader.readline(), timeout=30)
        if not request_line:
            return

        # Read all headers
        headers = []
        while True:
            line = await asyncio.wait_for(client_reader.readline(), timeout=10)
            if line == b"\r\n" or line == b"\n" or not line:
                break
            headers.append(line)

        # Connect to BrightData upstream
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(config["upstream_host"], config["upstream_port"]),
            timeout=15
        )

        # Build auth header
        auth_b64 = get_proxy_auth(config)
        auth_line = f"Proxy-Authorization: Basic {auth_b64}\r\n".encode()

        # Forward request line
        upstream_writer.write(request_line)

        # Forward headers, injecting auth and skipping any existing proxy-auth
        for h in headers:
            if not h.lower().startswith(b"proxy-authorization"):
                upstream_writer.write(h)
        upstream_writer.write(auth_line)
        upstream_writer.write(b"\r\n")
        await upstream_writer.drain()

        request_str = request_line.decode("utf-8", errors="replace").strip()
        is_connect = request_str.upper().startswith("CONNECT")

        if is_connect:
            # Read upstream's response to CONNECT
            response_line = await asyncio.wait_for(upstream_reader.readline(), timeout=15)
            resp_headers = [response_line]
            while True:
                line = await asyncio.wait_for(upstream_reader.readline(), timeout=10)
                resp_headers.append(line)
                if line == b"\r\n" or line == b"\n" or not line:
                    break

            # Forward response to client
            for line in resp_headers:
                client_writer.write(line)
            await client_writer.drain()

            # If 200, set up bidirectional tunnel
            if b"200" in response_line:
                t1 = asyncio.create_task(pipe(client_reader, upstream_writer, "c->u"))
                t2 = asyncio.create_task(pipe(upstream_reader, client_writer, "u->c"))
                done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
        else:
            # Plain HTTP: just pipe bidirectionally
            t1 = asyncio.create_task(pipe(client_reader, upstream_writer, "c->u"))
            t2 = asyncio.create_task(pipe(upstream_reader, client_writer, "u->c"))
            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()

    except asyncio.TimeoutError:
        pass
    except ConnectionRefusedError:
        print("[bridge] Upstream connection refused")
    except Exception as e:
        print(f"[bridge] Error: {e}")
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except:
            pass
        if upstream_writer:
            try:
                upstream_writer.close()
                await upstream_writer.wait_closed()
            except:
                pass


async def run_server(config):
    port = config["local_port"]

    async def on_client(r, w):
        await handle_client(r, w, config)

    server = await asyncio.start_server(on_client, "127.0.0.1", port)
    print(f"✅ Proxy bridge listening on 127.0.0.1:{port}", flush=True)
    print(f"   Upstream: {config['upstream_host']}:{config['upstream_port']}", flush=True)
    if config.get("country"):
        print(f"   Country: {config['country']}", flush=True)
    print(f"   Chromium flag: --proxy-server=http://127.0.0.1:{port}", flush=True)

    async with server:
        await server.serve_forever()


def test_proxy(config):
    """Test upstream proxy."""
    import urllib.request
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    username = config["username"]
    if config.get("country"):
        username += f"-country-{config['country']}"
    proxy_url = f"http://{username}:{config['password']}@{config['upstream_host']}:{config['upstream_port']}"

    handler = urllib.request.ProxyHandler({"https": proxy_url, "http": proxy_url})
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    opener = urllib.request.build_opener(handler, https_handler)

    tests = [
        ("BrightData Test", "https://geo.brdtest.com/mygeo.json"),
        ("Google", "https://www.google.com"),
        ("Hacker News", "https://news.ycombinator.com"),
    ]

    for name, url in tests:
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = opener.open(req, timeout=15)
            print(f"  ✅ {name}: HTTP {resp.status}")
            if "brdtest" in url:
                data = json.loads(resp.read().decode())
                print(f"     IP Country: {data.get('country', '?')}, City: {data.get('city', '?')}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="BrightData proxy bridge")
    parser.add_argument("--port", type=int, help="Local port (default: 18080)")
    parser.add_argument("--country", type=str, help="Target country (e.g. us)")
    parser.add_argument("--test", action="store_true", help="Test upstream and exit")
    parser.add_argument("--show-config", action="store_true", help="Show config")
    args = parser.parse_args()

    config = load_config()
    if args.port:
        config["local_port"] = args.port
        save_config(config)
    if args.country is not None:
        config["country"] = args.country
        save_config(config)

    if args.show_config:
        print(json.dumps(config, indent=2))
        return
    if args.test:
        print("Testing BrightData proxy...")
        test_proxy(config)
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(sig, frame):
        print("\n🛑 Shutting down proxy bridge...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(run_server(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()