from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carrier_risk.app_service import (  # noqa: E402
    filter_panel,
    frequency_evidence,
    frequency_table,
    route_blockers,
    route_for_record,
)
from carrier_risk.repository import PanelRepository  # noqa: E402
from carrier_risk.routing import CalculatorRoute  # noqa: E402


class AppServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository = PanelRepository(ROOT / "data" / "curated")

    def test_search_matches_gene_disease_and_omim(self):
        by_gene = filter_panel(self.repository.panel, query="smn1")
        by_disease = filter_panel(self.repository.panel, query="脊髓性肌肉萎縮")
        by_omim = filter_panel(self.repository.panel, query="253300")
        self.assertEqual([row["panel_row_id"] for row in by_gene], ["P0721"])
        self.assertIn("P0721", [row["panel_row_id"] for row in by_disease])
        self.assertEqual([row["panel_row_id"] for row in by_omim], ["P0721"])

    def test_category_filter_is_exact(self):
        rows = filter_panel(self.repository.panel, category="心血管疾病")
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["category_zh"] == "心血管疾病" for row in rows))

    def test_smn1_routes_to_dead_page(self):
        record = self.repository.panel_record("P0721")
        self.assertEqual(route_for_record(record).route, CalculatorRoute.DEAD_PAGE)

    def test_hold_record_exposes_expected_blockers(self):
        record = self.repository.panel_record("P0001")
        blockers = route_blockers(record)
        self.assertEqual(len(blockers), 3)
        self.assertTrue(any("detection rate" in blocker for blocker in blockers))

    def test_display_group_can_borrow_frequency_context(self):
        record = self.repository.panel_record("P0311")
        evidence = frequency_evidence(self.repository, record)
        self.assertGreater(len(evidence), 0)
        self.assertTrue(any(row["gene"] == "HBA1" for row in evidence))

    def test_smn1_table_preserves_east_asian_rate(self):
        record = self.repository.panel_record("P0721")
        table = frequency_table(frequency_evidence(self.repository, record))
        east_asian = [row for row in table if row["族群"] == "East Asian Population"]
        self.assertEqual(len(east_asian), 1)
        self.assertEqual(east_asian[0]["帶因率"], "1 in 59")


if __name__ == "__main__":
    unittest.main()
