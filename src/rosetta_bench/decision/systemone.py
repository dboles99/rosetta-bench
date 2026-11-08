"""Adapter for the System One decision API (`POST /v1/systemone`).

Request: {"model", "state", "questions": {qid: {"type", "instructions", "criteria"}}}.
Reply:   {"model", "answers": {qid: {...}}, "usage": {"input_tokens", ...}}.

Provider replies are untrusted: they are mapped into rosetta_core.decision answer
types without repair, and validation decides what is usable. Transport failures are
retried a bounded number of times with the same Idempotency-Key; a semantic answer is
never retried. Every attempt is recorded as an exchange (no request headers, so no key).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Mapping

from rosetta_core.decision import (
    AnswerBatch,
    ChoiceAnswer,
    ErrorKind,
    NoulAnswer,
    Primitive,
    ProviderError,
    QuestionDef,
    QuestionSet,
    ScoreAnswer,
)

from .profiles import ProviderProfile
from .transport import HttpResponse, Transport, TransportTimeout, TransportUnavailable, body_hash

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
KEPT_RESPONSE_HEADERS = ("content-type", "retry-after", "x-tokens-remaining")


class CapabilityError(ValueError):
    pass


@dataclass
class AskResult:
    result: AnswerBatch | ProviderError
    exchanges: list[dict] = field(default_factory=list)
    calls: int = 0
    transport_retries: int = 0
    elapsed_ms: float = 0.0
    input_tokens: int | None = None
    tokens_remaining: str | None = None


def encode_body(body: dict) -> bytes:
    """Deterministic but order-preserving: option order is part of the question contract."""
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def question_payload(question: QuestionDef) -> dict:
    entry: dict = {"type": question.primitive.value, "instructions": question.instructions}
    if isinstance(question.criteria, Mapping):
        entry["criteria"] = dict(question.criteria)
    elif isinstance(question.criteria, tuple):
        entry["criteria"] = list(question.criteria)
    return entry


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _score_answer(qid: str, raw: dict, question: QuestionDef | None, profile: ProviderProfile) -> ScoreAnswer | None:
    levels = question.levels if question is not None else None
    score = raw.get("score")
    base = None
    legend = raw.get("legend")
    if isinstance(legend, dict) and levels:
        try:
            numbered = sorted((float(key), value) for key, value in legend.items())
        except (TypeError, ValueError):
            numbered = []
        if [value for _, value in numbered] == list(levels):
            base = numbered[0][0]
    elif profile.score_base is not None:
        base = profile.score_base
    if base is None or not _is_number(score):
        return None
    probabilities = raw.get("probabilities")
    if isinstance(probabilities, list):
        probs = tuple(probabilities)
    elif isinstance(probabilities, dict) and levels and set(probabilities) == set(levels):
        probs = tuple(probabilities[level] for level in levels)
    else:
        probs = None
    return ScoreAnswer(qid, float(score) - base, probs, raw.get("confidence"))


def parse_reply(body: bytes, qset: QuestionSet, profile: ProviderProfile) -> AnswerBatch | ProviderError:
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ProviderError(ErrorKind.MALFORMED, "reply is not JSON")
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        return ProviderError(ErrorKind.MALFORMED, "reply has no answers object")
    served = data["model"] if isinstance(data.get("model"), str) else "<missing>"
    usage = data.get("usage")
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    answers: dict = {}
    unmapped: list[str] = []
    for qid, raw in data["answers"].items():
        if not isinstance(raw, dict):
            return ProviderError(ErrorKind.MALFORMED, "an answer is not an object")
        question = qset.get(qid) if qid in qset else None
        primitive = question.primitive.value if question is not None else raw.get("type", "noul")
        if primitive == Primitive.CHOICE.value:
            probabilities = raw.get("probabilities")
            answers[qid] = ChoiceAnswer(qid, raw.get("choice"), dict(probabilities) if isinstance(probabilities, dict) else None, raw.get("confidence"))
        elif primitive == Primitive.SCORE.value:
            answer = _score_answer(qid, raw, question, profile)
            if answer is None:
                unmapped.append(qid)
            else:
                answers[qid] = answer
        else:
            answers[qid] = NoulAnswer(qid, raw.get("noul"))
    return AnswerBatch(
        provider=profile.name,
        requested_model="",
        served_model=served,
        answers=answers,
        usage_input_tokens=tokens if _is_number(tokens) else None,
        extras={"unmapped_scores": unmapped} if unmapped else {},
    )


def _status_error(response: HttpResponse, attempts: int) -> ProviderError:
    status = response.status
    error_type = ""
    try:
        payload = json.loads(response.body.decode("utf-8"))
        candidate = payload.get("error", {}).get("type", "") if isinstance(payload, dict) else ""
        if isinstance(candidate, str) and candidate.replace("_", "").isalnum() and len(candidate) <= 64:
            error_type = candidate
    except (UnicodeDecodeError, ValueError, AttributeError):
        pass
    if status in (401, 403):
        kind = ErrorKind.AUTH
    elif status == 402:
        kind = ErrorKind.QUOTA_EXHAUSTED
    elif status == 429:
        kind = ErrorKind.RATE_LIMITED
    elif status >= 500:
        kind = ErrorKind.UNAVAILABLE
    elif 400 <= status < 500:
        kind = ErrorKind.INVALID_REQUEST
    else:
        kind = ErrorKind.MALFORMED
    detail = f"HTTP {status}" + (f" {error_type}" if error_type else "")
    return ProviderError(kind, detail, attempts=attempts, http_status=status)


class SystemOneAdapter:
    def __init__(
        self,
        profile: ProviderProfile,
        transport: Transport,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 15.0,
        max_transport_retries: int = 2,
        max_backoff_s: float = 10.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
        new_key: Callable[[], str] = lambda: uuid.uuid4().hex,
    ):
        self.profile = profile
        self.transport = transport
        self.model = model or profile.default_model
        self._api_key = api_key
        self.timeout_s = timeout_s
        self.max_transport_retries = max_transport_retries
        self.max_backoff_s = max_backoff_s
        self._sleep = sleep
        self._clock = clock
        self._new_key = new_key
        self._sequence = 0

    def chunks(self, qset: QuestionSet) -> list[tuple[QuestionDef, ...]]:
        for question in qset.questions:
            if question.primitive is Primitive.CHOICE and len(question.options) > self.profile.max_choice_options:
                raise CapabilityError(
                    f"{question.qid} has {len(question.options)} options; {self.profile.name} allows {self.profile.max_choice_options}"
                )
        size = self.profile.max_questions_per_call
        return [qset.questions[i:i + size] for i in range(0, len(qset.questions), size)]

    def _backoff(self, response: HttpResponse | None, attempt: int) -> float:
        delay = 0.5 * 2 ** (attempt - 1)
        if response is not None:
            try:
                delay = float(response.headers.get("retry-after", delay))
            except (TypeError, ValueError):
                pass
        return min(max(delay, 0.0), self.max_backoff_s)

    def _send(self, payload: bytes, exchanges: list[dict], context: dict) -> tuple[HttpResponse | ProviderError, int]:
        headers = {"Content-Type": "application/json", "User-Agent": "rosetta-bench/0.1"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self.profile.supports_idempotency_key:
            headers["Idempotency-Key"] = self._new_key()
        request_hash = body_hash(payload)
        attempt = 0
        while True:
            attempt += 1
            self._sequence += 1
            started = self._clock()
            response: HttpResponse | None = None
            error: ProviderError | None = None
            try:
                response = self.transport.post(self.profile.endpoint, headers, payload, self.timeout_s)
            except TransportTimeout:
                error = ProviderError(ErrorKind.TIMEOUT, f"no reply within {self.timeout_s:g}s", attempts=attempt)
            except TransportUnavailable as exc:
                error = ProviderError(ErrorKind.UNAVAILABLE, f"connection failed ({exc})", attempts=attempt)
            exchanges.append({
                **context,
                "sequence": self._sequence,
                "attempt": attempt,
                "request_hash": request_hash,
                "request_body": payload.decode("utf-8") if attempt == 1 else None,
                "status": response.status if response is not None else None,
                "response_headers": {k: v for k, v in (response.headers.items() if response else []) if k.lower() in KEPT_RESPONSE_HEADERS},
                "response_body": response.body.decode("utf-8", "replace") if response is not None else None,
                "error": error.kind.value if error else None,
                "elapsed_ms": (self._clock() - started) * 1000,
            })
            if response is not None and response.status == 200:
                return response, attempt
            if response is not None:
                error = _status_error(response, attempt)
            if not error.retryable or attempt > self.max_transport_retries:
                return error, attempt
            self._sleep(self._backoff(response, attempt))

    def ask(self, state: dict, qset: QuestionSet, context: dict | None = None) -> AskResult:
        context = dict(context or {})
        started = self._clock()
        outcome = AskResult(result=ProviderError(ErrorKind.MALFORMED, "not asked"))
        if self.profile.api_key_env and not self._api_key:
            outcome.result = ProviderError(ErrorKind.AUTH, f"{self.profile.api_key_env} is not set")
            return outcome
        try:
            chunks = self.chunks(qset)
        except CapabilityError as exc:
            outcome.result = ProviderError(ErrorKind.CONTRACT_MISMATCH, str(exc))
            return outcome

        answers: dict = {}
        served: str | None = None
        tokens: int | None = 0
        unmapped: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            body = {"model": self.model, "state": state, "questions": {q.qid: question_payload(q) for q in chunk}}
            reply, attempts = self._send(encode_body(body), outcome.exchanges, {**context, "chunk": index})
            outcome.calls += attempts
            outcome.transport_retries += attempts - 1
            if isinstance(reply, ProviderError):
                outcome.result = ProviderError(reply.kind, f"call {index}/{len(chunks)}: {reply.detail}", reply.attempts, reply.http_status)
                break
            outcome.tokens_remaining = reply.headers.get("x-tokens-remaining", outcome.tokens_remaining)
            parsed = parse_reply(reply.body, qset, self.profile)
            if isinstance(parsed, ProviderError):
                outcome.result = parsed
                break
            if served is not None and parsed.served_model != served:
                outcome.result = ProviderError(ErrorKind.MALFORMED, "served model changed between calls")
                break
            served = parsed.served_model
            answers.update(parsed.answers)
            unmapped += parsed.extras.get("unmapped_scores", [])
            tokens = None if tokens is None or parsed.usage_input_tokens is None else tokens + parsed.usage_input_tokens
        else:
            outcome.result = AnswerBatch(
                provider=self.profile.name,
                requested_model=self.model,
                served_model=served or "<missing>",
                answers=answers,
                usage_input_tokens=tokens,
                extras={"unmapped_scores": unmapped} if unmapped else {},
            )
            outcome.input_tokens = tokens
        outcome.elapsed_ms = (self._clock() - started) * 1000
        return outcome
