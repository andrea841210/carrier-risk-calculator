from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CalculatorRoute(str, Enum):
    CALCULATE = "CALCULATE"
    HOLD = "HOLD"
    DEAD_PAGE = "DEAD_PAGE"


class ModelType(str, Enum):
    STANDARD_AR = "STANDARD_AR"
    STANDARD_XL = "STANDARD_XL"
    SPECIAL_NGS_CHALLENGE = "SPECIAL_NGS_CHALLENGE"
    OTHER_REVIEW = "OTHER_REVIEW"


@dataclass(frozen=True, slots=True)
class PanelRoutingInput:
    model_type: str
    declared_route: str
    special_case_type: str | None
    carrier_rate_usage: str
    assay_dr_status: str
    scenario_complete: bool


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: CalculatorRoute
    reason_code: str
    message: str


def resolve_route(record: PanelRoutingInput) -> RouteDecision:
    """Resolve runtime behavior while preserving the manual release gate."""

    special = (record.special_case_type or "").strip()
    if record.model_type == ModelType.SPECIAL_NGS_CHALLENGE.value or special in {
        "FIXED_NO_CALC",
        "HOLD_ASSAY",
    }:
        return RouteDecision(
            CalculatorRoute.DEAD_PAGE,
            "SPECIAL_MODEL",
            "This record uses a non-standard or assay-dependent model.",
        )

    if record.declared_route == CalculatorRoute.DEAD_PAGE.value:
        return RouteDecision(
            CalculatorRoute.DEAD_PAGE,
            "MANUAL_DEAD_PAGE",
            "The curated record is explicitly routed to a dead page.",
        )

    if record.declared_route != CalculatorRoute.CALCULATE.value:
        return RouteDecision(
            CalculatorRoute.HOLD,
            "NOT_PROMOTED",
            "The curated record has not been promoted to CALCULATE.",
        )

    if record.model_type not in {
        ModelType.STANDARD_AR.value,
        ModelType.STANDARD_XL.value,
    }:
        return RouteDecision(
            CalculatorRoute.HOLD,
            "MODEL_NOT_APPROVED",
            "Only approved standard AR or XL models may calculate.",
        )

    if record.carrier_rate_usage != "RISK_INPUT":
        return RouteDecision(
            CalculatorRoute.HOLD,
            "CARRIER_RATE_NOT_APPROVED",
            "Carrier frequency is not approved for risk input.",
        )

    if record.assay_dr_status != "VALIDATED":
        return RouteDecision(
            CalculatorRoute.HOLD,
            "ASSAY_DR_NOT_VALIDATED",
            "An applicable assay-specific detection rate has not been validated.",
        )

    if not record.scenario_complete:
        return RouteDecision(
            CalculatorRoute.HOLD,
            "SCENARIO_INCOMPLETE",
            "Required scenario inputs are incomplete.",
        )

    return RouteDecision(
        CalculatorRoute.CALCULATE,
        "READY",
        "All calculation gates are satisfied.",
    )

