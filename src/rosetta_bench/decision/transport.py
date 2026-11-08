"""HTTP transports. The adapter never touches the network directly: tests and offline
runs inject FakeTransport or ReplayTransport; only UrllibTransport makes real calls."""
import hashlib
import json
import socket
import urllib.error
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class TransportTimeout(Exception):
    pass


class TransportUnavailable(Exception):
    pass


class ReplayMiss(KeyError):
    pass


class Transport(Protocol):
    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout_s: float) -> HttpResponse:
        ...


def body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _lower(headers) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (headers.items() if headers else [])}


class UrllibTransport:
    """Live HTTP transport. Used only when a run is started with --live."""

    def post(self, url, headers, body, timeout_s):
        request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                return HttpResponse(response.status, _lower(response.headers), response.read())
        except urllib.error.HTTPError as error:
            return HttpResponse(error.code, _lower(error.headers), error.read() if error.fp else b"")
        except (socket.timeout, TimeoutError) as error:
            raise TransportTimeout(str(error)) from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise TransportTimeout(str(error.reason)) from None
            raise TransportUnavailable(type(error.reason).__name__) from None
        except (ConnectionError, OSError) as error:
            raise TransportUnavailable(type(error).__name__) from None


class FakeTransport:
    """Scripted transport: a list of responses/exceptions served in order, or a callable
    computing a response from the decoded JSON body. Records every request."""

    def __init__(self, script):
        self._responder: Callable | None = script if callable(script) else None
        self._queue = deque([] if callable(script) else script)
        self.requests: list[dict] = []

    def post(self, url, headers, body, timeout_s):
        decoded = json.loads(body.decode("utf-8")) if body else None
        self.requests.append({"url": url, "headers": dict(headers), "body": decoded, "raw": body, "timeout_s": timeout_s})
        if self._responder is not None:
            return self._responder(decoded)
        item = self._queue.popleft()
        if isinstance(item, Exception):
            raise item
        return item


class ReplayTransport:
    """Serves recorded exchanges by request-body hash, attempt by attempt."""

    def __init__(self, exchanges: list[dict], hash_fn: Callable[[bytes], str] = body_hash):
        self._hash = hash_fn
        self._queues: dict[str, deque] = defaultdict(deque)
        for exchange in sorted(exchanges, key=lambda e: (e.get("sequence", 0), e.get("attempt", 0))):
            self._queues[exchange["request_hash"]].append(exchange)

    def post(self, url, headers, body, timeout_s):
        key = self._hash(body)
        queue = self._queues.get(key)
        if not queue:
            raise ReplayMiss(f"no recorded reply for request {key[:12]}")
        exchange = queue.popleft()
        if exchange.get("error") == "TIMEOUT":
            raise TransportTimeout("recorded timeout")
        if exchange.get("error") == "UNAVAILABLE":
            raise TransportUnavailable("recorded connection failure")
        body_text = exchange.get("response_body") or ""
        return HttpResponse(exchange["status"], exchange.get("response_headers") or {}, body_text.encode("utf-8"))


class BudgetExceeded(Exception):
    pass


class BudgetTransport:
    """Counts every call, retries included, and refuses calls beyond the budget."""

    def __init__(self, inner: Transport, max_calls: int):
        self.inner = inner
        self.max_calls = max_calls
        self.calls = 0

    def post(self, url, headers, body, timeout_s):
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"call budget of {self.max_calls} reached")
        self.calls += 1
        return self.inner.post(url, headers, body, timeout_s)
