from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carrier_risk.models import TestStatus  # noqa: E402
from carrier_risk.presentation import (  # noqa: E402
    carrier_formula,
    format_probability,
    frequency_display,
)


class PresentationTests(unittest.TestCase):
    def test_probability_has_percent_and_one_in_formats(self):
        display = format_probability(0.0025)
        self.assertEqual(display.percent, "0.2500%")
        self.assertEqual(display.one_in, "1 in 400")

    def test_zero_probability_is_explicit(self):
        display = format_probability(0)
        self.assertEqual(display.percent, "0%")
        self.assertEqual(display.one_in, "0")

    def test_integer_denominator_does_not_show_decimal_noise(self):
        display = format_probability(0.5)
        self.assertEqual(display.one_in, "1 in 2")

    def test_negative_formula_contains_residual_risk_once(self):
        formula = carrier_formula(TestStatus.NOT_DETECTED, party="mother")
        self.assertEqual(formula.count("1 − DR_mother"), 1)

    def test_frequency_bound_is_preserved(self):
        display = frequency_display(
            {"raw_value": "", "denominator": "50000", "relation": "<"}
        )
        self.assertEqual(display, "< 1 / 50,000")


if __name__ == "__main__":
    unittest.main()
