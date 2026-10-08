from __future__ import annotations

from csv import DictReader
from pathlib import Path
from typing import Iterable


def default_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "curated"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(DictReader(handle))


class PanelRepository:
    def __init__(self, data_root: str | Path | None = None):
        self.data_root = Path(data_root) if data_root else default_data_root()
        self._panel: list[dict[str, str]] | None = None
        self._frequencies: list[dict[str, str]] | None = None

    @property
    def panel(self) -> list[dict[str, str]]:
        if self._panel is None:
            self._panel = _read_csv(self.data_root / "panel_review.csv")
        return self._panel

    @property
    def frequencies(self) -> list[dict[str, str]]:
        if self._frequencies is None:
            self._frequencies = _read_csv(self.data_root / "carrier_frequency.csv")
        return self._frequencies

    def find_panel(self, *, gene: str, omim_id: str | None = None) -> list[dict[str, str]]:
        normalized_gene = gene.strip().upper()
        return [
            row
            for row in self.panel
            if row["gene"].strip().upper() == normalized_gene
            and (omim_id is None or row["omim_id"] == str(omim_id))
        ]

    def frequencies_for(
        self,
        *,
        gene: str,
        population: str | None = None,
        source_label: str | None = None,
    ) -> Iterable[dict[str, str]]:
        normalized_gene = gene.strip().upper()
        for row in self.frequencies:
            if row["gene"].strip().upper() != normalized_gene:
                continue
            if population is not None and row["population"] != population:
                continue
            if source_label is not None and row["source_label"] != source_label:
                continue
            yield row

