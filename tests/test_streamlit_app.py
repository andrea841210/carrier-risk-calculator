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

from carrier_risk.models import TestStatus  # noqa: E402
from carrier_risk.workflows import XLinkedScenario  # noqa: E402


@unittest.skipIf(AppTest is None, "streamlit is not installed")
class StreamlitSmokeTests(unittest.TestCase):
    def test_default_page_renders_without_exception(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.tabs), 0)
        self.assertEqual(len(app.metric), 0)
        self.assertEqual([box.label for box in app.selectbox], ["疾病或基因關鍵字"])

    def test_smn1_selection_renders_special_route_and_evidence(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.selectbox[0].set_value("P0721").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.selectbox[0].value, "P0721")
        self.assertEqual(len(app.dataframe), 1)
        rendered = "\n".join(markdown.value for markdown in app.markdown)
        self.assertIn("此基因需使用專屬檢測方式", rendered)
        self.assertIn("SMN1 exon 7 copy-number", rendered)

    def test_standard_ar_record_renders_customer_inputs_and_default_risk(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.selectbox[0].set_value("P0001").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            [box.label for box in app.selectbox],
            ["疾病或基因關鍵字", "本人族群別", "配偶族群別"],
        )
        self.assertEqual(len(app.radio), 2)
        self.assertEqual(len(app.number_input), 0)
        rendered = "\n".join(markdown.value for markdown in app.markdown)
        self.assertIn("下一代罹病風險", rendered)
        # Taiwan-facing default is East Asian: 1 × (1/1321) × 1/4.
        self.assertIn("0.0189%", rendered)

    def test_negative_status_without_master_dr_stops_numeric_result(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.selectbox[0].set_value("P0001").run()
        app.radio[1].set_value(TestStatus.NOT_DETECTED).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("有效 detection rate" in warning.value for warning in app.warning)
        )
        rendered = "\n".join(markdown.value for markdown in app.markdown)
        self.assertNotIn("下一代罹病風險", rendered)

    def test_x_linked_known_female_is_inheritance_probability(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20).run()
        app.selectbox[0].set_value("P0011").run()
        app.selectbox[3].set_value(XLinkedScenario.KNOWN_FEMALE_INHERITANCE).run()
        self.assertEqual(len(app.exception), 0)
        rendered = "\n".join(markdown.value for markdown in app.markdown)
        self.assertIn("女胎遺傳母源變異的機率", rendered)
        self.assertIn("50.00%", rendered)
        self.assertTrue(
            any("不等同於女胎罹病風險" in caption.value for caption in app.caption)
        )


if __name__ == "__main__":
    unittest.main()
