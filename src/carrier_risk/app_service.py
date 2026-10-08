from __future__ import annotations

from collections.abc import Iterable

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


def panel_label(record: dict[str, str]) -> str:
    return (
        f"{record['gene']} · {record['disease_name_zh']} "
        f"({record['disease_name_en']}) · OMIM {record['omim_id']}"
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
