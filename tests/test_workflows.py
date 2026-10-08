from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carrier_risk.calculator import CalculationUnavailable  # noqa: E402
from carrier_risk.models import TestStatus  # noqa: E402
from carrier_risk.workflows import (  # noqa: E402
    PersonScenario,
    XLinkedScenario,
    calculate_ar_scenario,
    calculate_x_linked_scenario,
)


class WorkflowTests(unittest.TestCase):
    def test_ar_scenario_returns_individual_and_reproductive_risks(self):
        result = calculate_ar_scenario(
            PersonScenario(100, TestStatus.DETECTED),
            PersonScenario(100, TestStatus.UNTESTED),
        )
        self.assertEqual(result.mother_carrier_risk, 1.0)
        self.assertEqual(result.father_carrier_risk, 0.01)
        self.assertEqual(result.reproductive_risk, 0.0025)

    def test_negative_scenario_uses_detection_rate_once(self):
        result = calculate_ar_scenario(
            PersonScenario(100, TestStatus.DETECTED),
            PersonScenario(100, TestStatus.NOT_DETECTED, 0.90),
        )
        expected_carrier_risk = 0.01 * 0.10 / (1 - 0.01 * 0.90)
        self.assertTrue(
            math.isclose(result.father_carrier_risk or 0, expected_carrier_risk, rel_tol=1e-15)
        )
        self.assertTrue(
            math.isclose(result.reproductive_risk, expected_carrier_risk * 0.25, rel_tol=1e-15)
        )

    def test_x_linked_known_female_is_inheritance_not_automatic_low_risk(self):
        result = calculate_x_linked_scenario(
            PersonScenario(100, TestStatus.DETECTED),
            XLinkedScenario.KNOWN_FEMALE_INHERITANCE,
        )
        self.assertEqual(result.output_code, "XL_FEMALE_INHERITANCE")
        self.assertEqual(result.reproductive_risk, 0.5)

    def test_x_linked_female_affected_requires_paternal_confirmation(self):
        with self.assertRaises(CalculationUnavailable):
            calculate_x_linked_scenario(
                PersonScenario(100, TestStatus.DETECTED),
                XLinkedScenario.KNOWN_FEMALE_AFFECTED,
                female_penetrance=0.20,
                father_variant_absent=False,
            )

    def test_x_linked_female_affected_uses_penetrance(self):
        result = calculate_x_linked_scenario(
            PersonScenario(100, TestStatus.DETECTED),
            XLinkedScenario.KNOWN_FEMALE_AFFECTED,
            female_penetrance=0.20,
            father_variant_absent=True,
        )
        self.assertEqual(result.reproductive_risk, 0.10)

    def test_denominator_must_be_valid(self):
        with self.assertRaises(CalculationUnavailable):
            PersonScenario(0, TestStatus.UNTESTED).as_carrier_input()


if __name__ == "__main__":
    unittest.main()
