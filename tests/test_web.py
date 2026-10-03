import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from docs_search_mcp.web import FetchError, check_url, fetch_url, html_to_markdown

PAGE = "<html><head><style>x{}</style></head><body><nav>menu</nav><h1>Title</h1><p>Hello <b>world</b></p><script>evil()</script></body></html>"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        routes = {
            "/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /private\n"),
            "/page": (200, "text/html", PAGE),
            "/private": (200, "text/html", "<p>secret</p>"),
            "/text": (200, "text/plain", "x" * 100),
            "/big": (200, "text/plain", "y" * 3_000_000),
            "/missing": (404, "text/plain", "no"),
        }
        if self.path == "/redir":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.end_headers()
            return
        if self.path == "/loop":
            self.send_response(302)
            self.send_header("Location", "/loop")
            self.end_headers()
            return
        code, ctype, body = routes.get(self.path, (404, "text/plain", "nf"))
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def base():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_html_to_markdown_strips_scripts_and_nav():
    md = html_to_markdown(PAGE)
    assert "# Title" in md and "**world**" in md
    assert "evil" not in md and "menu" not in md


def test_fetch_html_page(base):
    r = fetch_url(base + "/page", allow_private=True)
    assert "# Title" in r["content"] and r["next_start_index"] is None


def test_pagination(base):
    a = fetch_url(base + "/text", max_length=40, allow_private=True)
    assert len(a["content"]) == 40 and a["next_start_index"] == 40
    c = fetch_url(base + "/text", max_length=40, start_index=80, allow_private=True)
    assert len(c["content"]) == 20 and c["next_start_index"] is None


def test_private_addresses_blocked_by_default(base):
    with pytest.raises(FetchError, match="non-public"):
        fetch_url(base + "/page")
    for u in ["http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/latest/meta-data/", "http://10.0.0.1/", "http://[::1]/"]:
        with pytest.raises(FetchError):
            check_url(u)


@pytest.mark.parametrize("u", ["file:///etc/passwd", "ftp://example.com/x", "javascript:alert(1)", "/relative", ""])
def test_non_http_schemes_rejected(u):
    with pytest.raises(FetchError):
        check_url(u, allow_private=True)


def test_robots_disallow_respected_and_can_be_off_in_tests(base):
    with pytest.raises(FetchError, match="robots.txt"):
        fetch_url(base + "/private", allow_private=True)
    assert "secret" in fetch_url(base + "/private", allow_private=True, respect_robots=False)["content"]


def test_redirect_followed_and_loop_limited(base):
    assert fetch_url(base + "/redir", allow_private=True)["url"].endswith("/page")
    with pytest.raises(FetchError, match="redirects"):
        fetch_url(base + "/loop", allow_private=True, respect_robots=False)


def test_http_error_size_cap_and_argument_validation(base):
    with pytest.raises(FetchError, match="404"):
        fetch_url(base + "/missing", allow_private=True)
    with pytest.raises(FetchError, match="larger"):
        fetch_url(base + "/big", allow_private=True)
    with pytest.raises(FetchError):
        fetch_url(base + "/text", max_length=0, allow_private=True)
    with pytest.raises(FetchError):
        fetch_url(base + "/text", start_index=-1, allow_private=True)


def test_redirect_target_is_rechecked_for_ssrf(base, monkeypatch):
    """A public-looking first hop that redirects to a private address must be refused."""
    import docs_search_mcp.web as web
    real, calls = web.check_url, {"n": 0}

    def first_hop_allowed(url, allow_private=False):
        calls["n"] += 1
        return None if calls["n"] <= 2 else real(url, allow_private)  # hop 1: robots + page allowed

    monkeypatch.setattr(web, "check_url", first_hop_allowed)
    with pytest.raises(FetchError, match="non-public"):
        web.fetch_url(base + "/redir", allow_private=False, respect_robots=True)
