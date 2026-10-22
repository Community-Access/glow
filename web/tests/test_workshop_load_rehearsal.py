from __future__ import annotations

from scripts.workshop_load_rehearsal import build_http


def test_deployed_rehearsal_client_fetches_and_submits_csrf_token(monkeypatch):
    import requests

    class CookieJar:
        def set(self, *_args, **_kwargs):
            pass

    class Response:
        status_code = 200
        text = '<html><head><meta name="csrf-token" content="csrf-example"></head></html>'

    class FakeSession:
        def __init__(self):
            self.cookies = CookieJar()
            self.post_data = None

        def get(self, *_args, **_kwargs):
            return Response()

        def post(self, *_args, **kwargs):
            self.post_data = kwargs["data"]
            return Response()

    fake_session = FakeSession()
    monkeypatch.setattr(requests, "Session", lambda: fake_session)
    client_factory, _workshop_routes, _ = build_http("https://example.test")

    client = client_factory()
    client.get("/workshop/?code=ahg-load-test-123-1")
    client.post("/workshop/", data={"action": "join"})

    assert fake_session.post_data == {"action": "join", "csrf_token": "csrf-example"}
