from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carrier_risk.calculator import (  # noqa: E402
    CalculationUnavailable,
    ar_reproductive_risk,
    carrier_risk,
    residual_carrier_risk,
    x_linked_female_affected_risk,
    x_linked_female_inheritance_probability,
    x_linked_male_risk,
    x_linked_unknown_sex_risk,
)
from carrier_risk.models import CarrierRiskInput, TestStatus  # noqa: E402


class CarrierRiskTests(unittest.TestCase):
    def test_detected_result_is_one(self):
        inputs = CarrierRiskInput(0.01, TestStatus.DETECTED)
        self.assertEqual(carrier_risk(inputs), 1.0)

    def test_untested_result_uses_carrier_frequency(self):
        inputs = CarrierRiskInput(1 / 100, TestStatus.UNTESTED)
        self.assertEqual(carrier_risk(inputs), 0.01)

    def test_negative_result_uses_bayesian_residual_risk(self):
        expected = 0.01 * (1 - 0.90) / (1 - 0.01 * 0.90)
        self.assertTrue(math.isclose(residual_carrier_risk(0.01, 0.90), expected, rel_tol=1e-15))

    def test_negative_result_requires_detection_rate(self):
        inputs = CarrierRiskInput(0.01, TestStatus.NOT_DETECTED)
        with self.assertRaises(CalculationUnavailable):
            carrier_risk(inputs)

    def test_detection_rate_boundary_one_is_supported(self):
        self.assertEqual(residual_carrier_risk(0.01, 1.0), 0.0)


class ReproductiveRiskTests(unittest.TestCase):
    def setUp(self):
        self.carrier = CarrierRiskInput(0.01, TestStatus.DETECTED)
        self.untested_one_in_100 = CarrierRiskInput(0.01, TestStatus.UNTESTED)

    def test_ar_two_confirmed_carriers(self):
        self.assertEqual(ar_reproductive_risk(self.carrier, self.carrier), 0.25)

    def test_ar_one_confirmed_carrier(self):
        self.assertEqual(ar_reproductive_risk(self.carrier, self.untested_one_in_100), 0.0025)

    def test_x_linked_known_male(self):
        self.assertEqual(x_linked_male_risk(self.carrier), 0.5)

    def test_x_linked_unknown_fetal_sex(self):
        self.assertEqual(x_linked_unknown_sex_risk(self.carrier), 0.25)

    def test_x_linked_known_female_inheritance(self):
        self.assertEqual(x_linked_female_inheritance_probability(self.carrier), 0.5)

    def test_x_linked_known_female_affected_risk(self):
        result = x_linked_female_affected_risk(
            self.carrier,
            0.20,
            father_variant_absent=True,
        )
        self.assertEqual(result, 0.10)

    def test_x_linked_female_affected_risk_requires_paternal_information(self):
        with self.assertRaises(CalculationUnavailable):
            x_linked_female_affected_risk(
                self.carrier,
                0.20,
                father_variant_absent=False,
            )

    def test_x_linked_female_affected_risk_requires_penetrance(self):
        with self.assertRaises(CalculationUnavailable):
            x_linked_female_affected_risk(
                self.carrier,
                None,
                father_variant_absent=True,
            )


if __name__ == "__main__":
    unittest.main()

