import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import io
import random

st.set_page_config(page_title="Financial Dashboard", layout="wide", page_icon="💹",
                   initial_sidebar_state="expanded")

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #0a0e1a; }

/* 사이드바 */
[data-testid="stSidebar"] {
    background: rgba(13,17,30,0.95);
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* KPI 카드 */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 24px 28px;
    position: relative;
    overflow: hidden;
    transition: transform .2s, border-color .2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.16); }
.kpi-card::before {
    content:''; position:absolute; top:-40px; right:-40px;
    width:120px; height:120px; border-radius:50%;
    opacity:.08; filter:blur(30px);
}
.kpi-card.income::before  { background:#22d3ee; }
.kpi-card.expense::before { background:#f87171; }
.kpi-card.profit::before  { background:#34d399; }
.kpi-card.margin::before  { background:#a78bfa; }

.kpi-label { font-size:12px; font-weight:500; color:rgba(255,255,255,0.45); letter-spacing:.8px; text-transform:uppercase; margin-bottom:10px; }
.kpi-value { font-size:30px; font-weight:700; color:#fff; letter-spacing:-.5px; }
.kpi-delta { font-size:12px; margin-top:8px; font-weight:500; }
.kpi-delta.pos { color:#34d399; }
.kpi-delta.neg { color:#f87171; }
.kpi-icon { position:absolute; top:24px; right:24px; font-size:22px; opacity:.6; }

/* 차트 컨테이너 */
.chart-card {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 20px;
}
.chart-title { font-size:15px; font-weight:600; color:rgba(255,255,255,0.85); margin-bottom:4px; }
.chart-sub   { font-size:12px; color:rgba(255,255,255,0.35); margin-bottom:16px; }

/* 섹션 타이틀 */
.section-title { font-size:13px; font-weight:600; color:rgba(255,255,255,0.4); letter-spacing:1.2px; text-transform:uppercase; margin:8px 0 16px; }

/* 업로드 안내 */
.upload-guide {
    background: rgba(99,102,241,0.08);
    border: 1px dashed rgba(99,102,241,0.4);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    color: rgba(255,255,255,0.5);
    font-size:12px;
    line-height:1.7;
    margin-bottom:16px;
}

/* 데이터 에디터 래퍼 */
.editor-wrap {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    padding: 24px;
}
</style>
""", unsafe_allow_html=True)

# ── 샘플 데이터 ────────────────────────────────────────────────────────────
@st.cache_data
def get_sample_data():
    random.seed(42)
    categories = {
        "수입": ["제품 매출", "서비스 수수료", "컨설팅", "라이선스", "기타 수입"],
        "지출": ["인건비", "마케팅", "운영비", "임대료", "소모품"],
    }
    rows = []
    base = date(2025, 1, 1)
    for i in range(120):
        d = base + timedelta(days=i * 3)
        t = random.choice(["수입", "지출"])
        cat = random.choice(categories[t])
        amt = random.randint(200, 5000) * 1000 if t == "수입" else random.randint(100, 2000) * 1000
        rows.append({"날짜": d.strftime("%Y-%m-%d"), "유형": t, "카테고리": cat,
                     "금액": amt, "메모": ""})
    return pd.DataFrame(rows)

# ── 세션 상태 초기화 ───────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = get_sample_data()

# ── 유효성 검사 ────────────────────────────────────────────────────────────
REQUIRED_COLS = {"날짜", "유형", "카테고리", "금액"}

def validate(df: pd.DataFrame):
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        return False, f"누락된 컬럼: {', '.join(missing)}"
    if not pd.api.types.is_numeric_dtype(df["금액"]):
        try:
            df["금액"] = pd.to_numeric(df["금액"].astype(str).str.replace(",", ""), errors="raise")
        except:
            return False, "금액 컬럼에 숫자가 아닌 값이 있습니다."
    return True, df

# ── Excel 바이트 생성 ──────────────────────────────────────────────────────
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Financial Data")
    return buf.getvalue()

# ── 사이드바 ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💹 Financial Dashboard")
    st.markdown("---")

    st.markdown('<div class="section-title">데이터 업로드</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="upload-guide">
    📂 <b>Excel / CSV 업로드</b><br>
    필수 컬럼: <b>날짜, 유형, 카테고리, 금액</b><br>
    선택 컬럼: 메모<br>
    유형값: <b>수입 / 지출</b>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("파일 선택", type=["xlsx", "csv"], label_visibility="collapsed")
    if uploaded:
        merge_mode = st.radio("업로드 방식", ["기존 데이터 교체", "기존 데이터에 추가"], horizontal=True)
        if st.button("✅ 데이터 적용", use_container_width=True):
            with st.spinner("파일 처리 중..."):
                try:
                    raw = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
                    ok, result = validate(raw)
                    if ok:
                        if isinstance(result, pd.DataFrame):
                            raw = result
                        if merge_mode == "기존 데이터에 추가":
                            st.session_state.df = pd.concat([st.session_state.df, raw], ignore_index=True)
                        else:
                            st.session_state.df = raw
                        st.success(f"✅ {len(raw)}건 적용 완료!")
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")

    st.markdown("---")
    st.markdown('<div class="section-title">필터</div>', unsafe_allow_html=True)
    df_all = st.session_state.df.copy()
    df_all["날짜"] = pd.to_datetime(df_all["날짜"], errors="coerce")
    min_d = df_all["날짜"].min().date() if not df_all.empty else date(2025, 1, 1)
    max_d = df_all["날짜"].max().date() if not df_all.empty else date.today()
    date_range = st.date_input("기간", value=(min_d, max_d))
    type_filter = st.multiselect("유형", ["수입", "지출"], default=["수입", "지출"])

    st.markdown("---")
    dl_bytes = to_excel_bytes(st.session_state.df)
    st.download_button(
        label="📥 Excel 다운로드",
        data=dl_bytes,
        file_name=f"Financial_Report_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ── 데이터 필터링 ──────────────────────────────────────────────────────────
df = st.session_state.df.copy()
df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0)

if len(date_range) == 2:
    s, e = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["날짜"] >= s) & (df["날짜"] <= e)]
if type_filter:
    df = df[df["유형"].isin(type_filter)]

income  = df[df["유형"] == "수입"]["금액"].sum()
expense = df[df["유형"] == "지출"]["금액"].sum()
profit  = income - expense
margin  = (profit / income * 100) if income > 0 else 0

# ── KPI 카드 ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card income">
    <div class="kpi-icon">💰</div>
    <div class="kpi-label">총 수입</div>
    <div class="kpi-value">₩{income:,.0f}</div>
    <div class="kpi-delta pos">▲ 전월 대비 +12.4%</div>
  </div>
  <div class="kpi-card expense">
    <div class="kpi-icon">📤</div>
    <div class="kpi-label">총 지출</div>
    <div class="kpi-value">₩{expense:,.0f}</div>
    <div class="kpi-delta neg">▲ 전월 대비 +3.1%</div>
  </div>
  <div class="kpi-card profit">
    <div class="kpi-icon">📈</div>
    <div class="kpi-label">순이익</div>
    <div class="kpi-value">₩{profit:,.0f}</div>
    <div class="kpi-delta {'pos' if profit>=0 else 'neg'}">{'▲' if profit>=0 else '▼'} 수익 {'흑자' if profit>=0 else '적자'}</div>
  </div>
  <div class="kpi-card margin">
    <div class="kpi-icon">🎯</div>
    <div class="kpi-label">마진율</div>
    <div class="kpi-value">{margin:.1f}%</div>
    <div class="kpi-delta {'pos' if margin>=30 else 'neg'}">{'▲ 목표 달성' if margin>=30 else '▼ 목표 미달 (30%)'}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 차트 영역 ──────────────────────────────────────────────────────────────
col_chart, col_funnel = st.columns([2, 1], gap="medium")

with col_chart:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Cash Flow</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-sub">기간별 수입 / 지출 흐름</div>', unsafe_allow_html=True)

    if not df.empty:
        cf = df.copy()
        cf["월"] = cf["날짜"].dt.to_period("M").astype(str)
        cf_group = cf.groupby(["월", "유형"])["금액"].sum().reset_index()
        fig_cf = px.area(
            cf_group, x="월", y="금액", color="유형",
            color_discrete_map={"수입": "#22d3ee", "지출": "#f87171"},
            template="plotly_dark",
        )
        fig_cf.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(color="rgba(255,255,255,0.6)")),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
        )
        fig_cf.update_traces(line_width=2)
        st.plotly_chart(fig_cf, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("데이터가 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_funnel:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">영업 파이프라인</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-sub">카테고리별 수입 구성</div>', unsafe_allow_html=True)

    income_df = df[df["유형"] == "수입"].groupby("카테고리")["금액"].sum().reset_index()
    income_df = income_df.sort_values("금액", ascending=False)

    if not income_df.empty:
        fig_funnel = go.Figure(go.Funnel(
            y=income_df["카테고리"],
            x=income_df["금액"],
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(color=["#6366f1", "#22d3ee", "#34d399", "#f59e0b", "#f87171"][:len(income_df)]),
            connector=dict(line=dict(color="rgba(255,255,255,0.05)", width=1)),
        ))
        fig_funnel.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            font=dict(color="rgba(255,255,255,0.7)", size=11),
            yaxis=dict(tickfont=dict(color="rgba(255,255,255,0.5)")),
        )
        st.plotly_chart(fig_funnel, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("수입 데이터 없음")
    st.markdown("</div>", unsafe_allow_html=True)

# ── 데이터 에디터 ──────────────────────────────────────────────────────────
st.markdown('<div class="chart-card">', unsafe_allow_html=True)
st.markdown('<div class="chart-title">📋 데이터 편집</div>', unsafe_allow_html=True)
st.markdown('<div class="chart-sub">셀을 직접 클릭하여 수정 — 수정 사항이 차트에 실시간 반영됩니다</div>', unsafe_allow_html=True)

edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "날짜":   st.column_config.TextColumn("날짜", width="medium"),
        "유형":   st.column_config.SelectboxColumn("유형", options=["수입", "지출"], width="small"),
        "카테고리": st.column_config.TextColumn("카테고리", width="medium"),
        "금액":   st.column_config.NumberColumn("금액", format="₩%d", width="medium"),
        "메모":   st.column_config.TextColumn("메모", width="large"),
    },
    hide_index=True,
)

if not edited_df.equals(st.session_state.df):
    st.session_state.df = edited_df
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
