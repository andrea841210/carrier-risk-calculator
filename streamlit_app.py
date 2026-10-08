from __future__ import annotations

import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from carrier_risk.app_service import (
    PopulationRate,
    calculation_population_rates,
    consumer_panel_label,
    consumer_panel_records,
    frequency_evidence,
    frequency_table,
    route_for_record,
)
from carrier_risk.calculator import CalculationUnavailable
from carrier_risk.models import TestStatus
from carrier_risk.presentation import format_probability
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
    page_title="帶因篩檢風險計算工具",
    page_icon="🧬",
    layout="centered",
    initial_sidebar_state="collapsed",
)


APP_CSS = """
<style>
    :root {
        --crc-primary: #f97316;
        --crc-primary-dark: #c2410c;
        --crc-primary-soft: #ffedd5;
        --crc-bg: #fff7ed;
        --crc-border: #fed7aa;
        --crc-text: #431407;
        --crc-muted: #78350f;
    }
    .stApp {
        background:
            radial-gradient(circle at 92% 4%, rgba(254, 215, 170, .72), transparent 28rem),
            var(--crc-bg);
        color: var(--crc-text);
    }
    .block-container {
        max-width: 780px;
        padding-top: 2.1rem;
        padding-bottom: 3rem;
    }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    .crc-header { text-align: center; margin: 0 auto 1.25rem; }
    .crc-header h1 {
        margin: 0 0 .35rem;
        color: var(--crc-primary-dark);
        font-size: clamp(1.7rem, 5vw, 2.35rem);
        line-height: 1.2;
        letter-spacing: -.02em;
    }
    .crc-header p {
        margin: 0;
        color: var(--crc-muted);
        font-size: .92rem;
        letter-spacing: .02em;
    }
    .crc-step {
        display: flex;
        align-items: center;
        gap: .55rem;
        margin: .2rem 0 .72rem;
        color: var(--crc-text);
        font-weight: 700;
        font-size: 1.02rem;
    }
    .crc-step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.55rem;
        height: 1.55rem;
        border-radius: 999px;
        background: var(--crc-primary);
        color: white;
        font-size: .78rem;
    }
    .crc-gene-card {
        margin: .95rem 0 .75rem;
        padding: 1rem 1.1rem;
        border: 1px solid var(--crc-border);
        border-radius: 12px;
        background: rgba(255,255,255,.92);
        box-shadow: 0 7px 24px rgba(194, 65, 12, .06);
    }
    .crc-gene-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }
    .crc-gene-symbol {
        color: var(--crc-primary-dark);
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .crc-disease-name { margin-top: .22rem; color: var(--crc-text); font-weight: 650; }
    .crc-disease-en { margin-top: .12rem; color: #8a5a43; font-size: .78rem; }
    .crc-mode-pill {
        flex: 0 0 auto;
        padding: .28rem .58rem;
        border-radius: 999px;
        background: var(--crc-primary-soft);
        color: var(--crc-primary-dark);
        font-size: .75rem;
        font-weight: 750;
    }
    .crc-empty, .crc-route-card {
        padding: 1.2rem 1.25rem;
        border-radius: 12px;
        line-height: 1.65;
    }
    .crc-empty {
        border: 1px dashed #fdba74;
        background: rgba(255,255,255,.55);
        color: #8a5a43;
        text-align: center;
    }
    .crc-route-card strong { display: block; margin-bottom: .28rem; font-size: 1.02rem; }
    .crc-hold { border-left: 5px solid #d97706; background: #fff7e8; color: #6b3b08; }
    .crc-special { border-left: 5px solid #be4b63; background: #fff1f3; color: #642637; }
    .crc-method {
        margin-top: .75rem;
        padding: .95rem 1rem;
        border: 1px solid #fecdd3;
        border-radius: 10px;
        background: white;
    }
    .crc-method-label {
        margin-bottom: .25rem;
        color: #9f1239;
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .04em;
    }
    .crc-parent-label { margin-bottom: .2rem; font-size: .98rem; font-weight: 750; }
    .crc-parent-label.mother { color: var(--crc-primary-dark); }
    .crc-parent-label.father { color: #0369a1; }
    .crc-result-card {
        margin-top: .65rem;
        padding: 1.25rem;
        border: 1px solid var(--crc-border);
        border-radius: 13px;
        background: #fff;
        text-align: center;
        box-shadow: 0 8px 26px rgba(194, 65, 12, .08);
    }
    .crc-result-label { color: var(--crc-muted); font-size: .9rem; }
    .crc-result-value {
        margin: .18rem 0 .08rem;
        color: var(--crc-primary-dark);
        font-size: clamp(2rem, 8vw, 3rem);
        font-weight: 800;
        line-height: 1.1;
    }
    .crc-result-fraction { color: var(--crc-primary); font-size: 1rem; font-weight: 650; }
    .crc-risk-details {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .55rem;
        margin-top: .85rem;
    }
    .crc-risk-detail {
        padding: .62rem;
        border-radius: 8px;
        background: #fafaf9;
        color: #57534e;
        font-size: .78rem;
    }
    .crc-risk-detail b { display: block; margin-top: .12rem; color: #292524; font-size: .9rem; }
    .crc-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(194, 65, 12, .15);
        color: #9a6a51;
        font-size: .76rem;
        line-height: 1.55;
        text-align: center;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--crc-border);
        border-radius: 12px;
        background: rgba(255,255,255,.9);
        box-shadow: 0 5px 18px rgba(194, 65, 12, .045);
    }
    div[data-baseweb="select"] > div, div[data-testid="stTextInput"] input {
        border-color: #fdba74;
        background: white;
    }
    div[data-baseweb="select"] > div:focus-within, div[data-testid="stTextInput"] input:focus {
        border-color: var(--crc-primary);
        box-shadow: 0 0 0 1px var(--crc-primary);
    }
    div[role="radiogroup"] { gap: .35rem; }
    div[role="radiogroup"] label {
        padding: .28rem .45rem;
        border: 1px solid #e7e5e4;
        border-radius: 7px;
        background: white;
    }
    div[data-testid="stDataFrame"] {
        overflow: hidden;
        border: 1px solid #f1d0b7;
        border-radius: 10px;
    }
    div[data-testid="stExpander"] {
        border-color: #f1d0b7;
        background: rgba(255,255,255,.68);
    }
    @media (max-width: 640px) {
        .block-container { padding: 1.25rem .9rem 2rem; }
        .crc-gene-row { flex-direction: column; gap: .55rem; }
        .crc-risk-details { grid-template-columns: 1fr; }
        div[role="radiogroup"] { align-items: stretch; }
    }
</style>
"""


STATUS_LABELS = {
    TestStatus.DETECTED: "已檢出（帶因）",
    TestStatus.NOT_DETECTED: "已檢測未檢出",
    TestStatus.UNTESTED: "尚未檢測",
}

INHERITANCE_LABELS = {
    "AR": "體染色體隱性",
    "XL": "X 染色體性聯",
    "Mi": "粒線體遺傳",
    "待確認": "遺傳模式待確認",
}

XL_SCENARIO_LABELS = {
    XLinkedScenario.UNKNOWN_SEX: "胎兒性別未知",
    XLinkedScenario.KNOWN_MALE: "已知男胎",
    XLinkedScenario.KNOWN_FEMALE_INHERITANCE: "已知女胎",
}

OUTPUT_LABELS = {
    "AR_AFFECTED": "下一代罹病風險",
    "XL_MALE_AFFECTED": "男胎罹病風險",
    "XL_AFFECTED_MALE_PREGNANCY": "患病男胎妊娠風險",
    "XL_FEMALE_INHERITANCE": "女胎遺傳母源變異的機率",
    "XL_FEMALE_AFFECTED": "女胎罹病風險",
}


@st.cache_resource
def load_repository() -> PanelRepository:
    return PanelRepository(ROOT / "data" / "curated")


def render_header() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="crc-header">
          <h1>帶因篩檢風險計算工具</h1>
          <p>Carrier Screening Risk Calculator</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step(number: int, title: str) -> None:
    st.markdown(
        f'<div class="crc-step"><span class="crc-step-number">{number}</span>{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def render_gene_card(record: dict[str, str]) -> None:
    inheritance = INHERITANCE_LABELS.get(record["inheritance"], record["inheritance"])
    st.markdown(
        f"""
        <div class="crc-gene-card">
          <div class="crc-gene-row">
            <div>
              <div class="crc-gene-symbol">{escape(record['gene'])}</div>
              <div class="crc-disease-name">{escape(record['disease_name_zh'])}</div>
              <div class="crc-disease-en">{escape(record['disease_name_en'])}</div>
            </div>
            <div class="crc-mode-pill">{escape(inheritance)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_frequency_context(repository: PanelRepository, record: dict[str, str]) -> None:
    evidence = frequency_evidence(repository, record)
    if not evidence:
        st.caption("目前沒有可顯示的背景帶因率。")
        return
    st.dataframe(
        frequency_table(evidence),
        hide_index=True,
        width="stretch",
        height=min(330, 36 * (len(evidence) + 1)),
    )
    st.caption("僅供背景說明，不代表已核准作為本檢測的風險計算輸入。")


def render_special_route(repository: PanelRepository, record: dict[str, str]) -> None:
    method = record["recommended_method"] or "請依疾病與實驗室流程選擇專屬檢測方法。"
    st.markdown(
        f"""
        <div class="crc-route-card crc-special">
          <strong>此基因需使用專屬檢測方式</strong>
          現有帶因率可能來自 PCR、repeat analysis、MLPA、Sanger 或其他平台，
          不直接轉換為本 NGS／WES 檢測的剩餘風險。
          <div class="crc-method">
            <div class="crc-method-label">建議檢測方法</div>
            {escape(method)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("查看背景帶因率（僅供參考）", expanded=False):
        render_frequency_context(repository, record)


def render_hold_route(repository: PanelRepository, record: dict[str, str]) -> None:
    st.markdown(
        """
        <div class="crc-route-card crc-hold">
          <strong>此項目目前無法套用標準風險公式</strong>
          母檔中的遺傳模式或必要資料尚未完整，因此暫不顯示數值。
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("查看背景帶因率（僅供參考）", expanded=False):
        render_frequency_context(repository, record)


def validated_detection_rate(record: dict[str, str]) -> float | None:
    """Read the future numeric assay DR only after its status is validated."""

    if record.get("assay_dr_status") != "VALIDATED":
        return None
    raw = record.get("assay_detection_rate", "").strip()
    if not raw:
        return None
    if raw.endswith("%"):
        raw = raw[:-1].strip()
        scale = 100.0
    else:
        scale = 1.0
    try:
        value = float(raw) / scale
    except ValueError:
        return None
    return value if 0 <= value <= 1 else None


def person_input(
    *,
    prefix: str,
    heading: str,
    css_class: str,
    population_rates: list[PopulationRate],
    detection_rate: float | None,
    default_status: TestStatus,
) -> tuple[PersonScenario, PopulationRate]:
    st.markdown(
        f'<div class="crc-parent-label {css_class}">{escape(heading)}</div>',
        unsafe_allow_html=True,
    )
    rate_by_code = {rate.code: rate for rate in population_rates}
    population_codes = list(rate_by_code)
    default_population = "EAS" if "EAS" in rate_by_code else "TOTAL"
    population_code = st.selectbox(
        f"{heading}族群別",
        options=population_codes,
        index=population_codes.index(default_population)
        if default_population in population_codes
        else 0,
        format_func=lambda code: rate_by_code[code].display_label,
        key=f"{prefix}_population",
    )
    status = st.radio(
        f"{heading}檢測狀態",
        options=list(TestStatus),
        index=list(TestStatus).index(default_status),
        format_func=STATUS_LABELS.__getitem__,
        key=f"{prefix}_status",
    )
    selected_rate = rate_by_code[population_code]
    return (
        PersonScenario(
            denominator=selected_rate.denominator,
            test_status=status,
            detection_rate=detection_rate
            if status is TestStatus.NOT_DETECTED
            else None,
        ),
        selected_rate,
    )


def zh_one_in(value: str) -> str:
    if value == "0":
        return "0"
    return value.replace("1 in ", "約 1 / ")


def render_result_card(
    result: ScenarioResult,
    *,
    mother: PersonScenario,
    father: PersonScenario | None = None,
    mother_label: str = "女方",
    father_label: str = "男方",
) -> None:
    risk = format_probability(result.reproductive_risk)
    mother_risk = format_probability(result.mother_carrier_risk)
    detail_blocks = (
        f'<div class="crc-risk-detail">{escape(mother_label)}帶因風險'
        f'<b>{escape(mother_risk.percent)} · {escape(zh_one_in(mother_risk.one_in))}</b></div>'
    )
    if father is not None and result.father_carrier_risk is not None:
        father_risk = format_probability(result.father_carrier_risk)
        detail_blocks += (
            f'<div class="crc-risk-detail">{escape(father_label)}帶因風險'
            f'<b>{escape(father_risk.percent)} · {escape(zh_one_in(father_risk.one_in))}</b></div>'
        )
    st.markdown(
        f"""
        <div class="crc-result-card">
          <div class="crc-result-label">{escape(OUTPUT_LABELS[result.output_code])}</div>
          <div class="crc-result-value">{escape(risk.percent)}</div>
          <div class="crc-result-fraction">{escape(zh_one_in(risk.one_in))}</div>
          <div class="crc-risk-details">{detail_blocks}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if result.output_code == "XL_FEMALE_INHERITANCE":
        st.caption("女胎顯示的是遺傳母源變異的機率，不等同於女胎罹病風險。")


def render_calculation(
    repository: PanelRepository,
    record: dict[str, str],
) -> None:
    population_rates = calculation_population_rates(repository, record)
    if not population_rates:
        st.error("母檔沒有可作為精確輸入的帶因率，暫時無法計算。")
        return

    render_step(2, "選擇本人與配偶的族群及檢測狀態")
    detection_rate = validated_detection_rate(record)

    if record["inheritance"] == "AR":
        person_col, partner_col = st.columns(2)
        with person_col:
            with st.container(border=True):
                person, person_rate = person_input(
                    prefix="person",
                    heading="本人",
                    css_class="mother",
                    population_rates=population_rates,
                    detection_rate=detection_rate,
                    default_status=TestStatus.DETECTED,
                )
        with partner_col:
            with st.container(border=True):
                partner, partner_rate = person_input(
                    prefix="partner",
                    heading="配偶",
                    css_class="father",
                    population_rates=population_rates,
                    detection_rate=detection_rate,
                    default_status=TestStatus.UNTESTED,
                )
        if (
            person.test_status is TestStatus.NOT_DETECTED
            or partner.test_status is TestStatus.NOT_DETECTED
        ) and detection_rate is None:
            st.warning(
                "此情境包含「已檢測未檢出」，但母檔尚無本檢測的有效 detection rate，因此不顯示風險數值。"
            )
            return
        try:
            result = calculate_ar_scenario(person, partner)
        except CalculationUnavailable as exc:
            st.warning(str(exc))
            return
        render_step(3, "生育風險")
        render_result_card(
            result,
            mother=person,
            father=partner,
            mother_label="本人",
            father_label="配偶",
        )
        with st.expander("查看計算方式", expanded=False):
            st.code(
                "本人帶因風險 × 配偶帶因風險 × 1/4\n"
                f"本人族群：{person_rate.display_label}\n"
                f"配偶族群：{partner_rate.display_label}",
                language="text",
            )
        return

    if record["inheritance"] != "XL":
        st.info("此遺傳模式不適用標準 AR／XL 計算。")
        return

    person_role = st.radio(
        "本人為",
        options=["FEMALE", "MALE"],
        format_func=lambda value: "女方" if value == "FEMALE" else "男方",
        horizontal=True,
        key="person_role",
    )
    person_col, partner_col = st.columns(2)
    with person_col:
        with st.container(border=True):
            person, person_rate = person_input(
                prefix="person",
                heading="本人",
                css_class="mother",
                population_rates=population_rates,
                detection_rate=detection_rate,
                default_status=TestStatus.DETECTED,
            )
    with partner_col:
        with st.container(border=True):
            partner, partner_rate = person_input(
                prefix="partner",
                heading="配偶",
                css_class="father",
                population_rates=population_rates,
                detection_rate=detection_rate,
                default_status=TestStatus.UNTESTED,
            )

    if person_role == "FEMALE":
        female, female_rate, female_label = person, person_rate, "本人（女方）"
        male = partner
    else:
        female, female_rate, female_label = partner, partner_rate, "配偶（女方）"
        male = person

    scenario = st.selectbox(
        "胎兒情境",
        options=list(XL_SCENARIO_LABELS),
        format_func=XL_SCENARIO_LABELS.__getitem__,
        key="xl_scenario",
    )
    st.caption("X-linked 標準公式依女方帶因風險與胎兒情境計算。")
    if male.test_status is TestStatus.DETECTED:
        st.warning("男方已檢出 X-linked 變異時需個別評估，無法套用本頁的標準公式。")
        return
    if female.test_status is TestStatus.NOT_DETECTED and detection_rate is None:
        st.warning(
            "女方為「已檢測未檢出」，但母檔尚無本檢測的有效 detection rate，因此不顯示風險數值。"
        )
        return
    try:
        result = calculate_x_linked_scenario(female, scenario)
    except CalculationUnavailable as exc:
        st.warning(str(exc))
        return
    render_step(3, "生育風險")
    render_result_card(result, mother=female, mother_label=female_label)
    with st.expander("查看計算方式", expanded=False):
        formula = {
            XLinkedScenario.KNOWN_MALE: "女方帶因風險 × 1/2",
            XLinkedScenario.UNKNOWN_SEX: "女方帶因風險 × 1/2 × 1/2",
            XLinkedScenario.KNOWN_FEMALE_INHERITANCE: "女方帶因風險 × 1/2",
        }[scenario]
        st.code(
            f"{formula}\n女方族群：{female_rate.display_label}",
            language="text",
        )


def main() -> None:
    repository = load_repository()
    records = consumer_panel_records(repository.panel)
    record_by_id = {record["panel_row_id"]: record for record in records}

    render_header()
    with st.container(border=True):
        render_step(1, "搜尋疾病或基因")
        selected_id = st.selectbox(
            "疾病或基因關鍵字",
            options=list(record_by_id),
            index=None,
            format_func=lambda row_id: consumer_panel_label(record_by_id[row_id]),
            placeholder="例如：囊性纖維化、CFTR、SMN1",
            help="可輸入 gene symbol 或疾病名稱篩選清單。",
            key="gene_selector",
        )
        if selected_id is None:
            st.markdown(
                '<div class="crc-empty">輸入疾病或 gene name，選擇本人與配偶資料後即可估算生育風險。</div>',
                unsafe_allow_html=True,
            )
        else:
            record = record_by_id[selected_id]
            render_gene_card(record)
            decision = route_for_record(record)
            if decision.route is CalculatorRoute.DEAD_PAGE:
                render_special_route(repository, record)
            elif record["model_type"] in {"STANDARD_AR", "STANDARD_XL"}:
                render_calculation(repository, record)
            else:
                render_hold_route(repository, record)

    st.markdown(
        """
        <div class="crc-footer">
          本工具依目前母檔的帶因率、檢測效能與遺傳模式估算風險。
          低風險不等於零風險；結果不取代遺傳諮詢或臨床診斷。
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
