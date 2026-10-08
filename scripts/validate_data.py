#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURATED = DATA / "curated"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(name: str) -> list[dict[str, str]]:
    with (CURATED / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate(root: Path = ROOT) -> list[str]:
    manifest_path = root / "data" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    curated = root / "data" / "curated"

    def load(name: str) -> list[dict[str, str]]:
        with (curated / name).open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    panel = load("panel_review.csv")
    genes = load("gene_registry.csv")
    frequencies = load("carrier_frequency.csv")
    special = load("special_cases.csv")
    issues = load("review_issues.csv")
    sources = load("source_registry.csv")

    checks = []
    expected_counts = {
        "panel records": (len(panel), 721),
        "gene registry records": (len(genes), 684),
        "carrier frequency records": (len(frequencies), 8822),
        "special-case records": (len(special), 12),
        "review issue records": (len(issues), 273),
        "source registry records": (len(sources), 19),
    }
    for label, (actual, expected) in expected_counts.items():
        require(actual == expected, f"{label}: expected {expected}, found {actual}")
        checks.append(f"{label}={actual}")

    panel_ids = [row["panel_row_id"] for row in panel]
    frequency_ids = [row["frequency_id"] for row in frequencies]
    require(all(panel_ids), "panel_row_id contains blanks")
    require(len(set(panel_ids)) == len(panel_ids), "panel_row_id is not unique")
    require(all(frequency_ids), "frequency_id contains blanks")
    require(len(set(frequency_ids)) == len(frequency_ids), "frequency_id is not unique")

    valid_routes = {"CALCULATE", "HOLD", "DEAD_PAGE"}
    valid_models = {"STANDARD_AR", "STANDARD_XL", "SPECIAL_NGS_CHALLENGE", "OTHER_REVIEW"}
    require({row["calculator_route"] for row in panel} <= valid_routes, "invalid calculator route")
    require({row["model_type"] for row in panel} <= valid_models, "invalid model type")

    routes = Counter(row["calculator_route"] for row in panel)
    require(routes == Counter({"HOLD": 709, "DEAD_PAGE": 12}), f"unexpected route counts: {routes}")
    models = Counter(row["model_type"] for row in panel)
    require(
        models == Counter({"STANDARD_AR": 637, "STANDARD_XL": 72, "SPECIAL_NGS_CHALLENGE": 12}),
        f"unexpected model counts: {models}",
    )

    dead = [row for row in panel if row["calculator_route"] == "DEAD_PAGE"]
    require(all(row["model_type"] == "SPECIAL_NGS_CHALLENGE" for row in dead), "dead page model mismatch")
    require(all(row["carrier_rate_usage"] == "DISPLAY_ONLY" for row in dead), "dead page rate use mismatch")
    require(Counter(row["special_case_type"] for row in dead) == Counter({"FIXED_NO_CALC": 7, "HOLD_ASSAY": 5}), "special case count mismatch")

    for row in panel:
        if row["calculator_route"] == "CALCULATE":
            require(row["carrier_rate_usage"] == "RISK_INPUT", f"{row['panel_row_id']} lacks approved carrier rate")
            require(row["assay_dr_status"] == "VALIDATED", f"{row['panel_row_id']} lacks validated DR")
            require(row["model_type"] in {"STANDARD_AR", "STANDARD_XL"}, f"{row['panel_row_id']} is not a standard model")

    smn1 = [row for row in panel if row["gene"] == "SMN1"]
    require(len(smn1) == 1, "SMN1 panel row count mismatch")
    require(smn1[0]["panel_row_id"] == "P0721", "SMN1 panel ID mismatch")
    require(smn1[0]["omim_id"] == "253300", "SMN1 OMIM mismatch")
    require(smn1[0]["source_total_denominator"] == "54", "SMN1 total denominator mismatch")
    require(smn1[0]["source_east_asian_denominator"] == "59", "SMN1 East Asian denominator mismatch")
    require(smn1[0]["calculator_route"] == "DEAD_PAGE", "SMN1 must route to dead page")

    alpha = [row for row in panel if row["display_group_id"] == "ALPHA_THAL_604131"]
    require(len(alpha) == 2, "alpha-thalassemia display group must contain two rows")

    workbook_checks = manifest["source_workbook_checks"]
    require(len(workbook_checks) == 19, "expected 19 source workbook checks")
    require(all(row["status"] == "PASS" for row in workbook_checks), "source workbook contains a failed check")

    for relative, metadata in manifest["datasets"].items():
        path = root / relative
        require(path.exists(), f"missing dataset: {relative}")
        require(sha256(path) == metadata["sha256"], f"checksum mismatch: {relative}")

    require(not list(root.rglob("*.xlsx")), "source workbooks must not be committed inside the repository")
    checks.extend([
        "stable identifiers are unique",
        "route and model enums are valid",
        "dead-page gates are intact",
        "SMN1 integration is intact",
        "alpha-thalassemia display grouping is intact",
        "19 source workbook checks are PASS",
        "dataset checksums match the manifest",
    ])
    return checks


def main() -> int:
    checks = validate()
    print(f"Validation passed ({len(checks)} checks)")
    for check in checks:
        print(f"- {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

