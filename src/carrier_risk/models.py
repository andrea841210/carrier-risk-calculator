from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TestStatus(str, Enum):
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    UNTESTED = "UNTESTED"


@dataclass(frozen=True, slots=True)
class CarrierRiskInput:
    """Inputs required to derive one person's carrier risk.

    ``detection_rate`` is required only for ``NOT_DETECTED``. The caller is
    responsible for selecting a carrier frequency and detection rate that
    match the same population, assay, gene, disease, and variant class.
    """

    carrier_frequency: float
    test_status: TestStatus
    detection_rate: float | None = None

