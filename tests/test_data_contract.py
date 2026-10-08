from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from carrier_risk.repository import PanelRepository  # noqa: E402
from validate_data import validate  # noqa: E402


class DataContractTests(unittest.TestCase):
    def test_full_data_package_validates(self):
        checks = validate(ROOT)
        self.assertGreaterEqual(len(checks), 10)

    def test_repository_finds_smn1(self):
        repository = PanelRepository(ROOT / "data" / "curated")
        records = repository.find_panel(gene="SMN1", omim_id="253300")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["calculator_route"], "DEAD_PAGE")

    def test_smn1_frequency_context_is_available(self):
        repository = PanelRepository(ROOT / "data" / "curated")
        records = list(repository.frequencies_for(gene="SMN1"))
        self.assertEqual(len(records), 8)


if __name__ == "__main__":
    unittest.main()

