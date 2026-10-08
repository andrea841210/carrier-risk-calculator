from __future__ import annotations

import math
from dataclasses import dataclass

from .models import TestStatus


@dataclass(frozen=True, slots=True)
class ProbabilityDisplay:
    percent: str
    one_in: str
    decimal: str


def format_probability(value: float) -> ProbabilityDisplay:
    """Format a probability without changing calculation precision."""

    probability = float(value)
    if not math.isfinite(probability) or probability < 0 or probability > 1:
        raise ValueError("probability must be finite and between 0 and 1")
    if probability == 0:
        return ProbabilityDisplay("0%", "0", "0")

    percent_value = probability * 100
    if percent_value >= 1:
        percent = f"{percent_value:.2f}%"
    elif percent_value >= 0.01:
        percent = f"{percent_value:.4f}%"
    else:
        percent = f"{percent_value:.6f}%"

    denominator = 1.0 / probability
    if denominator.is_integer():
        one_in = f"1 in {denominator:,.0f}"
    elif denominator < 10:
        one_in = f"1 in {denominator:.2f}"
    else:
        one_in = f"1 in {denominator:,.0f}"
    return ProbabilityDisplay(percent, one_in, f"{probability:.10g}")


def carrier_formula(status: TestStatus, *, party: str = "person") -> str:
    status = TestStatus(status)
    if status is TestStatus.DETECTED:
        return f"CR_{party} = 1"
    if status is TestStatus.UNTESTED:
        return f"CR_{party} = CF_{party}"
    return f"CR_{party} = CF_{party} × (1 − DR_{party}) / (1 − CF_{party} × DR_{party})"


def frequency_display(row: dict[str, str]) -> str:
    raw_value = row.get("raw_value", "").strip()
    denominator = row.get("denominator", "").strip()
    relation = row.get("relation", "").strip()

    if raw_value and ("in" in raw_value.lower() or "/" in raw_value):
        return raw_value
    if denominator:
        prefix = "< " if relation == "<" else ""
        try:
            number = float(denominator)
            rendered = f"{number:,.0f}" if number.is_integer() else f"{number:g}"
        except ValueError:
            rendered = denominator
        return f"{prefix}1 / {rendered}"
    return raw_value or "—"
