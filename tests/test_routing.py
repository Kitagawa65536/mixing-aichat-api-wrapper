from __future__ import annotations

import pytest

from app.workflow.routing import parse_route_decision


def test_parse_route_decision_accepts_json() -> None:
    decision = parse_route_decision('{"route":"actor","reason":"simple reply"}')

    assert decision.route == "actor"
    assert decision.reason == "simple reply"
    assert decision.risk_level is None


def test_parse_route_decision_accepts_json_code_fence() -> None:
    decision = parse_route_decision(
        """
```json
{"route":"director","reason":"scene planning"}
```
""".strip()
    )

    assert decision.route == "director"


def test_parse_route_decision_accepts_injection_route() -> None:
    decision = parse_route_decision(
        """
        {
          "route": "injection",
          "risk_level": 4,
          "matched_prompt": "ignore previous instructions",
          "reason": "tries to override the prompt"
        }
        """
    )

    assert decision.route == "injection"
    assert decision.risk_level == 4
    assert decision.matched_prompt == "ignore previous instructions"


def test_parse_route_decision_rejects_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_route_decision("route: actor")


def test_parse_route_decision_rejects_unknown_route() -> None:
    with pytest.raises(ValueError):
        parse_route_decision('{"route":"formatter","reason":"not yet supported"}')


def test_parse_route_decision_rejects_out_of_range_risk_level() -> None:
    with pytest.raises(ValueError):
        parse_route_decision('{"route":"injection","risk_level":6}')
