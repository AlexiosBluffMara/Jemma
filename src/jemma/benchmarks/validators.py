from __future__ import annotations

import json

from jemma.core.types import BenchmarkScenario


def validate_response(scenario: BenchmarkScenario, response_text: str) -> tuple[bool, float, list[str]]:
    reasons: list[str] = []
    score = 1.0

    if scenario.validator == "exact_text":
        expected = scenario.expected or ""
        passed = response_text.strip() == expected.strip()
        if not passed:
            reasons.append(f"expected exact text {expected!r}")
            score = 0.0
        return passed, score, reasons

    if scenario.validator == "contains_all":
        missing = [item for item in scenario.expected_keywords if item not in response_text]
        if missing:
            reasons.append(f"missing keywords: {', '.join(missing)}")
            score = max(0.0, 1.0 - (len(missing) / max(len(scenario.expected_keywords), 1)))
        return not missing, score, reasons

    if scenario.validator == "json_object":
        text = response_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            return False, 0.0, [f"invalid json: {exc.msg}"]
        if not isinstance(parsed, dict):
            return False, 0.0, ["response is not a JSON object"]
        return True, 1.0, reasons

    reasons.append(f"unknown validator {scenario.validator!r}")
    return False, 0.0, reasons

