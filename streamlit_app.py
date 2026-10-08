from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from carrier_risk.app_service import (
    filter_panel,
    frequency_evidence,
    frequency_table,
    panel_label,
    route_blockers,
    route_for_record,
)
from carrier_risk.calculator import CalculationUnavailable
from carrier_risk.models import TestStatus
from carrier_risk.presentation import carrier_formula, format_probability
from carrier_risk.repository import PanelRepository
from carrier_risk.routing import CalculatorRoute
from carrier_risk.workflows import (
    PersonScenario,
    ScenarioResult,
    XLinkedScenario,
    calculate_ar_scenario,
    calculate_x_linked_scenario,
)


st.set_page_config(
    page_title="Carrier Risk Calculator",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


APP_CSS = """
<style>
    .stApp { background: #f7f8fa; color: #182235; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
    .crc-hero {
        padding: 2rem 2.2rem;
        border-radius: 22px;
        background: linear-gradient(125deg, #132a45 0%, #203d5b 62%, #8b4c3b 150%);
        color: #fff;
        box-shadow: 0 18px 48px rgba(20, 42, 69, 0.16);
        margin-bottom: 1.2rem;
    }
    .crc-eyebrow { color: #e8b69f; font-size: .78rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
    .crc-title { font-size: clamp(2rem, 5vw, 3.25rem); font-weight: 760; line-height: 1.08; margin: .45rem 0 .65rem; }
    .crc-subtitle { max-width: 780px; color: #dbe5ef; font-size: 1.02rem; line-height: 1.65; }
    .crc-chip { display: inline-block; margin-top: 1.15rem; padding: .38rem .72rem; border: 1px solid rgba(255,255,255,.25); border-radius: 999px; color: #f6d6c7; font-size: .82rem; }
    .crc-status { padding: 1.05rem 1.2rem; border-radius: 14px; margin: .75rem 0 1.1rem; border-left: 5px solid; }
    .crc-status strong { display: block; margin-bottom: .2rem; }
    .crc-hold { background: #fff6e9; border-color: #d08a31; color: #5d3a0d; }
    .crc-dead { background: #f8edf0; border-color: #a04c62; color: #572432; }
    .crc-calculate { background: #eaf7f0; border-color: #2f8a61; color: #174b36; }
    .crc-note { padding: .95rem 1rem; background: #eef3f7; border-radius: 12px; color: #34475b; line-height: 1.55; }
    .crc-footer { margin-top: 2.6rem; padding-top: 1.2rem; border-top: 1px solid #dce2e8; color: #677586; font-size: .82rem; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e2e7ec; padding: .9rem 1rem; border-radius: 14px; }
    div[data-testid="stDataFrame"] { border: 1px solid #e2e7ec; border-radius: 12px; overflow: hidden; }
</style>
"""

STATUS_LABELS = {
    TestStatus.DETECTED: "已檢出致病／可能致病變異",
    TestStatus.NOT_DETECTED: "已檢測，未檢出",
    TestStatus.UNTESTED: "未檢測",
}

XL_SCENARIO_LABELS = {
    XLinkedScenario.KNOWN_MALE: "已知男胎：患病風險",
    XLinkedScenario.UNKNOWN_SEX: "胎兒性別未知：患病男胎妊娠風險",
    XLinkedScenario.KNOWN_FEMALE_INHERITANCE: "已知女胎：母源變異遺傳機率",
    XLinkedScenario.KNOWN_FEMALE_AFFECTED: "已知女胎：患病風險（需 penetrance）",
}

OUTPUT_LABELS = {
    "AR_AFFECTED": "每次妊娠的患病風險",
    "XL_MALE_AFFECTED": "已知男胎的患病風險",
    "XL_AFFECTED_MALE_PREGNANCY": "性別未知時的患病男胎妊娠風險",
    "XL_FEMALE_INHERITANCE": "已知女胎遺傳母源變異的機率",
    "XL_FEMALE_AFFECTED": "已知女胎的患病風險",
}


@st.cache_resource
def load_repository() -> PanelRepository:
    return PanelRepository(ROOT / "data" / "curated")


def render_header(repository: PanelRepository) -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <section class="crc-hero">
          <div class="crc-eyebrow">SDBT · Review prototype</div>
          <div class="crc-title">Carrier Risk Calculator</div>
          <div class="crc-subtitle">
            將疾病清單、族群帶因率、檢測限制與生育風險公式分層處理。
            數值計算只在資料與情境門檻完整時啟用。
          </div>
          <span class="crc-chip">v0.2 · Data-gated workflow</span>
        </section>
        """,
        unsafe_allow_html=True,
    )

    routes = {"HOLD": 0, "DEAD_PAGE": 0, "CALCULATE": 0}
    for record in repository.panel:
        routes[record["calculator_route"]] += 1
    columns = st.columns(4)
    columns[0].metric("Panel records", f"{len(repository.panel):,}")
    columns[1].metric("Carrier-rate evidence", f"{len(repository.frequencies):,}")
    columns[2].metric("Special handling", f"{routes['DEAD_PAGE']:,}")
    columns[3].metric("Production enabled", f"{routes['CALCULATE']:,}")


def render_route_card(route: CalculatorRoute) -> None:
    copy = {
        CalculatorRoute.HOLD: (
            "crc-hold",
            "HOLD · 尚未啟用數值計算",
            "可檢視既有證據與待補條件，但不產出生育風險。",
        ),
        CalculatorRoute.DEAD_PAGE: (
            "crc-dead",
            "SPECIAL · 非標準計算模型",
            "顯示既有帶因率與建議方法；不套用標準 AR／XL 公式。",
        ),
        CalculatorRoute.CALCULATE: (
            "crc-calculate",
            "CALCULATE · 資料門檻已通過",
            "此筆可在情境輸入完整後進入數值計算。",
        ),
    }
    css_class, title, message = copy[route]
    st.markdown(
        f'<div class="crc-status {css_class}"><strong>{title}</strong>{message}</div>',
        unsafe_allow_html=True,
    )


def render_frequency_evidence(repository: PanelRepository, record: dict[str, str]) -> None:
    evidence = frequency_evidence(repository, record)
    if not evidence:
        st.caption("目前沒有可顯示的帶因率證據列。")
        return
    st.dataframe(
        frequency_table(evidence),
        hide_index=True,
        width="stretch",
        height=min(440, 36 * (len(evidence) + 1)),
    )
    st.caption(
        "帶因率保留來源、族群與疾病範圍；顯示不代表已核准作為數值計算輸入。"
    )


def render_panel_explorer(repository: PanelRepository) -> None:
    st.subheader("Panel 分流檢視")
    st.caption("搜尋基因、疾病、OMIM 或分類，查看該筆目前應進入的介面路徑。")

    search_col, category_col = st.columns([2.2, 1])
    query = search_col.text_input(
        "搜尋",
        placeholder="例如 SMN1、脊髓性肌肉萎縮症、253300",
        key="panel_query",
    )
    category_options = ["全部分類", *repository.categories]
    category_value = category_col.selectbox(
        "疾病分類",
        category_options,
        key="panel_category",
    )
    category = None if category_value == "全部分類" else category_value
    records = filter_panel(repository.panel, query=query, category=category)
    st.caption(f"符合條件：{len(records):,} 筆")
    if not records:
        st.warning("找不到符合條件的 panel record。")
        return

    labels = {record["panel_row_id"]: panel_label(record) for record in records}
    panel_row_id = st.selectbox(
        "選擇疾病紀錄",
        options=[record["panel_row_id"] for record in records],
        format_func=labels.__getitem__,
        key="panel_record",
    )
    record = repository.panel_record(panel_row_id)
    decision = route_for_record(record)

    st.markdown("---")
    st.subheader(record["disease_name_zh"])
    st.caption(record["disease_name_en"])
    metadata = st.columns(4)
    metadata[0].metric("Gene", record["gene"])
    metadata[1].metric("Inheritance", record["inheritance"])
    metadata[2].metric("OMIM", record["omim_id"])
    metadata[3].metric("Category", record["category_zh"])
    render_route_card(decision.route)

    if decision.route is CalculatorRoute.DEAD_PAGE:
        st.markdown("#### 特殊處理")
        method_col, reason_col = st.columns(2)
        with method_col:
            st.markdown("**建議檢測方法**")
            st.write(record["recommended_method"] or "依疾病與實驗室流程個別確認")
        with reason_col:
            st.markdown("**不進入標準計算的原因**")
            st.write(record["review_rationale"] or decision.message)
        st.markdown(
            '<div class="crc-note">既有帶因率可作為背景資訊，但可能來自 PCR、repeat analysis、MLPA、Sanger 或其他平台；不直接轉換為本 NGS assay 的 residual risk。</div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### 可顯示的帶因率證據")
        render_frequency_evidence(repository, record)

    elif decision.route is CalculatorRoute.HOLD:
        st.markdown("#### 尚待完成")
        for blocker in route_blockers(record):
            st.markdown(f"- {blocker}")
        if record["calculation_enablement"]:
            st.info(record["calculation_enablement"])
        with st.expander("查看現有帶因率證據", expanded=False):
            render_frequency_evidence(repository, record)

    else:
        st.success("此筆已符合資料層計算門檻；情境計算可沿用下方『公式測試』工作流。")
        render_frequency_evidence(repository, record)

    with st.expander("資料治理欄位", expanded=False):
        governance = {
            "panel_row_id": record["panel_row_id"],
            "model_type": record["model_type"],
            "calculator_route": record["calculator_route"],
            "special_case_type": record["special_case_type"] or "—",
            "carrier_rate_usage": record["carrier_rate_usage"],
            "assay_dr_status": record["assay_dr_status"],
            "display_group_id": record["display_group_id"] or "—",
        }
        st.json(governance)


def person_controls(
    *,
    prefix: str,
    label: str,
    default_status: TestStatus,
) -> PersonScenario:
    st.markdown(f"#### {label}")
    denominator = st.number_input(
        "族群帶因率分母（1 / N）",
        min_value=1.0,
        value=100.0,
        step=1.0,
        key=f"{prefix}_denominator",
    )
    status = st.selectbox(
        "檢測狀態",
        options=list(TestStatus),
        index=list(TestStatus).index(default_status),
        format_func=STATUS_LABELS.__getitem__,
        key=f"{prefix}_status",
    )
    detection_rate = None
    if status is TestStatus.NOT_DETECTED:
        detection_rate_percent = st.number_input(
            "此 assay 的 detection rate（%）",
            min_value=0.0,
            max_value=100.0,
            value=95.0,
            step=0.1,
            key=f"{prefix}_dr",
        )
        detection_rate = detection_rate_percent / 100.0
    return PersonScenario(
        denominator=denominator,
        test_status=status,
        detection_rate=detection_rate,
    )


def result_formula(result: ScenarioResult) -> str:
    return {
        "AR_AFFECTED": "RR_AR = CR_mother × CR_father × 1/4",
        "XL_MALE_AFFECTED": "RR_male = CR_mother × 1/2",
        "XL_AFFECTED_MALE_PREGNANCY": "RR_unknown = CR_mother × 1/2 × 1/2",
        "XL_FEMALE_INHERITANCE": "P_female,inherit = CR_mother × 1/2",
        "XL_FEMALE_AFFECTED": "RR_female = CR_mother × 1/2 × Pen_female",
    }[result.output_code]


def render_result(
    result: ScenarioResult,
    *,
    mother: PersonScenario,
    father: PersonScenario | None = None,
) -> None:
    display = format_probability(result.reproductive_risk)
    st.markdown("---")
    st.markdown(f"### {OUTPUT_LABELS[result.output_code]}")
    result_columns = st.columns(3)
    result_columns[0].metric("Risk", display.percent)
    result_columns[1].metric("Equivalent", display.one_in)
    result_columns[2].metric("Decimal", display.decimal)

    carrier_columns = st.columns(2 if father is not None else 1)
    mother_display = format_probability(result.mother_carrier_risk)
    carrier_columns[0].metric(
        "Maternal carrier risk",
        mother_display.percent,
        help=mother_display.one_in,
    )
    if father is not None and result.father_carrier_risk is not None:
        father_display = format_probability(result.father_carrier_risk)
        carrier_columns[1].metric(
            "Paternal carrier risk",
            father_display.percent,
            help=father_display.one_in,
        )

    trace = [carrier_formula(mother.test_status, party="mother")]
    if father is not None:
        trace.append(carrier_formula(father.test_status, party="father"))
    trace.append(result_formula(result))
    st.code("\n".join(trace), language="text")
    st.caption("完整精度保留於計算層；百分比與 1 in N 僅為呈現格式。")


def render_formula_sandbox() -> None:
    st.subheader("公式測試")
    st.markdown(
        '<div class="crc-note">此區由使用者人工輸入 CF／DR，用於確認公式與情境互動；不會修改母檔，也不代表該基因已通過正式資料閘門。</div>',
        unsafe_allow_html=True,
    )
    model = st.radio(
        "遺傳模式",
        options=["AR", "XL"],
        horizontal=True,
        key="sandbox_model",
    )

    if model == "AR":
        mother_col, father_col = st.columns(2)
        with mother_col:
            mother = person_controls(
                prefix="ar_mother",
                label="母方",
                default_status=TestStatus.DETECTED,
            )
        with father_col:
            father = person_controls(
                prefix="ar_father",
                label="父方",
                default_status=TestStatus.UNTESTED,
            )
        try:
            result = calculate_ar_scenario(mother, father)
        except CalculationUnavailable as exc:
            st.error(str(exc))
        else:
            render_result(result, mother=mother, father=father)
        return

    mother_col, outcome_col = st.columns(2)
    with mother_col:
        mother = person_controls(
            prefix="xl_mother",
            label="母方",
            default_status=TestStatus.DETECTED,
        )
    with outcome_col:
        st.markdown("#### 胎兒／輸出情境")
        scenario = st.selectbox(
            "選擇輸出",
            options=list(XLinkedScenario),
            format_func=XL_SCENARIO_LABELS.__getitem__,
            key="xl_scenario",
        )
        father_variant_absent = False
        female_penetrance = None
        if scenario is XLinkedScenario.KNOWN_FEMALE_AFFECTED:
            father_variant_absent = st.checkbox(
                "已確認父方不存在本模型所需排除的變異",
                key="xl_father_absent",
            )
            penetrance_percent = st.number_input(
                "疾病特異的女性 penetrance（%）",
                min_value=0.0,
                max_value=100.0,
                value=20.0,
                step=0.1,
                key="xl_penetrance",
            )
            female_penetrance = penetrance_percent / 100.0

    try:
        result = calculate_x_linked_scenario(
            mother,
            scenario,
            female_penetrance=female_penetrance,
            father_variant_absent=father_variant_absent,
        )
    except CalculationUnavailable as exc:
        st.info(str(exc))
    else:
        render_result(result, mother=mother)


def render_methods() -> None:
    st.subheader("模型與使用邊界")
    st.markdown(
        """
| Route | 何時使用 | v0.2 行為 |
|---|---|---|
| `CALCULATE` | 標準 AR／XL，且 carrier rate、assay DR 與情境皆完整 | 回傳數值結果 |
| `HOLD` | 任一必要資料或人工核准尚未完成 | 顯示缺口，不計算 |
| `DEAD_PAGE` | repeat、CNV、同源基因、mtDNA 或其他 NGS challenge | 顯示帶因率背景與建議方法，不計算 |
        """
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### Individual carrier risk")
        st.code(
            "Detected: CR = 1\n"
            "Not detected: CR = CF × (1 − DR) / (1 − CF × DR)\n"
            "Untested: CR = CF",
            language="text",
        )
        st.markdown("#### Autosomal recessive")
        st.code("RR_AR = CR_mother × CR_father × 1/4", language="text")
    with right:
        st.markdown("#### X-linked")
        st.code(
            "Known male: CR_mother × 1/2\n"
            "Unknown sex: CR_mother × 1/4\n"
            "Known female inheritance: CR_mother × 1/2\n"
            "Known female affected: CR_mother × 1/2 × Pen_female",
            language="text",
        )
        st.warning("女胎不得統一標示為『極低』；若缺少必要條件，患病風險應標示為不可計算。")

    st.markdown("#### v0.2 snapshot")
    st.write(
        "目前母檔尚無正式 `CALCULATE` 紀錄；公式測試與 panel route 分開，避免人工輸入值被誤認為已核准的產品資料。"
    )


def main() -> None:
    repository = load_repository()
    render_header(repository)
    explorer_tab, sandbox_tab, methods_tab = st.tabs(
        ["01 · Panel 分流", "02 · 公式測試", "03 · 模型說明"]
    )
    with explorer_tab:
        render_panel_explorer(repository)
    with sandbox_tab:
        render_formula_sandbox()
    with methods_tab:
        render_methods()
    st.markdown(
        '<div class="crc-footer">Reference implementation · Not a clinical report, validated laboratory procedure, or substitute for genetic counseling.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
