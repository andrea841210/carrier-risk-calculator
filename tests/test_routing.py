from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carrier_risk.routing import (  # noqa: E402
    CalculatorRoute,
    PanelRoutingInput,
    resolve_route,
)


class RoutingTests(unittest.TestCase):
    def record(self, **overrides) -> PanelRoutingInput:
        values = {
            "model_type": "STANDARD_AR",
            "declared_route": "CALCULATE",
            "special_case_type": None,
            "carrier_rate_usage": "RISK_INPUT",
            "assay_dr_status": "VALIDATED",
            "scenario_complete": True,
        }
        values.update(overrides)
        return PanelRoutingInput(**values)

    def test_ready_standard_record_calculates(self):
        decision = resolve_route(self.record())
        self.assertEqual(decision.route, CalculatorRoute.CALCULATE)
        self.assertEqual(decision.reason_code, "READY")

    def test_manual_hold_remains_hold(self):
        decision = resolve_route(self.record(declared_route="HOLD"))
        self.assertEqual(decision.route, CalculatorRoute.HOLD)
        self.assertEqual(decision.reason_code, "NOT_PROMOTED")

    def test_missing_validated_dr_holds(self):
        decision = resolve_route(self.record(assay_dr_status="MISSING"))
        self.assertEqual(decision.route, CalculatorRoute.HOLD)
        self.assertEqual(decision.reason_code, "ASSAY_DR_NOT_VALIDATED")

    def test_unapproved_carrier_rate_holds(self):
        decision = resolve_route(self.record(carrier_rate_usage="PENDING_VALIDATION"))
        self.assertEqual(decision.route, CalculatorRoute.HOLD)
        self.assertEqual(decision.reason_code, "CARRIER_RATE_NOT_APPROVED")

    def test_incomplete_scenario_holds(self):
        decision = resolve_route(self.record(scenario_complete=False))
        self.assertEqual(decision.route, CalculatorRoute.HOLD)
        self.assertEqual(decision.reason_code, "SCENARIO_INCOMPLETE")

    def test_fixed_special_case_always_uses_dead_page(self):
        decision = resolve_route(
            self.record(
                model_type="SPECIAL_NGS_CHALLENGE",
                declared_route="CALCULATE",
                special_case_type="FIXED_NO_CALC",
            )
        )
        self.assertEqual(decision.route, CalculatorRoute.DEAD_PAGE)

    def test_assay_dependent_special_case_uses_dead_page(self):
        decision = resolve_route(
            self.record(
                model_type="SPECIAL_NGS_CHALLENGE",
                declared_route="HOLD",
                special_case_type="HOLD_ASSAY",
            )
        )
        self.assertEqual(decision.route, CalculatorRoute.DEAD_PAGE)


if __name__ == "__main__":
    unittest.main()

