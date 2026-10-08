from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:  # pragma: no cover - dependency checked in the full app environment
    AppTest = None

from carrier_risk.workflows import XLinkedScenario  # noqa: E402


@unittest.skipIf(AppTest is None, "streamlit is not installed")
class StreamlitSmokeTests(unittest.TestCase):
    def test_default_page_renders_without_exception(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.tabs), 3)
        self.assertGreaterEqual(len(app.metric), 8)

    def test_smn1_search_renders_special_route_and_evidence(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.text_input[0].set_value("SMN1").run()
        self.assertEqual(len(app.exception), 0)
        record_selector = [box for box in app.selectbox if box.label == "選擇疾病紀錄"][0]
        self.assertEqual(record_selector.value, "P0721")
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("Spinal muscular atrophy", [caption.value for caption in app.caption])

    def test_x_linked_known_female_returns_inheritance_probability(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.radio[0].set_value("XL").run()
        scenario = [box for box in app.selectbox if box.label == "選擇輸出"][0]
        scenario.set_value(XLinkedScenario.KNOWN_FEMALE_INHERITANCE).run()
        self.assertEqual(len(app.exception), 0)
        risks = [metric.value for metric in app.metric if metric.label == "Risk"]
        self.assertEqual(risks, ["50.00%"])


if __name__ == "__main__":
    unittest.main()
