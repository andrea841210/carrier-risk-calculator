from __future__ import annotations

import math

from .models import CarrierRiskInput, TestStatus


class CalculationUnavailable(ValueError):
    """Raised when an approved calculation cannot be produced."""


def _probability(value: float, name: str, *, allow_zero: bool = True) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CalculationUnavailable(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise CalculationUnavailable(f"{name} must be finite")
    lower_ok = number >= 0 if allow_zero else number > 0
    if not lower_ok or number > 1:
        lower = "0" if allow_zero else "greater than 0"
        raise CalculationUnavailable(f"{name} must be {lower} and no greater than 1")
    return number


def residual_carrier_risk(carrier_frequency: float, detection_rate: float) -> float:
    """Return post-test carrier risk after a negative result.

    Formula: CF * (1 - DR) / (1 - CF * DR)
    """

    cf = _probability(carrier_frequency, "carrier_frequency", allow_zero=False)
    dr = _probability(detection_rate, "detection_rate")
    denominator = 1.0 - cf * dr
    if denominator <= 0:
        raise CalculationUnavailable("residual carrier risk is undefined for these inputs")
    return cf * (1.0 - dr) / denominator


def carrier_risk(inputs: CarrierRiskInput) -> float:
    """Return individual carrier risk for detected, negative, or untested status."""

    cf = _probability(inputs.carrier_frequency, "carrier_frequency", allow_zero=False)
    try:
        status = TestStatus(inputs.test_status)
    except ValueError as exc:
        raise CalculationUnavailable(f"unsupported test status: {inputs.test_status}") from exc

    if status is TestStatus.DETECTED:
        return 1.0
    if status is TestStatus.UNTESTED:
        return cf
    if inputs.detection_rate is None:
        raise CalculationUnavailable("validated detection_rate is required after a negative result")
    return residual_carrier_risk(cf, inputs.detection_rate)


def ar_reproductive_risk(mother: CarrierRiskInput, father: CarrierRiskInput) -> float:
    """Return per-pregnancy risk for the same autosomal recessive condition."""

    return carrier_risk(mother) * carrier_risk(father) * 0.25


def x_linked_male_risk(mother: CarrierRiskInput) -> float:
    """Return affected risk for a known male fetus under the baseline model."""

    return carrier_risk(mother) * 0.5


def x_linked_unknown_sex_risk(mother: CarrierRiskInput) -> float:
    """Return risk of an affected male pregnancy when fetal sex is unknown."""

    return carrier_risk(mother) * 0.5 * 0.5


def x_linked_female_inheritance_probability(mother: CarrierRiskInput) -> float:
    """Return probability that a known female fetus inherits the maternal variant."""

    return carrier_risk(mother) * 0.5


def x_linked_female_affected_risk(
    mother: CarrierRiskInput,
    female_penetrance: float | None,
    *,
    father_variant_absent: bool,
) -> float:
    """Return affected risk for a known female fetus when prerequisites are met."""

    if not father_variant_absent:
        raise CalculationUnavailable(
            "female affected risk requires confirmation that the father does not carry the modeled variant"
        )
    if female_penetrance is None:
        raise CalculationUnavailable("disease-specific female penetrance is required")
    penetrance = _probability(female_penetrance, "female_penetrance")
    return carrier_risk(mother) * 0.5 * penetrance

