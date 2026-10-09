"""One-time Google OAuth for Meet API (OPEN spaces)."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
import socket
import threading
import webbrowser

from google_auth_oauthlib.flow import InstalledAppFlow

from google_meet import SCOPES, TOKEN_FILE, _credentials_from_env_or_file


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    client_config = _credentials_from_env_or_file()
    if not client_config:
        raise SystemExit("Missing credentials.json")

    port = _free_port()
    redirect_uri = f"http://127.0.0.1:{port}/"
    flow = InstalledAppFlow.from_client_config(
        client_config,
        SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="false",
    )

    result: dict[str, str] = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            got_state = (params.get("state") or [None])[0]
            code = (params.get("code") or [None])[0]
            err = (params.get("error") or [None])[0]
            if err:
                body = f"OAuth error: {err}"
                self._reply(400, body)
                result["error"] = err
                done.set()
                return
            if got_state != state or not code:
                self._reply(404, "Waiting for Google OAuth redirect…")
                print(f"ignored request path={self.path!r}")
                return
            self._reply(200, "OK — можеш да затвориш този таб и да се върнеш в Cursor.")
            result["code"] = code
            done.set()

        def log_message(self, format: str, *args) -> None:
            print("http:", args[0] if args else format)

        def _reply(self, status: int, text: str) -> None:
            payload = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("\n1) In Google Cloud Console click PUBLISH APP (In production).")
    print("2) Then open this URL and click Allow:\n")
    print(auth_url)
    print(f"\nCallback: {redirect_uri}")
    webbrowser.open(auth_url)

    if not done.wait(timeout=300):
        server.shutdown()
        raise SystemExit("Timed out waiting for Google Allow (5 min).")

    server.shutdown()
    if "error" in result:
        raise SystemExit(f"Google OAuth error: {result['error']}")

    flow.fetch_token(code=result["code"])
    TOKEN_FILE.write_text(flow.credentials.to_json(), encoding="utf-8")
    print(f"OK — token saved to {TOKEN_FILE}")
    print(f"scopes: {flow.credentials.scopes}")
    print(f"valid: {flow.credentials.valid}")
    print(f"has_refresh: {bool(flow.credentials.refresh_token)}")


if __name__ == "__main__":
    main()
