from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .presentation import frequency_display
from .repository import PanelRepository
from .routing import PanelRoutingInput, RouteDecision, resolve_route


SEARCH_FIELDS = (
    "gene",
    "omim_id",
    "disease_name_zh",
    "disease_name_en",
    "category_zh",
)

POPULATION_ORDER = {
    "Total": 0,
    "General Population": 1,
    "EAS": 2,
    "East Asian Population": 3,
}

CALCULATOR_POPULATION_ORDER = {
    "TOTAL": 0,
    "AFR": 1,
    "AMR": 2,
    "ASJ": 3,
    "EAS": 4,
    "FIN": 5,
    "MID": 6,
    "NFE": 7,
    "SAS": 8,
    "REMAINING": 9,
}

CALCULATOR_POPULATION_LABELS = {
    "TOTAL": "整體族群",
    "AFR": "非洲／非裔",
    "AMR": "拉丁裔／混合美洲",
    "ASJ": "阿什肯納茲猶太裔",
    "EAS": "東亞",
    "FIN": "芬蘭",
    "MID": "中東",
    "NFE": "歐洲（非芬蘭）",
    "SAS": "南亞",
    "REMAINING": "其他／未分類族群",
}

POPULATION_ALIASES = {
    "Total": "TOTAL",
    "General Population": "TOTAL",
    "General Population†": "TOTAL",
    "AFR": "AFR",
    "African / African American Population": "AFR",
    "African/African American Population": "AFR",
    "African American Population": "AFR",
    "African Population": "AFR",
    "AMR": "AMR",
    "Latino / Admixed American Population": "AMR",
    "Latino Population": "AMR",
    "ASJ": "ASJ",
    "Ashkenazi Jewish Population": "ASJ",
    "EAS": "EAS",
    "East Asian Population": "EAS",
    "FIN": "FIN",
    "Finnish Population": "FIN",
    "MID": "MID",
    "Middle Eastern Population": "MID",
    "Middle-Eastern Population": "MID",
    "NFE": "NFE",
    "Caucasian / European Population": "NFE",
    "European (Non-Finnish) Population": "NFE",
    "SAS": "SAS",
    "South Asian Population": "SAS",
    "South Asian/Indian Population": "SAS",
    "Remaining": "REMAINING",
}


@dataclass(frozen=True, slots=True)
class PopulationRate:
    code: str
    label: str
    denominator: float
    source_label: str
    source_population: str
    frequency_id: str

    @property
    def display_label(self) -> str:
        return f"{self.label}（1 / {self.denominator:,.0f}）"


def panel_label(record: dict[str, str]) -> str:
    return (
        f"{record['gene']} · {record['disease_name_zh']} "
        f"({record['disease_name_en']}) · OMIM {record['omim_id']}"
    )


def consumer_panel_records(records: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Return one customer-facing row per display entity.

    Display groups avoid duplicate choices such as HBA1 and HBA1/HBA2. They do
    not merge frequencies or reproductive risks.
    """

    grouped: dict[str, dict[str, str]] = {}
    standalone: list[dict[str, str]] = []
    for record in records:
        group_id = record.get("display_group_id", "").strip()
        if not group_id:
            standalone.append(record)
            continue
        current = grouped.get(group_id)
        if current is None or (
            "/" in record.get("gene", "") and "/" not in current.get("gene", "")
        ):
            grouped[group_id] = record
    return sorted(
        [*standalone, *grouped.values()],
        key=lambda record: (
            record["gene"].casefold(),
            record["disease_name_zh"].casefold(),
            record["omim_id"],
        ),
    )


def consumer_panel_label(record: dict[str, str]) -> str:
    return (
        f"{record['gene']} — {record['disease_name_zh']} "
        f"({record['disease_name_en']})"
    )


def filter_panel(
    records: Iterable[dict[str, str]],
    *,
    query: str = "",
    category: str | None = None,
) -> list[dict[str, str]]:
    needle = query.strip().casefold()
    selected: list[dict[str, str]] = []
    for record in records:
        if category and record["category_zh"] != category:
            continue
        if needle and not any(needle in record[field].casefold() for field in SEARCH_FIELDS):
            continue
        selected.append(record)
    return selected


def route_for_record(
    record: dict[str, str],
    *,
    scenario_complete: bool = True,
) -> RouteDecision:
    return resolve_route(
        PanelRoutingInput(
            model_type=record["model_type"],
            declared_route=record["calculator_route"],
            special_case_type=record["special_case_type"] or None,
            carrier_rate_usage=record["carrier_rate_usage"],
            assay_dr_status=record["assay_dr_status"],
            scenario_complete=scenario_complete,
        )
    )


def route_blockers(record: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    if record["calculator_route"] != "CALCULATE":
        blockers.append("尚未由母檔人工提升為 CALCULATE")
    if record["carrier_rate_usage"] != "RISK_INPUT":
        blockers.append("帶因率尚未核准作為風險計算輸入")
    if record["assay_dr_status"] != "VALIDATED":
        blockers.append("尚無匹配此檢測方法的有效 detection rate")
    return blockers


def frequency_evidence(
    repository: PanelRepository,
    record: dict[str, str],
) -> list[dict[str, str]]:
    genes = {record["gene"]}
    if record["display_group_id"]:
        genes.update(
            member["gene"]
            for member in repository.display_group_members(record["display_group_id"])
        )

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for gene in genes:
        for row in repository.frequencies_for(gene=gene):
            if row["frequency_id"] in seen:
                continue
            if not (row["raw_value"].strip() or row["denominator"].strip()):
                continue
            seen.add(row["frequency_id"])
            rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            POPULATION_ORDER.get(row["population"], 99),
            row["population"],
            row["source_label"],
            row["frequency_id"],
        ),
    )


def frequency_table(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "Gene": row["gene"],
            "族群": row["population"],
            "帶因率": frequency_display(row),
            "疾病範圍": row["disease_scope"],
            "來源": row["source_label"],
            "適用性註記": row["disease_applicability"] or "—",
        }
        for row in rows
    ]


def _exact_denominator(row: dict[str, str]) -> float | None:
    if row.get("relation", "").strip() not in {"", "="}:
        return None
    raw = row.get("denominator", "").strip()
    if not raw:
        return None
    try:
        denominator = float(raw)
    except ValueError:
        return None
    return denominator if denominator >= 1 else None


def _frequency_rank(row: dict[str, str], record: dict[str, str]) -> tuple[int, str]:
    source_sheet = row.get("source_sheet", "")
    disease_scope = row.get("disease_scope", "").strip().casefold()
    disease_name = record.get("disease_name_en", "").strip().casefold()
    if source_sheet == "GenIE原始" and disease_scope.startswith("gene-level"):
        return (0, row.get("frequency_id", ""))
    if disease_scope == disease_name:
        return (1, row.get("frequency_id", ""))
    if "Fulgent" in row.get("source_label", ""):
        return (2, row.get("frequency_id", ""))
    return (3, row.get("frequency_id", ""))


def calculation_population_rates(
    repository: PanelRepository,
    record: dict[str, str],
) -> list[PopulationRate]:
    """Select one exact master frequency per broad population.

    GenIE gene-level rows are the base source. Disease-matched and Fulgent rows
    fill populations absent from that base. Bounds such as ``<1/500`` are never
    converted into exact risk inputs.
    """

    candidates: dict[str, list[tuple[tuple[int, str], dict[str, str], float]]] = {}
    for row in frequency_evidence(repository, record):
        code = POPULATION_ALIASES.get(row.get("population", ""))
        denominator = _exact_denominator(row)
        if code is None or denominator is None:
            continue
        candidates.setdefault(code, []).append(
            (_frequency_rank(row, record), row, denominator)
        )

    rates: list[PopulationRate] = []
    for code, rows in candidates.items():
        _, row, denominator = min(rows, key=lambda item: item[0])
        rates.append(
            PopulationRate(
                code=code,
                label=CALCULATOR_POPULATION_LABELS[code],
                denominator=denominator,
                source_label=row.get("source_label", ""),
                source_population=row.get("population", ""),
                frequency_id=row.get("frequency_id", ""),
            )
        )
    return sorted(
        rates,
        key=lambda rate: (CALCULATOR_POPULATION_ORDER[rate.code], rate.frequency_id),
    )
