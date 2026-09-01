"""Connect-time SSRF guard (DNS-rebinding defense).

`_is_public_url` is only a name-based pre-check; DNS can rebind between that
lookup and the socket connect. The guarded requests session validates the
*actual* peer address inside `connect()`, which is TOCTOU-free. These tests
prove the peer check refuses internal addresses without changing normal TLS.
"""

from __future__ import annotations

import http.server
import socketserver
import threading

import pytest

import acb_large_print_web.site_audit as site_audit


def test_ip_is_public_classifies_addresses():
    assert site_audit._ip_is_public("93.184.216.34") is True
    for internal in ("127.0.0.1", "169.254.169.254", "10.0.0.1", "192.168.1.1", "::1", "0.0.0.0"):
        assert site_audit._ip_is_public(internal) is False, internal


def test_assert_public_peer_blocks_internal_and_allows_public():
    class _Sock:
        def __init__(self, ip):
            self._ip = ip

        def getpeername(self):
            return (self._ip, 443)

    with pytest.raises(site_audit.BlockedURLError):
        site_audit._assert_public_peer(_Sock("127.0.0.1"))
    with pytest.raises(site_audit.BlockedURLError):
        site_audit._assert_public_peer(_Sock("169.254.169.254"))
    # A public peer passes silently.
    site_audit._assert_public_peer(_Sock("93.184.216.34"))


def test_guarded_session_refuses_loopback_at_connect():
    """End-to-end: the adapter/pool/connection chain fires the peer check.

    We bypass the name pre-check by calling the session directly on a loopback
    URL; the connection reaches 127.0.0.1 and must be refused inside connect().
    """
    server = socketserver.TCPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(Exception) as excinfo:
            site_audit._guarded_session.get(f"http://127.0.0.1:{port}/", timeout=5)
        # The underlying cause is our BlockedURLError, however requests wraps it.
        assert "BlockedURLError" in repr(excinfo.value) or isinstance(
            excinfo.value, site_audit.BlockedURLError
        )
    finally:
        server.shutdown()
        server.server_close()
