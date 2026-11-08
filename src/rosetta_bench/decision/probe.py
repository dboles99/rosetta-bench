"""One-call capability probe: what does this provider actually return?

Sends the intake battery once over the corpus canary request with no transport
retries, and records the served model, the fields present in each answer, usage, the
token-balance header and the validation result. The API key never reaches the file."""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from rosetta_core.decision import AnswerBatch, ProviderError, assert_no_secrets, validate_batch

from .battery import intake_battery
from .masking import Masker
from .profiles import ProviderProfile
from .shadow import load_routing_corpus
from .systemone import SystemOneAdapter
from .transport import Transport


def run_probe(profile: ProviderProfile, transport: Transport, api_key: str | None, corpus_dir: Path, out_dir: Path) -> dict:
    routes, cases, _ = load_routing_corpus(corpus_dir)
    canary = next(case for case in cases if case.category == "obvious" and case.data_class == "synthetic")
    qset = intake_battery(routes)
    masker = Masker()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    state = {
        "objective": "Choose the workflow for this request from the listed routes.",
        "constraints": {"data_class": "synthetic"},
        "routes": {route["id"]: route["description"] for route in routes},
        "evidence": {"request.text": {"value": masker.mask_text(canary.request_text), "source": f"corpus:{canary.case_id}",
                                      "retrieved_at": now, "verified": False, "trusted": False}},
    }
    adapter = SystemOneAdapter(profile, transport, api_key=api_key, max_transport_retries=0)
    ask = adapter.ask(state, qset, context={"case_id": canary.case_id, "probe": True})
    result = ask.result
    fields = {}
    if ask.exchanges and ask.exchanges[-1]["status"] == 200:
        try:
            raw_answers = json.loads(ask.exchanges[-1]["response_body"]).get("answers", {})
            fields = {qid: sorted(raw) for qid, raw in raw_answers.items() if isinstance(raw, dict)}
        except (ValueError, AttributeError):
            fields = {}
    probe = {
        "schema": "rosetta-bench/probe@1",
        "created_at": now,
        "profile": profile.name,
        "endpoint": profile.endpoint,
        "requested_model": adapter.model,
        "served_model": result.served_model if isinstance(result, AnswerBatch) else None,
        "calls": ask.calls,
        "http_status": ask.exchanges[-1]["status"] if ask.exchanges else None,
        "elapsed_ms": ask.elapsed_ms,
        "input_tokens": ask.input_tokens,
        "tokens_remaining": ask.tokens_remaining,
        "fields": fields,
        "answers": {qid: asdict(a) for qid, a in result.answers.items()} if isinstance(result, AnswerBatch) else None,
        "violations": [asdict(v) for v in validate_batch(result, qset)] if isinstance(result, AnswerBatch) else None,
        "error": {"kind": result.kind.value, "detail": result.detail} if isinstance(result, ProviderError) else None,
        "question_set_hash": qset.content_hash(),
        "exchanges": ask.exchanges,
    }
    forbidden = masker.originals + ((api_key,) if api_key else ())
    assert_no_secrets(probe, forbidden=forbidden)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe.json").write_text(json.dumps(probe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return probe
