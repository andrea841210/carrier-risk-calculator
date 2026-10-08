from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .calculator import (
    CalculationUnavailable,
    ar_reproductive_risk,
    carrier_risk,
    x_linked_female_affected_risk,
    x_linked_female_inheritance_probability,
    x_linked_male_risk,
    x_linked_unknown_sex_risk,
)
from .models import CarrierRiskInput, TestStatus


class XLinkedScenario(str, Enum):
    KNOWN_MALE = "KNOWN_MALE"
    UNKNOWN_SEX = "UNKNOWN_SEX"
    KNOWN_FEMALE_INHERITANCE = "KNOWN_FEMALE_INHERITANCE"
    KNOWN_FEMALE_AFFECTED = "KNOWN_FEMALE_AFFECTED"


@dataclass(frozen=True, slots=True)
class PersonScenario:
    """Human-facing inputs for one carrier-risk calculation."""

    denominator: float
    test_status: TestStatus
    detection_rate: float | None = None

    def as_carrier_input(self) -> CarrierRiskInput:
        try:
            denominator = float(self.denominator)
        except (TypeError, ValueError) as exc:
            raise CalculationUnavailable("carrier-frequency denominator must be numeric") from exc
        if not math.isfinite(denominator) or denominator < 1:
            raise CalculationUnavailable("carrier-frequency denominator must be at least 1")
        return CarrierRiskInput(
            carrier_frequency=1.0 / denominator,
            test_status=TestStatus(self.test_status),
            detection_rate=self.detection_rate,
        )


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    output_code: str
    reproductive_risk: float
    mother_carrier_risk: float
    father_carrier_risk: float | None = None


def calculate_ar_scenario(
    mother: PersonScenario,
    father: PersonScenario,
) -> ScenarioResult:
    mother_input = mother.as_carrier_input()
    father_input = father.as_carrier_input()
    return ScenarioResult(
        output_code="AR_AFFECTED",
        reproductive_risk=ar_reproductive_risk(mother_input, father_input),
        mother_carrier_risk=carrier_risk(mother_input),
        father_carrier_risk=carrier_risk(father_input),
    )


def calculate_x_linked_scenario(
    mother: PersonScenario,
    scenario: XLinkedScenario,
    *,
    female_penetrance: float | None = None,
    father_variant_absent: bool = False,
) -> ScenarioResult:
    mother_input = mother.as_carrier_input()
    maternal_risk = carrier_risk(mother_input)
    scenario = XLinkedScenario(scenario)

    if scenario is XLinkedScenario.KNOWN_MALE:
        risk = x_linked_male_risk(mother_input)
        output_code = "XL_MALE_AFFECTED"
    elif scenario is XLinkedScenario.UNKNOWN_SEX:
        risk = x_linked_unknown_sex_risk(mother_input)
        output_code = "XL_AFFECTED_MALE_PREGNANCY"
    elif scenario is XLinkedScenario.KNOWN_FEMALE_INHERITANCE:
        risk = x_linked_female_inheritance_probability(mother_input)
        output_code = "XL_FEMALE_INHERITANCE"
    else:
        risk = x_linked_female_affected_risk(
            mother_input,
            female_penetrance,
            father_variant_absent=father_variant_absent,
        )
        output_code = "XL_FEMALE_AFFECTED"

    return ScenarioResult(
        output_code=output_code,
        reproductive_risk=risk,
        mother_carrier_risk=maternal_risk,
    )
