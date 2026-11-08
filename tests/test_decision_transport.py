import socket
import urllib.error

import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_bench.decision import transport as transport_module
from rosetta_bench.decision.transport import (
    FakeTransport,
    HttpResponse,
    ReplayMiss,
    ReplayTransport,
    TransportTimeout,
    TransportUnavailable,
    UrllibTransport,
)


def test_fake_transport_records_requests_and_serves_scripted_replies():
    fake = FakeTransport([HttpResponse(200, {}, b"{}"), TransportTimeout("slow")])
    assert fake.post("u", {"A": "1"}, b'{"x":1}', 5.0).status == 200
    with pytest.raises(TransportTimeout):
        fake.post("u", {}, b"{}", 5.0)
    assert fake.requests[0]["body"] == {"x": 1}
    assert fake.requests[0]["headers"] == {"A": "1"}


def test_fake_transport_can_compute_replies_from_the_request():
    fake = FakeTransport(lambda body: HttpResponse(200, {}, str(body["n"] * 2).encode()))
    assert fake.post("u", {}, b'{"n":21}', 5.0).body == b"42"


def test_replay_serves_recorded_attempts_in_order_by_request_hash():
    exchanges = [
        {"request_hash": "h1", "attempt": 1, "status": 502, "response_headers": {}, "response_body": "bad gateway", "error": None},
        {"request_hash": "h1", "attempt": 2, "status": 200, "response_headers": {}, "response_body": "{}", "error": None},
    ]
    replay = ReplayTransport(exchanges, hash_fn=lambda body: "h1")
    assert replay.post("u", {}, b"x", 5.0).status == 502
    assert replay.post("u", {}, b"x", 5.0).status == 200


def test_replay_reraises_recorded_transport_failures():
    exchanges = [{"request_hash": "h1", "attempt": 1, "status": None, "response_headers": {}, "response_body": None, "error": "TIMEOUT"}]
    with pytest.raises(TransportTimeout):
        ReplayTransport(exchanges, hash_fn=lambda body: "h1").post("u", {}, b"x", 5.0)


def test_replay_refuses_a_request_that_was_never_recorded():
    with pytest.raises(ReplayMiss):
        ReplayTransport([], hash_fn=lambda body: "h9").post("u", {}, b"x", 5.0)


def test_urllib_transport_maps_a_socket_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr(transport_module.urllib.request, "urlopen", raise_timeout)
    with pytest.raises(TransportTimeout):
        UrllibTransport().post("https://example.invalid", {}, b"{}", 1.0)


def test_urllib_transport_maps_a_refused_connection(monkeypatch):
    def refuse(*args, **kwargs):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(transport_module.urllib.request, "urlopen", refuse)
    with pytest.raises(TransportUnavailable):
        UrllibTransport().post("https://example.invalid", {}, b"{}", 1.0)


def test_urllib_transport_returns_http_errors_as_responses(monkeypatch):
    import io

    def http_error(*args, **kwargs):
        raise urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "3"}, io.BytesIO(b'{"error":{}}'))

    monkeypatch.setattr(transport_module.urllib.request, "urlopen", http_error)
    response = UrllibTransport().post("https://example.invalid", {}, b"{}", 1.0)
    assert response.status == 429
    assert response.headers["retry-after"] == "3"
