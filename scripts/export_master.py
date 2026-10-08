#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_RE = re.compile(r"([A-Z]+)(\d+)")

PANEL_HEADERS = {
    "Panel列ID": "panel_row_id",
    "Gene": "gene",
    "工作OMIM": "omim_id",
    "工作疾病中文": "disease_name_zh",
    "工作Disease": "disease_name_en",
    "原分類（未改）": "category_zh",
    "工作遺傳模式": "inheritance",
    "遺傳模式依據": "inheritance_evidence",
    "審查分流": "review_track",
    "審查進度": "review_progress",
    "頻率適用判定": "frequency_applicability",
    "原Total分母": "source_total_denominator",
    "原EAS分母": "source_east_asian_denominator",
    "Fulgent候選原列": "fulgent_source_rows",
    "Jeen候選原列": "jeen_source_rows",
    "判定理由／下一步": "review_rationale",
    "Panel原始列": "panel_source_row",
    "原OMIM": "original_omim",
    "計算啟用狀態": "calculation_enablement",
    "Andrea決定": "owner_decision",
    "審查回覆": "review_response",
    "Model_type": "model_type",
    "Calculator_route": "calculator_route",
    "Special_case_type": "special_case_type",
    "Carrier_rate_usage": "carrier_rate_usage",
    "MGsafe_DR_status": "assay_dr_status",
    "Display_group_id": "display_group_id",
    "Recommended_method": "recommended_method",
}

GENE_HEADERS = {
    "Panel基因字串": "panel_gene",
    "HGNC現行符號": "hgnc_symbol",
    "名稱判定": "symbol_status",
    "HGNC ID": "hgnc_id",
    "Panel項目數": "panel_item_count",
    "GenIE原始列": "genie_source_rows",
    "Fulgent符號": "fulgent_symbol",
    "Fulgent原始列": "fulgent_source_rows",
    "Jeen符號": "jeen_symbol",
    "Jeen原始列": "jeen_source_rows",
    "Fulgent對接狀態": "fulgent_mapping_status",
    "HGNC來源連結": "hgnc_source_url",
    "適用界線": "applicability_boundary",
}

FREQUENCY_HEADERS = {
    "頻率ID": "frequency_id",
    "標準Gene": "gene",
    "來源疾病範圍": "disease_scope",
    "來源MOI": "inheritance",
    "來源族群（不混併）": "population",
    "原始值": "raw_value",
    "頻率關係符": "relation",
    "分母": "denominator",
    "頻率值或界限": "frequency",
    "數值型態": "value_type",
    "來源標記": "source_label",
    "原始分頁": "source_sheet",
    "原始列": "source_row",
    "來源註記": "source_note",
    "取值檢查": "extraction_check",
    "疾病適用狀態": "disease_applicability",
    "覆核回覆": "review_response",
}

ISSUE_HEADERS = {
    "問題ID+A1:I270": "issue_id",
    "Gene": "gene",
    "位置": "location",
    "問題類型": "issue_type",
    "證據": "evidence",
    "下一步": "next_step",
    "處理者": "owner",
    "處理狀態": "status",
    "回覆": "response",
}

SOURCE_HEADERS = {
    "來源ID": "source_id",
    "檔案／資源": "resource",
    "角色與範圍": "role_and_scope",
    "版本／擷取": "version_or_retrieval",
    "連結或校核依據": "url_or_verification_basis",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def column_index(ref: str) -> int:
    match = CELL_RE.fullmatch(ref)
    if not match:
        raise ValueError(f"invalid cell reference: {ref}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


class XlsxReader:
    """Small OOXML reader used because the source workbook uses prefixed namespaces."""

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def _shared_strings(zf: ZipFile) -> list[str]:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        return [
            "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
            for item in root.findall(f"{{{MAIN_NS}}}si")
        ]

    @staticmethod
    def _sheet_targets(zf: ZipFile) -> dict[str, str]:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
        }
        output = {}
        for sheet in workbook.find(f"{{{MAIN_NS}}}sheets"):
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = targets[rel_id].lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            output[sheet.attrib["name"]] = target
        return output

    @staticmethod
    def _cell_value(cell: ET.Element, strings: list[str]):
        cell_type = cell.attrib.get("t")
        value = cell.find(f"{{{MAIN_NS}}}v")
        if cell_type == "inlineStr":
            inline = cell.find(f"{{{MAIN_NS}}}is")
            if inline is None:
                return ""
            return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))
        if value is None or value.text is None:
            return None
        raw = value.text
        if cell_type == "s":
            return strings[int(raw)]
        if cell_type == "b":
            return raw == "1"
        if cell_type in {"str", "e"}:
            return raw
        try:
            number = float(raw)
            return int(number) if number.is_integer() else number
        except ValueError:
            return raw

    def rows(self, sheet_name: str) -> list[list[object]]:
        with ZipFile(self.path) as zf:
            strings = self._shared_strings(zf)
            target = self._sheet_targets(zf)[sheet_name]
            root = ET.fromstring(zf.read(target))
            sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
            if sheet_data is None:
                return []
            output = []
            for row in sheet_data.findall(f"{{{MAIN_NS}}}row"):
                cells = {
                    column_index(cell.attrib["r"]): self._cell_value(cell, strings)
                    for cell in row.findall(f"{{{MAIN_NS}}}c")
                }
                width = max(cells, default=0)
                output.append([cells.get(index) for index in range(1, width + 1)])
            return output


def normalized_rows(rows: list[list[object]]) -> tuple[list[str], list[list[object]]]:
    if not rows:
        return [], []
    width = max(len(row) for row in rows)
    header = list(rows[0]) + [None] * (width - len(rows[0]))
    headers = [
        str(value) if value not in {None, ""} else f"unnamed_{index}"
        for index, value in enumerate(header, start=1)
    ]
    data = []
    for row in rows[1:]:
        padded = list(row) + [None] * (width - len(row))
        if any(value not in {None, ""} for value in padded):
            data.append(padded)
    return headers, data


def write_csv(
    rows: list[list[object]],
    output_path: Path,
    header_map: dict[str, str] | None = None,
) -> tuple[list[str], list[dict[str, object]]]:
    headers, data = normalized_rows(rows)
    if header_map is not None:
        missing = [header for header in headers if header not in header_map]
        if missing:
            raise ValueError(f"missing header mapping for {output_path.name}: {missing}")
        headers = [header_map[header] for header in headers]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(data)
    records = [dict(zip(headers, row, strict=True)) for row in data]
    return headers, records


def write_records(records: list[dict[str, object]], fields: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def source_checks(reader: XlsxReader) -> list[dict[str, object]]:
    rows = reader.rows("資料檢查")
    if len(rows) < 3:
        return []
    headers = ["check_id", "check_name", "actual", "expected", "status", "note"]
    output = []
    for row in rows[2:]:
        padded = list(row) + [None] * (len(headers) - len(row))
        if padded[0]:
            output.append(dict(zip(headers, padded[: len(headers)], strict=True)))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the SDBT workbook to a versioned CSV data package.")
    parser.add_argument("source_workbook", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-date", default=date.today().isoformat())
    args = parser.parse_args()

    source = args.source_workbook.resolve()
    root = args.output_root.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    reader = XlsxReader(source)
    curated = root / "data" / "curated"
    raw = root / "data" / "raw"

    datasets: dict[str, dict[str, object]] = {}

    panel_path = curated / "panel_review.csv"
    _, panel = write_csv(reader.rows("Panel審查"), panel_path, PANEL_HEADERS)
    datasets[str(panel_path.relative_to(root))] = {"records": len(panel)}

    gene_path = curated / "gene_registry.csv"
    _, genes = write_csv(reader.rows("Gene對接"), gene_path, GENE_HEADERS)
    datasets[str(gene_path.relative_to(root))] = {"records": len(genes)}

    frequency_path = curated / "carrier_frequency.csv"
    _, frequencies = write_csv(reader.rows("頻率整理"), frequency_path, FREQUENCY_HEADERS)
    datasets[str(frequency_path.relative_to(root))] = {"records": len(frequencies)}

    issue_path = curated / "review_issues.csv"
    _, issues = write_csv(reader.rows("待辦"), issue_path, ISSUE_HEADERS)
    datasets[str(issue_path.relative_to(root))] = {"records": len(issues)}

    source_path = curated / "source_registry.csv"
    _, sources = write_csv(reader.rows("來源說明"), source_path, SOURCE_HEADERS)
    datasets[str(source_path.relative_to(root))] = {"records": len(sources)}

    special_fields = [
        "panel_row_id",
        "gene",
        "omim_id",
        "disease_name_zh",
        "disease_name_en",
        "inheritance",
        "source_total_denominator",
        "source_east_asian_denominator",
        "special_case_type",
        "carrier_rate_usage",
        "assay_dr_status",
        "display_group_id",
        "recommended_method",
        "review_rationale",
    ]
    special = [
        {field: row.get(field) for field in special_fields}
        for row in panel
        if row["calculator_route"] == "DEAD_PAGE"
    ]
    special_path = curated / "special_cases.csv"
    write_records(special, special_fields, special_path)
    datasets[str(special_path.relative_to(root))] = {"records": len(special)}

    for sheet_name, filename in {
        "Panel原始": "panel_raw.csv",
        "GenIE原始": "genie_raw.csv",
        "Fulgent原始": "fulgent_raw.csv",
        "Jeen原始": "jeen_raw.csv",
    }.items():
        path = raw / filename
        _, records = write_csv(reader.rows(sheet_name), path)
        datasets[str(path.relative_to(root))] = {"records": len(records), "source_sheet": sheet_name}

    for relative, metadata in datasets.items():
        metadata["sha256"] = sha256(root / relative)

    route_counts = Counter(row["calculator_route"] for row in panel)
    model_counts = Counter(row["model_type"] for row in panel)
    special_counts = Counter(row["special_case_type"] for row in special)
    checks = source_checks(reader)

    manifest = {
        "package_version": "0.1.0",
        "formula_specification_date": "2026-09-29",
        "build_date": args.build_date,
        "source": {
            "filename": source.name,
            "sha256": sha256(source),
        },
        "summary": {
            "panel_records": len(panel),
            "gene_registry_records": len(genes),
            "carrier_frequency_records": len(frequencies),
            "review_issue_records": len(issues),
            "source_registry_records": len(sources),
            "route_counts": dict(sorted(route_counts.items())),
            "model_counts": dict(sorted(model_counts.items())),
            "special_case_counts": dict(sorted(special_counts.items())),
        },
        "datasets": dict(sorted(datasets.items())),
        "source_workbook_checks": checks,
    }
    manifest_path = root / "data" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

