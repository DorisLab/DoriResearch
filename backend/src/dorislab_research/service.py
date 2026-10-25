"""Private loopback service. Stdin EOF ties lifetime to the desktop parent."""

import argparse
import hmac
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import job_process
from .database import connect, migrate
from .library import Library
from .service_api import dispatch


def serve(root: Path, token: str, port: int = 0) -> None:
    library = Library(root)
    with connect(root) as db:
        db.execute(
            "UPDATE jobs SET status='failed',error='程序已重启，这次回测未完成，请重新发起' "
            "WHERE status IN ('running','queued')"
        )

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(30)

        def do_POST(self) -> None:
            if self.path != "/rpc" or not hmac.compare_digest(
                self.headers.get("Authorization", ""), f"Bearer {token}"
            ):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError("请求大小无效")
                request = json.loads(self.rfile.read(length))
                value = {"result": dispatch(library, request["operation"], request.get("args", {}))}
                payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
            except Exception as error:
                payload = json.dumps({"error": str(error)}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    # Never print the bearer token. The parent already owns it.
    print(json.dumps({"port": server.server_address[1]}), flush=True)

    def parent_closed() -> None:
        sys.stdin.buffer.read()
        server.shutdown()

    threading.Thread(target=parent_closed, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        job_process.stop_all()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["migrate", "serve", "seed", "check", "verify", "restore"]
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.cache:
        args.cache.mkdir(parents=True, exist_ok=True)
        os.environ["DORIRESEARCH_CACHE"] = str(args.cache.resolve())
    if args.command == "migrate":
        migrate(args.data)
    elif args.command == "seed":
        from .examples import seed

        seed(Library(args.data))
    elif args.command == "verify":
        from .service_verify import verify

        print(json.dumps(verify(args.data)))
    elif args.command == "check":
        print(json.dumps(dispatch(Library(args.data), "health", {})))
    elif args.command == "restore":
        from .storage import restore

        if args.backup is None:
            parser.error("restore requires --backup")
        restore(args.data, args.backup)
    else:
        serve(args.data, os.environ["DORIRESEARCH_TOKEN"])


if __name__ == "__main__":
    main()
