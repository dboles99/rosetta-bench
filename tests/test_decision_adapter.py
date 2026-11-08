import json

import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_core.decision import ErrorKind, Primitive, ProviderError, QuestionDef, QuestionSet, validate_batch

from rosetta_bench.decision.profiles import PROFILES, ProviderProfile
from rosetta_bench.decision.systemone import SystemOneAdapter
from rosetta_bench.decision.transport import FakeTransport, HttpResponse, TransportTimeout

KEY = "test-key-" + "q" * 20  # not a real credential
QSET = QuestionSet(
    "intake",
    "1.0",
    (
        QuestionDef("route_fits", "1.0", Primitive.NOUL, "Does a listed workflow fit?"),
        QuestionDef("workflow_route", "1.0", Primitive.CHOICE, "Which workflow fits best?", {"zeta": "Last letter", "alpha": "First letter"}),
        QuestionDef("effort", "1.0", Primitive.SCORE, "How much effort?", ("low", "medium", "high")),
    ),
)
STATE = {"objective": "route", "evidence": {"request.text": {"value": "add a flag"}}}
GOOD_REPLY = {
    "model": "jev-latest",
    "answers": {
        "route_fits": {"type": "noul", "noul": 0.91},
        "workflow_route": {"type": "choice", "choice": "zeta", "probabilities": {"zeta": 0.8, "alpha": 0.2}, "confidence": 0.6},
        "effort": {"type": "score", "score": 2.0, "legend": {"1": "low", "2": "medium", "3": "high"}, "probabilities": [0.1, 0.8, 0.1], "confidence": 0.7},
    },
    "usage": {"input_tokens": 120, "output_tokens": 0},
}
TEST_PROFILE = ProviderProfile(
    name="test", endpoint="https://provider.invalid/v1/systemone", api_key_env="TEST_KEY", default_model="jev-latest",
    pricing_tool="JEVMODEL", max_questions_per_call=8, max_choice_options=20, score_base=None,
    pins_versions=False, supports_idempotency_key=True, notes="test",
)


def _ok(body=None, headers=None):
    return HttpResponse(200, headers or {"content-type": "application/json"}, json.dumps(body or GOOD_REPLY).encode())


def _adapter(script, profile=TEST_PROFILE, api_key=KEY, **kwargs):
    sleeps = []
    transport = FakeTransport(script)
    adapter = SystemOneAdapter(profile, transport, api_key=api_key, sleep=sleeps.append, **kwargs)
    return adapter, transport, sleeps


def test_request_body_carries_model_state_and_typed_questions():
    adapter, transport, _ = _adapter([_ok()])
    adapter.ask(STATE, QSET)
    body = transport.requests[0]["body"]
    assert body["model"] == "jev-latest"
    assert body["state"] == STATE
    assert body["questions"]["route_fits"] == {"type": "noul", "instructions": "Does a listed workflow fit?"}
    assert body["questions"]["effort"]["criteria"] == ["low", "medium", "high"]


def test_choice_options_are_sent_in_declared_order():
    adapter, transport, _ = _adapter([_ok()])
    adapter.ask(STATE, QSET)
    raw = transport.requests[0]["raw"].decode("utf-8")
    assert raw.index('"zeta"') < raw.index('"alpha"')


def test_auth_and_idempotency_headers_are_sent():
    adapter, transport, _ = _adapter([_ok()])
    adapter.ask(STATE, QSET)
    headers = transport.requests[0]["headers"]
    assert headers["Authorization"] == f"Bearer {KEY}"
    assert len(headers["Idempotency-Key"]) >= 16


def test_missing_key_fails_without_calling_the_provider():
    adapter, transport, _ = _adapter([_ok()], api_key=None)
    result = adapter.ask(STATE, QSET).result
    assert isinstance(result, ProviderError) and result.kind is ErrorKind.AUTH
    assert "TEST_KEY" in result.detail
    assert transport.requests == []


def test_a_valid_reply_is_normalised():
    outcome = _adapter([_ok()])[0].ask(STATE, QSET)
    batch = outcome.result
    assert batch.served_model == "jev-latest"
    assert batch.answers["route_fits"].p_yes == 0.91
    assert batch.answers["workflow_route"].selected == "zeta"
    assert batch.answers["effort"].position == 1.0  # legend numbers from 1, so score 2 is the middle level
    assert batch.answers["effort"].probabilities == (0.1, 0.8, 0.1)
    assert outcome.input_tokens == 120
    assert validate_batch(batch, QSET) == []


def test_a_score_without_a_legend_is_left_unmapped_not_guessed():
    reply = json.loads(json.dumps(GOOD_REPLY))
    reply["answers"]["effort"] = {"type": "score", "score": 2.0, "confidence": 0.7}
    batch = _adapter([_ok(reply)])[0].ask(STATE, QSET).result
    assert "effort" not in batch.answers
    assert batch.extras["unmapped_scores"] == ["effort"]
    assert {v.code for v in validate_batch(batch, QSET)} == {"MISSING"}


def test_non_json_reply_is_malformed():
    result = _adapter([HttpResponse(200, {}, b"<html>oops</html>")])[0].ask(STATE, QSET).result
    assert result.kind is ErrorKind.MALFORMED


def test_reply_without_answers_is_malformed():
    result = _adapter([_ok({"model": "jev-latest"})])[0].ask(STATE, QSET).result
    assert result.kind is ErrorKind.MALFORMED


def test_nan_in_a_reply_is_passed_on_for_validation_to_reject():
    raw = json.dumps(GOOD_REPLY).replace("0.91", "NaN").encode()
    batch = _adapter([HttpResponse(200, {}, raw)])[0].ask(STATE, QSET).result
    assert {v.code for v in validate_batch(batch, QSET)} == {"BAD_PROBABILITY"}


@pytest.mark.parametrize(
    "status, kind",
    [(401, ErrorKind.AUTH), (403, ErrorKind.AUTH), (402, ErrorKind.QUOTA_EXHAUSTED), (422, ErrorKind.INVALID_REQUEST)],
)
def test_non_retryable_statuses_fail_after_one_call(status, kind):
    adapter, transport, sleeps = _adapter([HttpResponse(status, {}, b'{"error":{"type":"x","message":"m"}}')] * 3)
    result = adapter.ask(STATE, QSET).result
    assert result.kind is kind
    assert len(transport.requests) == 1
    assert sleeps == []


def test_rate_limit_is_retried_after_the_advertised_delay():
    adapter, transport, sleeps = _adapter([HttpResponse(429, {"retry-after": "3"}, b"{}"), _ok()])
    outcome = adapter.ask(STATE, QSET)
    assert not isinstance(outcome.result, ProviderError)
    assert outcome.transport_retries == 1
    assert sleeps == [3.0]
    keys = [r["headers"]["Idempotency-Key"] for r in transport.requests]
    assert keys[0] == keys[1]


def test_retries_are_bounded_and_backoff_is_capped():
    adapter, transport, sleeps = _adapter([HttpResponse(502, {"retry-after": "99"}, b"")] * 5, max_transport_retries=2)
    result = adapter.ask(STATE, QSET).result
    assert result.kind is ErrorKind.UNAVAILABLE
    assert len(transport.requests) == 3
    assert sleeps == [10.0, 10.0]


def test_repeated_timeouts_become_a_timeout_error():
    adapter, transport, sleeps = _adapter([TransportTimeout("slow")] * 3, max_transport_retries=2)
    result = adapter.ask(STATE, QSET).result
    assert result.kind is ErrorKind.TIMEOUT
    assert sleeps == [0.5, 1.0]


def test_questions_beyond_the_provider_cap_are_split_across_calls():
    questions = tuple(QuestionDef(f"q{i}", "1.0", Primitive.NOUL, f"Question {i}?") for i in range(10))
    qset = QuestionSet("many", "1.0", questions)

    def responder(body):
        answers = {qid: {"type": "noul", "noul": 0.5} for qid in body["questions"]}
        return _ok({"model": "jev-latest", "answers": answers, "usage": {"input_tokens": 10}})

    adapter, transport, _ = _adapter(responder)
    outcome = adapter.ask(STATE, qset)
    assert [len(r["body"]["questions"]) for r in transport.requests] == [8, 2]
    assert set(outcome.result.answers) == {f"q{i}" for i in range(10)}
    assert outcome.input_tokens == 20


def test_a_choice_beyond_the_option_cap_is_refused_before_any_call():
    options = {f"o{i}": f"option {i}" for i in range(21)}
    qset = QuestionSet("wide", "1.0", (QuestionDef("pick", "1.0", Primitive.CHOICE, "Pick one", options),))
    adapter, transport, _ = _adapter([_ok()])
    result = adapter.ask(STATE, qset).result
    assert result.kind is ErrorKind.CONTRACT_MISMATCH
    assert transport.requests == []


def test_a_model_change_between_split_calls_is_malformed():
    questions = tuple(QuestionDef(f"q{i}", "1.0", Primitive.NOUL, f"Question {i}?") for i in range(9))
    replies = iter(["jev-latest", "jev-1.15.0"])

    def responder(body):
        answers = {qid: {"type": "noul", "noul": 0.5} for qid in body["questions"]}
        return _ok({"model": next(replies), "answers": answers})

    result = _adapter(responder)[0].ask(STATE, QuestionSet("many", "1.0", questions)).result
    assert result.kind is ErrorKind.MALFORMED


def test_exchanges_never_contain_the_api_key():
    outcome = _adapter([HttpResponse(429, {}, b"{}"), _ok()])[0].ask(STATE, QSET)
    assert KEY not in json.dumps(outcome.exchanges)
    assert outcome.exchanges[0]["request_body"] is not None


def test_shipped_profiles_encode_documented_limits():
    assert PROFILES["jevmodel"].endpoint == "https://jevmodel.org/v1/systemone"
    assert PROFILES["jevmodel"].api_key_env == "JEVMODEL_API_KEY"
    assert PROFILES["jevmodel"].max_questions_per_call == 8
    assert PROFILES["jevmodel"].max_choice_options == 20
    assert PROFILES["clef-ollama"].api_key_env is None
    assert PROFILES["fake"].endpoint.startswith("fake://")
