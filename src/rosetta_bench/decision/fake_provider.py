"""SYNTHETIC offline System One server for wiring tests. It scores keyword overlap
between the request and each option description. It is not a model, and its numbers
are not evidence about Jev, clef or any decision model."""
import json
import re

from .transport import HttpResponse

_WORD = re.compile(r"[a-z][a-z0-9_]{3,}")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _evidence_text(state: dict) -> str:
    evidence = state.get("evidence", {}) if isinstance(state, dict) else {}
    return " ".join(str(item.get("value", "")) for item in evidence.values() if isinstance(item, dict))


class FakeSystemOne:
    def __init__(self, model: str = "fake-systemone-1", fit_bias: float = 0.0):
        self.model = model
        self.fit_bias = fit_bias  # a second fake with a different bias makes consensus testable

    def __call__(self, request: dict) -> HttpResponse:
        state = request.get("state", {})
        routes = state.get("routes", {}) if isinstance(state, dict) else {}
        answers = {}
        for qid, question in request.get("questions", {}).items():
            slot = re.search(r"_(r\d+)$", qid)
            items = state.get("items", {}) if isinstance(state, dict) else {}
            source = items.get(slot.group(1), {}) if slot and items else state  # batched states hold one item per slot
            words = _words(_evidence_text(source))
            best_route_overlap = max((len(words & _words(f"{rid} {desc}")) for rid, desc in routes.items()), default=0)
            base_qid = qid[: slot.start()] if slot and items else qid
            kind = question.get("type")
            if kind == "choice":
                options = question.get("criteria", {})
                weights = {opt: 0.2 + len(words & _words(f"{opt} {desc}")) for opt, desc in options.items()}
                total = sum(weights.values())
                probabilities = {opt: round(weight / total, 6) for opt, weight in weights.items()}
                selected = max(weights, key=lambda option: weights[option])  # ties go to the first listed option
                n = len(options)
                confidence = (probabilities[selected] - 1 / n) / (1 - 1 / n)
                answers[qid] = {"type": "choice", "choice": selected, "probabilities": probabilities, "confidence": round(confidence, 6)}
            elif kind == "score":
                levels = question.get("criteria", [])
                n = len(levels)
                answers[qid] = {
                    "type": "score", "score": 1 + (n - 1) / 2, "legend": {str(i + 1): level for i, level in enumerate(levels)},
                    "probabilities": [round(1 / n, 6)] * n, "confidence": 0.0,
                }
            else:
                p_yes = min(0.95, 0.1 + self.fit_bias + 0.25 * best_route_overlap) if base_qid == "route_fits" else 0.5
                answers[qid] = {"type": "noul", "noul": round(p_yes, 6)}
        body = {"model": self.model, "answers": answers, "usage": {"input_tokens": len(json.dumps(request).split()), "output_tokens": 0}}
        return HttpResponse(200, {"content-type": "application/json"}, json.dumps(body).encode("utf-8"))
