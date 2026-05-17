import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import sqlite3
import io
import base64
import json
import hashlib
from pathlib import Path
from PIL import Image as _PILImage

DEFAULT_ADMIN_PW_HASH = hashlib.sha256("0413".encode()).hexdigest()

_FAVICON_PATH = Path(__file__).parent / "data" / "favicon.png"
_SETTINGS_PATH_EARLY = Path(__file__).parent / "data" / "menu_settings.json"

def _load_early_settings():
    if _SETTINGS_PATH_EARLY.exists():
        try:
            d = json.loads(_SETTINGS_PATH_EARLY.read_text(encoding="utf-8"))
            return d.get("site_name", "화장품 유통 관리"), d.get("admin_pw_hash", DEFAULT_ADMIN_PW_HASH)
        except Exception:
            pass
    return "화장품 유통 관리", DEFAULT_ADMIN_PW_HASH

_page_title, _admin_pw_hash_init = _load_early_settings()
_page_icon  = _PILImage.open(_FAVICON_PATH) if _FAVICON_PATH.exists() else "💄"

st.set_page_config(page_title=_page_title, layout="wide", page_icon=_page_icon,
                   initial_sidebar_state="collapsed")

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:#0b0f1a}
[data-testid="stSidebar"]{background:#0d1117;border-right:1px solid rgba(255,255,255,0.07)}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.kpi{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
     border-radius:16px;padding:20px 24px;position:relative;overflow:hidden}
.kpi-label{font-size:11px;font-weight:600;color:rgba(255,255,255,0.4);
           letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px}
.kpi-value{font-size:26px;font-weight:700;color:#fff}
.kpi-sub{font-size:12px;margin-top:6px;color:rgba(255,255,255,0.4)}
.warn-banner{background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.4);
             border-radius:12px;padding:14px 20px;margin-bottom:16px;
             color:#fca5a5;font-size:14px;font-weight:500}
.card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
      border-radius:16px;padding:20px;margin-bottom:16px}
.card-title{font-size:14px;font-weight:600;color:rgba(255,255,255,0.8);margin-bottom:4px}
.card-sub{font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:14px}
.fifo-box{background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.3);
          border-radius:10px;padding:12px 16px;margin:10px 0;font-size:13px;color:#a5b4fc}
</style>
""", unsafe_allow_html=True)

# ── DB ─────────────────────────────────────────────────────────────────────
DB_PATH       = Path(__file__).parent / "data" / "cosmetics.db"
SETTINGS_PATH = Path(__file__).parent / "data" / "menu_settings.json"

DEFAULT_SITE_NAME    = "화장품 유통 관리"
DEFAULT_SITE_CAPTION = "바크로 · 물톡스 통합 관리"
DEFAULT_SITE_ICON    = "💄"

def load_menu_settings(default_menu, default_labels):
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            order   = data.get("order",        default_menu.copy())
            labels  = data.get("labels",       default_labels.copy())
            site    = data.get("site_name",    DEFAULT_SITE_NAME)
            caption = data.get("site_caption", DEFAULT_SITE_CAPTION)
            icon    = data.get("site_icon",    DEFAULT_SITE_ICON)
            for k in default_menu:
                if k not in labels:
                    labels[k] = k
            return order, labels, site, caption, icon
        except Exception:
            pass
    return default_menu.copy(), default_labels.copy(), DEFAULT_SITE_NAME, DEFAULT_SITE_CAPTION, DEFAULT_SITE_ICON

def save_menu_settings(order, labels, site_name=None, site_caption=None, site_icon=None, admin_pw_hash=None):
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    existing = {}
    if SETTINGS_PATH.exists():
        try:
            existing = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing["order"]         = order
    existing["labels"]        = labels
    existing["site_name"]     = site_name     if site_name     is not None else existing.get("site_name",     DEFAULT_SITE_NAME)
    existing["site_caption"]  = site_caption  if site_caption  is not None else existing.get("site_caption",  DEFAULT_SITE_CAPTION)
    existing["site_icon"]     = site_icon     if site_icon     is not None else existing.get("site_icon",     DEFAULT_SITE_ICON)
    existing["admin_pw_hash"] = admin_pw_hash if admin_pw_hash is not None else existing.get("admin_pw_hash", DEFAULT_ADMIN_PW_HASH)
    SETTINGS_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

CATEGORY_DISCOUNT = {
    "더데이랩스": 0.20,
    "루트스퀘어": 0.17,
    "비네트워크":  0.10,
}
CATEGORIES = ["", "더데이랩스", "루트스퀘어", "비네트워크"]

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            spec TEXT,
            purchase_price INTEGER DEFAULT 0,
            sale_price INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 10
        );
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            contact TEXT,
            phone TEXT,
            address TEXT,
            credit_limit INTEGER DEFAULT 0,
            discount_rate REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS stock_in (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 0,
            purchase_price INTEGER DEFAULT 0,
            lot_number TEXT,
            expiry_date TEXT,
            remaining_qty INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS stock_out (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            client_id INTEGER,
            product_id INTEGER,
            type TEXT DEFAULT '출고',
            quantity INTEGER DEFAULT 0,
            discount_rate REAL DEFAULT 0,
            supply_amount INTEGER DEFAULT 0,
            vat_amount INTEGER DEFAULT 0,
            total_amount INTEGER DEFAULT 0,
            fifo_purchase_price INTEGER DEFAULT 0,
            margin_amount INTEGER DEFAULT 0,
            margin_rate REAL DEFAULT 0,
            note TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            client_id INTEGER,
            amount INTEGER DEFAULT 0,
            linked_out_id INTEGER,
            note TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
    """)
    conn.commit()
    # 기존 DB에 category 컬럼 없으면 추가
    try:
        conn.execute("ALTER TABLE clients ADD COLUMN category TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.close()

def run_sql(query, params=()):
    conn = get_conn()
    df = pd.read_sql(query, conn, params=list(params))
    conn.close()
    return df

def execute(query, params=()):
    conn = get_conn()
    cur = conn.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def fmt(v):    return f"₩{int(v or 0):,}"
def days_left(s):
    try: return (datetime.strptime(s, "%Y-%m-%d").date() - date.today()).days
    except: return None

def expiry_badge(s):
    d = days_left(s)
    if d is None: return "⚪ 정보없음"
    if d < 0:  return "🔴 만료"
    if d <= 90: return "🟡 3개월 이내"
    return "🟢 안전"

# ── FIFO 계산 ──────────────────────────────────────────────────────────────
def get_fifo_info(product_id, qty_needed):
    lots = run_sql("""
        SELECT id, expiry_date, remaining_qty, purchase_price
        FROM stock_in
        WHERE product_id=? AND remaining_qty>0
        ORDER BY expiry_date ASC, date ASC
    """, (product_id,))
    if lots.empty or qty_needed <= 0:
        return 0, [], 0
    available = int(lots["remaining_qty"].sum())
    if qty_needed > available:
        return 0, [], available
    usage, remaining, total_cost = [], qty_needed, 0
    for _, lot in lots.iterrows():
        if remaining <= 0: break
        use = min(remaining, int(lot["remaining_qty"]))
        usage.append({"lot_id": int(lot["id"]), "use_qty": use, "price": int(lot["purchase_price"])})
        total_cost += use * int(lot["purchase_price"])
        remaining -= use
    avg_cost = int(total_cost / qty_needed)
    return avg_cost, usage, available

def apply_fifo(product_id, qty_needed):
    _, usage, _ = get_fifo_info(product_id, qty_needed)
    conn = get_conn()
    for u in usage:
        conn.execute("UPDATE stock_in SET remaining_qty=remaining_qty-? WHERE id=?",
                     (u["use_qty"], u["lot_id"]))
    conn.commit()
    conn.close()

def restore_fifo(out_id):
    conn = get_conn()
    row = conn.execute("SELECT product_id, quantity, type FROM stock_out WHERE id=?", (out_id,)).fetchone()
    if not row: conn.close(); return
    # 단순 복원: 가장 최근 lot에 반환
    conn.execute("""
        UPDATE stock_in SET remaining_qty=remaining_qty+?
        WHERE product_id=? AND id=(SELECT id FROM stock_in WHERE product_id=? ORDER BY expiry_date ASC LIMIT 1)
    """, (row["quantity"], row["product_id"], row["product_id"]))
    conn.commit(); conn.close()

# ══════════════════════════════════════════════════════════════════════════
# 대시보드
# ══════════════════════════════════════════════════════════════════════════
def page_dashboard():

    today      = date.today()
    today_str  = today.strftime("%Y-%m-%d")
    week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    this_month = today.strftime("%Y-%m")
    this_year  = today.strftime("%Y")

    def sales_sum(where, params=()):
        return run_sql(f"SELECT COALESCE(SUM(total_amount),0) as v FROM stock_out WHERE type='출고' AND {where}", params).iloc[0]["v"]

    today_sales  = sales_sum("date=?",              (today_str,))
    week_sales   = sales_sum("date BETWEEN ? AND ?", (week_start, today_str))
    month_sales  = sales_sum("date LIKE ?",          (f"{this_month}%",))
    year_sales   = sales_sum("date LIKE ?",          (f"{this_year}%",))

    total_recv   = run_sql("""
        SELECT COALESCE(SUM(o.total_amount),0)-COALESCE(SUM(p.amount),0) as v
        FROM stock_out o LEFT JOIN payments p ON p.client_id=o.client_id
        WHERE o.type='출고'
    """).iloc[0]["v"]
    month_margin = run_sql("SELECT COALESCE(AVG(margin_rate),0) as v FROM stock_out WHERE date LIKE ? AND type='출고'", (f"{this_month}%",)).iloc[0]["v"]
    low_stock_items = run_sql("""
        SELECT p.name as 제품명, COALESCE(s.rq,0) as 현재고, p.min_stock as 최소재고
        FROM products p
        LEFT JOIN (SELECT product_id, SUM(remaining_qty) as rq FROM stock_in GROUP BY product_id) s ON p.id=s.product_id
        WHERE COALESCE(s.rq,0) < p.min_stock
        ORDER BY COALESCE(s.rq,0) ASC
    """)
    low_stock_cnt = len(low_stock_items)

    # 매출 리포트
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">오늘 매출</div><div class="kpi-value">{fmt(today_sales)}</div><div class="kpi-sub">{today_str}</div></div>
      <div class="kpi"><div class="kpi-label">주간 매출</div><div class="kpi-value">{fmt(week_sales)}</div><div class="kpi-sub">{week_start} ~ {today_str}</div></div>
      <div class="kpi"><div class="kpi-label">월간 매출</div><div class="kpi-value">{fmt(month_sales)}</div><div class="kpi-sub">{this_month}</div></div>
      <div class="kpi"><div class="kpi-label">연간 매출</div><div class="kpi-value">{fmt(year_sales)}</div><div class="kpi-sub">{this_year}년</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 주요 현황
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">미수금 합계</div><div class="kpi-value">{fmt(total_recv)}</div><div class="kpi-sub">전체 누적</div></div>
      <div class="kpi"><div class="kpi-label">이번달 평균 마진율</div><div class="kpi-value">{month_margin:.1f}%</div><div class="kpi-sub">{this_month}</div></div>
      <div class="kpi"><div class="kpi-label">재고 부족 품목</div><div class="kpi-value">{low_stock_cnt}개</div><div class="kpi-sub">최소 재고 미달 ↓ 클릭</div></div>
    </div>
    """, unsafe_allow_html=True)

    if low_stock_cnt > 0:
        with st.expander(f"⚠️ 재고 부족 품목 {low_stock_cnt}개 — 상세 보기", expanded=False):
            st.dataframe(low_stock_items, use_container_width=True, hide_index=True)

    # 유통기한 경고 배너
    expiry_warn = run_sql("""
        SELECT p.name, s.expiry_date, SUM(s.remaining_qty) as qty
        FROM stock_in s JOIN products p ON s.product_id=p.id
        WHERE s.remaining_qty>0 AND s.expiry_date IS NOT NULL
          AND julianday(s.expiry_date)-julianday('now')<=90
        GROUP BY p.name, s.expiry_date ORDER BY s.expiry_date ASC
    """)
    if not expiry_warn.empty:
        items = " / ".join([f"{r['name']} ({r['expiry_date']}, {int(r['qty'])}개)" for _, r in expiry_warn.iterrows()])
        st.markdown(f'<div class="warn-banner">⚠️ 유통기한 임박 제품: {items}</div>', unsafe_allow_html=True)

    # 월별 / 연도별 그래프 나란히
    gcol1, gcol2 = st.columns(2, gap="medium")

    with gcol1:
        st.markdown('<div class="card"><div class="card-title">월별 매출 추이</div><div class="card-sub">출고 기준</div>', unsafe_allow_html=True)
        monthly = run_sql("""
            SELECT substr(date,1,7) as 월, SUM(total_amount) as 매출, SUM(margin_amount) as 마진
            FROM stock_out WHERE type='출고' GROUP BY 월 ORDER BY 월
        """)
        if not monthly.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["월"], y=monthly["매출"], name="매출", marker_color="#6366f1"))
            fig.add_trace(go.Scatter(x=monthly["월"], y=monthly["마진"], name="마진", line=dict(color="#34d399", width=2), yaxis="y2"))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              yaxis2=dict(overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
                              xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
                              yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
                              legend=dict(font=dict(color="rgba(255,255,255,0.6)")),
                              margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("출고 데이터가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)

    with gcol2:
        st.markdown('<div class="card"><div class="card-title">연도별 매출 추이</div><div class="card-sub">출고 기준</div>', unsafe_allow_html=True)
        yearly = run_sql("""
            SELECT substr(date,1,4) as 연도, SUM(total_amount) as 매출, SUM(margin_amount) as 마진
            FROM stock_out WHERE type='출고' GROUP BY 연도 ORDER BY 연도
        """)
        if not yearly.empty:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=yearly["연도"], y=yearly["매출"], name="매출", marker_color="#818cf8"))
            fig2.add_trace(go.Scatter(x=yearly["연도"], y=yearly["마진"], name="마진", line=dict(color="#34d399", width=2), yaxis="y2"))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               yaxis2=dict(overlaying="y", side="right", gridcolor="rgba(0,0,0,0)"),
                               xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
                               yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="rgba(255,255,255,0.4)")),
                               legend=dict(font=dict(color="rgba(255,255,255,0.6)")),
                               margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("출고 데이터가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 미수금 TOP 5
    st.markdown('<div class="card"><div class="card-title">미수금 TOP 5 거래처</div><div class="card-sub">높은 순</div>', unsafe_allow_html=True)
    top_recv = run_sql("""
        SELECT c.name, COALESCE(SUM(o.total_amount),0)-COALESCE(SUM(p.amount),0) as 미수금
        FROM clients c
        LEFT JOIN stock_out o ON c.id=o.client_id AND o.type='출고'
        LEFT JOIN payments p ON c.id=p.client_id
        GROUP BY c.id HAVING 미수금>0 ORDER BY 미수금 DESC LIMIT 5
    """)
    if not top_recv.empty:
        top_recv["미수금"] = top_recv["미수금"].apply(fmt)
        st.dataframe(top_recv, use_container_width=True, hide_index=True)
    else:
        st.success("미수금 없음")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# 매입/매출 입력
# ══════════════════════════════════════════════════════════════════════════
def page_stock_entry():
    tab1, tab2 = st.tabs(["📥 입고 등록", "📤 출고 등록"])

    products = run_sql("SELECT id, name, purchase_price, sale_price FROM products")
    clients  = run_sql("SELECT id, name, category, discount_rate FROM clients")

    # ── 입고 ──
    with tab1:
        if "in_cart" not in st.session_state:
            st.session_state.in_cart = []
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if products.empty:
            st.warning("먼저 제품을 등록해주세요.")
        else:
            in_date = st.date_input("입고일", value=date.today(), key="in_date")
            st.divider()
            st.markdown("**품목 추가**")
            c1, c2 = st.columns([3, 1])
            prod_sel = c1.selectbox("품목 선택", products["name"].tolist(), key="in_prod_sel")
            prod_row = products[products["name"] == prod_sel].iloc[0]
            ca, cb, cc, cd = st.columns(4)
            qty_add   = ca.number_input("수량", min_value=1, value=1, key="in_qty_add")
            price_add = cb.number_input("매입가", min_value=0,
                                        value=int(prod_row["purchase_price"]),
                                        step=100, key="in_price_add")
            lot_add   = cc.text_input("LOT번호", key="in_lot_add")
            exp_add   = cd.date_input("유통기한", key="in_exp_add")
            if st.button("➕ 목록에 추가", key="in_add_btn", use_container_width=True):
                st.session_state.in_cart.append({
                    "product_id": int(prod_row["id"]), "품목": prod_sel,
                    "수량": qty_add, "매입가": price_add, "LOT": lot_add,
                    "유통기한": str(exp_add), "소계": price_add * qty_add,
                }); st.rerun()
            if st.session_state.in_cart:
                st.divider()
                st.markdown("**입고 목록**")
                disp_in = pd.DataFrame(st.session_state.in_cart)[
                    ["품목", "수량", "매입가", "LOT", "유통기한", "소계"]].copy()
                disp_in.index = range(1, len(disp_in) + 1)
                disp_in["매입가"] = disp_in["매입가"].apply(fmt)
                disp_in["소계"]   = disp_in["소계"].apply(fmt)
                st.dataframe(disp_in, use_container_width=True)
                dc1, dc2 = st.columns([1, 3])
                del_i = dc1.number_input("삭제할 행 번호", min_value=1,
                                          max_value=len(st.session_state.in_cart),
                                          value=1, step=1, key="in_del_idx")
                if dc2.button("선택 행 삭제", key="in_del_btn"):
                    st.session_state.in_cart.pop(del_i - 1); st.rerun()
                st.metric("합계 매입금액", fmt(sum(i["소계"] for i in st.session_state.in_cart)))
                in_note = st.text_input("공통 메모", key="in_note_final")
                sb1, sb2 = st.columns(2)
                if sb1.button("✅ 입고 등록 완료", type="primary", use_container_width=True):
                    cnt = len(st.session_state.in_cart)
                    conn = get_conn()
                    for item in st.session_state.in_cart:
                        conn.execute("""INSERT INTO stock_in
                            (date,product_id,quantity,purchase_price,lot_number,expiry_date,remaining_qty,note)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (str(in_date), item["product_id"], item["수량"],
                             item["매입가"], item["LOT"], item["유통기한"],
                             item["수량"], in_note))
                    conn.commit(); conn.close()
                    st.session_state.in_cart = []
                    st.success(f"입고 등록 완료 — {cnt}개 품목"); st.rerun()
                if sb2.button("🗑 전체 초기화", use_container_width=True, key="in_clear"):
                    st.session_state.in_cart = []; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        recent_in = run_sql("""SELECT s.date as 날짜, p.name as 품목, s.quantity as 수량,
                                      s.purchase_price as 매입가, s.lot_number as LOT,
                                      s.expiry_date as 유통기한, s.remaining_qty as 잔여수량
                               FROM stock_in s JOIN products p ON s.product_id=p.id
                               ORDER BY s.date DESC LIMIT 30""")
        if not recent_in.empty:
            st.subheader("최근 입고 내역")
            st.dataframe(recent_in, use_container_width=True, hide_index=True)

    # ── 출고 ──
    with tab2:
        if "out_cart" not in st.session_state:
            st.session_state.out_cart = []
        if "out_last_client" not in st.session_state:
            st.session_state.out_last_client = None
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if clients.empty or products.empty:
            st.warning("거래처와 제품을 먼저 등록해주세요.")
        else:
            oc1, oc2 = st.columns(2)
            out_type = oc1.radio("유형", ["출고", "반품"], horizontal=True)
            out_date = oc2.date_input("날짜", value=date.today(), key="out_date")
            client_sel = oc1.selectbox("거래처", clients["name"].tolist(), key="out_client")
            client_row = clients[clients["name"] == client_sel].iloc[0]
            discount_rate = float(client_row["discount_rate"])
            cat_label = f"[{client_row['category']}] " if client_row.get("category") else ""
            oc2.info(f"{cat_label}할인율: **{discount_rate*100:.1f}%**")
            if st.session_state.out_last_client != client_sel:
                st.session_state.out_cart = []
                st.session_state.out_last_client = client_sel
            st.divider()
            st.markdown("**품목 추가**")
            prod_sel2 = st.selectbox("품목 선택", products["name"].tolist(), key="out_prod_sel")
            prod_row2 = products[products["name"] == prod_sel2].iloc[0]
            base_price2 = int(prod_row2["sale_price"])
            avail_db = int(run_sql(
                "SELECT COALESCE(SUM(remaining_qty),0) as v FROM stock_in WHERE product_id=?",
                (int(prod_row2["id"]),)).iloc[0]["v"])
            carted_qty = sum(i["수량"] for i in st.session_state.out_cart
                             if i["product_id"] == int(prod_row2["id"]))
            remaining_avail = max(0, avail_db - carted_qty)
            pc1, pc2 = st.columns([3, 1])
            qty_add2 = pc1.number_input("수량", min_value=1,
                                         max_value=max(1, remaining_avail),
                                         value=1, key="out_qty_add")
            pc2.metric("가용 재고", f"{remaining_avail}개")
            if remaining_avail <= 0:
                st.error("⚠️ 재고가 없습니다.")
            else:
                if carted_qty > 0:
                    st.caption(f"이미 {carted_qty}개 목록 추가됨 — FIFO 단가는 등록 시 재계산")
                avg_cost2, _, _ = get_fifo_info(int(prod_row2["id"]), qty_add2)
                disc_price2   = int(base_price2 * (1 - discount_rate))
                supply_amt2   = disc_price2 * qty_add2
                vat_amt2      = int(supply_amt2 * 0.1)
                total_amt2    = supply_amt2 + vat_amt2
                margin_unit2  = disc_price2 - avg_cost2
                margin_total2 = margin_unit2 * qty_add2
                margin_rate2  = (margin_unit2 / disc_price2 * 100) if disc_price2 > 0 else 0
                st.markdown(
                    f'<div class="fifo-box">FIFO 평균 매입가: <b>{fmt(avg_cost2)}</b> | '
                    f'할인 단가: <b>{fmt(disc_price2)}</b> | '
                    f'예상 마진율: <b>{margin_rate2:.1f}%</b></div>',
                    unsafe_allow_html=True)
                if margin_rate2 < 0:
                    st.error(f"🚨 마진율 음수 ({margin_rate2:.1f}%) — 확인 필요!")
                elif margin_rate2 < 10:
                    st.warning(f"⚠️ 마진율 낮음 ({margin_rate2:.1f}%)")
                if st.button("➕ 목록에 추가", key="out_add_btn", use_container_width=True):
                    st.session_state.out_cart.append({
                        "product_id": int(prod_row2["id"]), "품목": prod_sel2,
                        "수량": qty_add2, "FIFO매입가": avg_cost2,
                        "할인단가": disc_price2, "공급가액": supply_amt2,
                        "VAT": vat_amt2, "합계": total_amt2,
                        "마진액": margin_total2, "마진율": margin_rate2,
                        "discount_rate": discount_rate,
                    }); st.rerun()
            if st.session_state.out_cart:
                st.divider()
                st.markdown("**출고 목록**")
                disp_out = pd.DataFrame(st.session_state.out_cart)[
                    ["품목", "수량", "할인단가", "공급가액", "마진율"]].copy()
                disp_out.index = range(1, len(disp_out) + 1)
                disp_out["할인단가"] = disp_out["할인단가"].apply(fmt)
                disp_out["공급가액"] = disp_out["공급가액"].apply(fmt)
                disp_out["마진율"]   = disp_out["마진율"].apply(lambda x: f"{x:.1f}%")
                st.dataframe(disp_out, use_container_width=True)
                tot_supply = sum(i["공급가액"] for i in st.session_state.out_cart)
                tot_vat    = sum(i["VAT"]      for i in st.session_state.out_cart)
                tot_all    = sum(i["합계"]     for i in st.session_state.out_cart)
                tot_margin = sum(i["마진액"]   for i in st.session_state.out_cart)
                avg_mr = (tot_margin / tot_supply * 100) if tot_supply > 0 else 0
                sm1, sm2, sm3, sm4 = st.columns(4)
                sm1.metric("공급가액", fmt(tot_supply))
                sm2.metric("VAT",      fmt(tot_vat))
                sm3.metric("합계",     fmt(tot_all))
                sm4.metric("평균 마진율", f"{avg_mr:.1f}%")
                dc3, dc4 = st.columns([1, 3])
                del_j = dc3.number_input("삭제할 행 번호", min_value=1,
                                          max_value=len(st.session_state.out_cart),
                                          value=1, step=1, key="out_del_idx")
                if dc4.button("선택 행 삭제", key="out_del_btn"):
                    st.session_state.out_cart.pop(del_j - 1); st.rerun()
                out_note2 = st.text_input("메모", key="out_note_final")
                sb3, sb4 = st.columns(2)
                if sb3.button("✅ 출고 등록 완료", type="primary", use_container_width=True):
                    cnt2 = len(st.session_state.out_cart)
                    tot2 = sum(i["합계"] for i in st.session_state.out_cart)
                    conn = get_conn()
                    for item in st.session_state.out_cart:
                        conn.execute("""INSERT INTO stock_out
                            (date,client_id,product_id,type,quantity,discount_rate,
                             supply_amount,vat_amount,total_amount,fifo_purchase_price,
                             margin_amount,margin_rate,note)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (str(out_date), int(client_row["id"]), item["product_id"], out_type,
                             item["수량"], item["discount_rate"], item["공급가액"],
                             item["VAT"], item["합계"], item["FIFO매입가"],
                             item["마진액"], item["마진율"], out_note2))
                    conn.commit(); conn.close()
                    if out_type == "출고":
                        for item in st.session_state.out_cart:
                            apply_fifo(item["product_id"], item["수량"])
                    st.session_state.out_cart = []
                    st.success(f"출고 등록 완료 — {cnt2}개 품목 ({fmt(tot2)})"); st.rerun()
                if sb4.button("🗑 전체 초기화", use_container_width=True, key="out_clear"):
                    st.session_state.out_cart = []; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        recent_out = run_sql("""SELECT o.date as 날짜, c.name as 거래처, p.name as 품목,
                                       o.type as 유형, o.quantity as 수량,
                                       o.total_amount as 합계, o.margin_rate as 마진율
                                FROM stock_out o
                                JOIN clients c ON o.client_id=c.id
                                JOIN products p ON o.product_id=p.id
                                ORDER BY o.date DESC LIMIT 30""")
        if not recent_out.empty:
            st.subheader("최근 출고 내역")
            recent_out["합계"] = recent_out["합계"].apply(fmt)
            recent_out["마진율"] = recent_out["마진율"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(recent_out, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
# 미수금 현황
# ══════════════════════════════════════════════════════════════════════════
def page_receivables():

    # 공통 데이터 로드
    recv = run_sql("""
        SELECT c.id, c.name as 거래처,
               COALESCE(SUM(o.total_amount),0) as 총매출,
               COALESCE(SUM(p.amount),0) as 총수금
        FROM clients c
        LEFT JOIN stock_out o ON c.id=o.client_id AND o.type='출고'
        LEFT JOIN payments p ON c.id=p.client_id
        GROUP BY c.id ORDER BY (총매출-총수금) DESC
    """)
    recv["미수금"] = recv["총매출"] - recv["총수금"]
    total_recv = recv["미수금"].sum()
    st.metric("전체 미수금 합계", fmt(total_recv))

    tab1, tab2, tab3, tab4 = st.tabs(["🏥 의원별 미수금 현황", "💳 수금 등록", "📋 거래처 원장", "🥧 미수금 비중"])

    with tab1:
        display = recv[recv["미수금"] > 0].copy()
        if display.empty:
            st.success("미수금 없음")
        else:
            display["총매출"] = display["총매출"].apply(fmt)
            display["총수금"] = display["총수금"].apply(fmt)
            display["미수금"] = display["미수금"].apply(fmt)
            st.dataframe(display[["거래처","총매출","총수금","미수금"]],
                         use_container_width=True, hide_index=True)

    with tab2:
        clients_pay = run_sql("SELECT id, name FROM clients ORDER BY name")
        if clients_pay.empty:
            st.warning("거래처를 먼저 등록해주세요.")
        else:
            pay_client = st.selectbox("거래처", clients_pay["name"].tolist(), key="pay_sel_client")
            client_id  = int(clients_pay[clients_pay["name"]==pay_client].iloc[0]["id"])

            # 현재 미수금 표시
            row = recv[recv["거래처"] == pay_client]
            outstanding = int(row["미수금"].iloc[0]) if not row.empty else 0
            if outstanding > 0:
                st.info(f"현재 미수금: **{fmt(outstanding)}**")
            else:
                st.success("현재 미수금: 없음")

            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.form("form_pay"):
                col1, col2 = st.columns(2)
                pay_date   = col1.date_input("수금일", value=date.today())
                pay_amount = col2.number_input("수금액", min_value=0, step=10000)
                pay_note   = st.text_input("메모")
                if st.form_submit_button("✅ 수금 등록", use_container_width=True):
                    execute("INSERT INTO payments (date,client_id,amount,note) VALUES (?,?,?,?)",
                            (str(pay_date), client_id, pay_amount, pay_note))
                    st.success(f"수금 완료 — {pay_client} {fmt(pay_amount)}")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        clients_list = run_sql("SELECT id, name FROM clients")
        if clients_list.empty:
            st.info("거래처가 없습니다.")
        else:
            sel_client = st.selectbox("거래처 선택", clients_list["name"].tolist(), key="recv_sel_client")
            cid = int(clients_list[clients_list["name"]==sel_client].iloc[0]["id"])
            detail = run_sql("""
                SELECT date as 날짜, '출고' as 구분, total_amount as 금액, 0 as 수금액
                FROM stock_out WHERE client_id=? AND type='출고'
                UNION ALL
                SELECT date, '수금', 0, amount FROM payments WHERE client_id=?
                ORDER BY 날짜 ASC
            """, (cid, cid))
            if not detail.empty:
                detail["금액"]  = detail["금액"].apply(fmt)
                detail["수금액"] = detail["수금액"].apply(fmt)
                st.dataframe(detail, use_container_width=True, hide_index=True)
            else:
                st.info("거래 내역이 없습니다.")

    with tab4:
        pie_data = recv[recv["미수금"] > 0]
        if pie_data.empty:
            st.info("미수금 데이터 없음")
        else:
            fig = px.pie(pie_data, values="미수금", names="거래처",
                         title="거래처별 미수금 비중", template="plotly_dark",
                         color_discrete_sequence=px.colors.sequential.Plasma_r)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════════
# 유통기한 관리
# ══════════════════════════════════════════════════════════════════════════
def page_expiry():
    st.title("🧪 유통기한 관리")

    lots = run_sql("""
        SELECT p.name as 제품, s.lot_number as LOT, s.expiry_date as 유통기한,
               s.remaining_qty as 잔여수량
        FROM stock_in s JOIN products p ON s.product_id=p.id
        WHERE s.remaining_qty>0 AND s.expiry_date IS NOT NULL
        ORDER BY s.expiry_date ASC
    """)

    if lots.empty:
        st.info("유통기한 정보가 있는 재고가 없습니다.")
        return

    lots["상태"] = lots["유통기한"].apply(expiry_badge)
    lots["D-day"] = lots["유통기한"].apply(lambda x: days_left(x))

    expired  = lots[lots["D-day"] < 0]
    soon     = lots[(lots["D-day"] >= 0) & (lots["D-day"] <= 90)]
    safe     = lots[lots["D-day"] > 90]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 만료", f"{len(expired)}건")
    c2.metric("🟡 3개월 이내", f"{len(soon)}건")
    c3.metric("🟢 안전", f"{len(safe)}건")

    st.divider()

    if not expired.empty:
        st.error("🔴 만료된 재고")
        st.dataframe(expired.drop("D-day", axis=1), use_container_width=True, hide_index=True)

    if not soon.empty:
        st.warning("🟡 3개월 이내 만료 예정")
        st.dataframe(soon.drop("D-day", axis=1), use_container_width=True, hide_index=True)

    if not safe.empty:
        with st.expander("🟢 안전 재고 보기"):
            st.dataframe(safe.drop("D-day", axis=1), use_container_width=True, hide_index=True)

    # 바 차트
    fig = px.bar(lots.sort_values("D-day"), x="제품", y="잔여수량", color="상태",
                 color_discrete_map={"🔴 만료":"#ef4444","🟡 3개월 이내":"#f59e0b","🟢 안전":"#22c55e"},
                 template="plotly_dark", title="제품별 잔여 재고 현황")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=0,r=0,t=40,b=0))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════════════════════════════════════
# 기초 데이터 관리
# ══════════════════════════════════════════════════════════════════════════
def page_master():
    tab1, tab2 = st.tabs(["🏷️ 제품 관리", "🏢 거래처 관리"])

    with tab1:
        with st.expander("➕ 제품 등록"):
            with st.form("form_prod"):
                c1, c2 = st.columns(2)
                pname  = c1.text_input("제품명 *")
                spec   = c2.text_input("규격")
                minstk = st.number_input("최소 재고 알림 기준", min_value=0, value=10)
                if st.form_submit_button("등록"):
                    if pname:
                        execute("INSERT INTO products (name,spec,min_stock) VALUES (?,?,?)",
                                (pname, spec, minstk))
                        st.success("제품 등록 완료"); st.rerun()
        prods = run_sql("""
            SELECT p.id, p.name as 제품명, p.spec as 규격,
                   p.min_stock as 최소재고,
                   COALESCE(SUM(s.remaining_qty),0) as 현재고
            FROM products p LEFT JOIN stock_in s ON p.id=s.product_id
            GROUP BY p.id
        """)
        if not prods.empty:
            edited_prods = st.data_editor(
                prods.drop("id", axis=1),
                use_container_width=True, hide_index=True, num_rows="fixed",
                column_config={
                    "제품명":   st.column_config.TextColumn("제품명", disabled=True),
                    "규격":     st.column_config.TextColumn("규격", disabled=True),
                    "최소재고": st.column_config.NumberColumn("최소재고", min_value=0, step=1),
                    "현재고":   st.column_config.NumberColumn("현재고", disabled=True),
                },
            )
            if st.button("최소재고 저장", type="primary", key="save_minstk"):
                conn = get_conn()
                for i, row in edited_prods.iterrows():
                    conn.execute("UPDATE products SET min_stock=? WHERE id=?",
                                 (int(row["최소재고"]), int(prods.iloc[i]["id"])))
                conn.commit(); conn.close()
                st.success("최소재고 저장 완료!"); st.rerun()

    with tab2:
        with st.expander("➕ 거래처 등록"):
            with st.form("form_client"):
                r1c1, r1c2, r1c3 = st.columns([2, 1, 1])
                cname    = r1c1.text_input("거래처명 *")
                category = r1c2.selectbox("대분류", CATEGORIES,
                                          help="선택하면 기본 할인율 자동 적용")
                contact  = r1c3.text_input("담당자")
                r2c1, r2c2 = st.columns(2)
                phone   = r2c1.text_input("연락처")
                address = r2c2.text_input("주소")
                base_disc = int(CATEGORY_DISCOUNT.get(category, 0.17) * 100) if category else 17
                if category:
                    st.info(f"[{category}] 기본 할인율: {int(CATEGORY_DISCOUNT[category]*100)}%")
                disc = st.slider("세부 할인율 조정 (%)", 0, 50, base_disc,
                                 help="대분류 기본값에서 개별 조정 가능")
                if st.form_submit_button("등록", use_container_width=True):
                    if cname:
                        execute("""INSERT INTO clients
                                   (name,category,contact,phone,address,discount_rate)
                                   VALUES (?,?,?,?,?,?)""",
                                (cname, category, contact, phone, address, disc/100))
                        st.success(f"거래처 '{cname}' 등록 완료 (할인율 {disc}%)")
                        st.rerun()
        st.divider()
        st.subheader("등록된 거래처 수정")
        clients_df = run_sql("""
            SELECT id, name as 거래처명, category as 대분류,
                   contact as 담당자, phone as 연락처, address as 주소,
                   ROUND(discount_rate*100,1) as 할인율_PCT
            FROM clients ORDER BY name
        """)
        if not clients_df.empty:
            edited = st.data_editor(
                clients_df,
                use_container_width=True, hide_index=True, num_rows="fixed",
                column_config={
                    "id":         st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "거래처명":   st.column_config.TextColumn("거래처명", width="medium"),
                    "대분류":     st.column_config.SelectboxColumn("대분류", options=CATEGORIES, width="small"),
                    "담당자":     st.column_config.TextColumn("담당자", width="small"),
                    "연락처":     st.column_config.TextColumn("연락처", width="small"),
                    "주소":       st.column_config.TextColumn("주소", width="medium"),
                    "할인율_PCT": st.column_config.NumberColumn("할인율(%)", min_value=0, max_value=50,
                                                                step=0.5, width="small",
                                                                help="숫자 직접 입력 또는 대분류 변경 후 저장"),
                },
            )
            st.caption("* 대분류를 변경해도 할인율(%)은 자동 적용되지 않습니다. 할인율(%)을 직접 수정하거나 아래 버튼을 눌러주세요.")
            col_a, col_b = st.columns([1, 3])
            with col_a:
                if st.button("대분류 기본 할인율 일괄 적용", use_container_width=True):
                    for _, row in edited.iterrows():
                        cat = row["대분류"]
                        if cat and cat in CATEGORY_DISCOUNT:
                            edited.loc[edited["id"]==row["id"], "할인율_PCT"] = CATEGORY_DISCOUNT[cat]*100
            if st.button("변경사항 저장", type="primary", use_container_width=True):
                conn = get_conn()
                for _, row in edited.iterrows():
                    conn.execute("""UPDATE clients
                                    SET name=?, category=?, contact=?, phone=?, address=?,
                                        discount_rate=?
                                    WHERE id=?""",
                                 (row["거래처명"], row["대분류"] or "",
                                  row["담당자"] or "", row["연락처"] or "",
                                  row["주소"] or "", float(row["할인율_PCT"])/100,
                                  int(row["id"])))
                conn.commit(); conn.close()
                st.success("거래처 정보 저장 완료!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════════
init_db()

DEFAULT_MENU   = ["🏠 대시보드", "📦 매입 / 매출 입력", "💰 미수금 현황", "⚙️ 기초 데이터 관리"]
DEFAULT_LABELS = {k: k for k in DEFAULT_MENU}

if "menu_order" not in st.session_state or "menu_labels" not in st.session_state:
    _order, _labels, _site, _caption, _icon = load_menu_settings(DEFAULT_MENU, DEFAULT_LABELS)
    st.session_state.menu_order    = _order
    st.session_state.admin_pw_hash = _admin_pw_hash_init  # 앱 시작 시 파일에서 로드한 값 사용
    st.session_state.menu_labels   = _labels
    st.session_state.site_name     = _site
    st.session_state.site_caption  = _caption
    st.session_state.site_icon     = _icon
if "editing_menu" not in st.session_state:
    st.session_state.editing_menu = None

order  = st.session_state.menu_order
labels = st.session_state.menu_labels

# 헤더 — 브라우저 탭 제목 동적 업데이트 (파비콘은 set_page_config에서 처리)
st.markdown(f"""
<script>
(function() {{
    window.parent.document.title = {json.dumps(st.session_state.site_name)};
}})();
</script>
""", unsafe_allow_html=True)

hc1, hc2 = st.columns([8, 1])
with hc1:
    st.markdown(f"## {st.session_state.site_name}")
    st.caption(st.session_state.site_caption)
with hc2:
    with st.popover("⚙️ 메뉴 설정", use_container_width=True):
        if "is_admin" not in st.session_state:
            st.session_state.is_admin = False

        if not st.session_state.is_admin:
            st.caption("관리자 로그인")
            pw_input = st.text_input("비밀번호", type="password", key="admin_pw_input",
                                     label_visibility="collapsed", placeholder="비밀번호 입력")
            if st.button("확인", key="admin_login_btn", use_container_width=True):
                if hashlib.sha256(pw_input.encode()).hexdigest() == st.session_state.get("admin_pw_hash", DEFAULT_ADMIN_PW_HASH):
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
        else:
            ac1, ac2 = st.columns([3, 1])
            ac1.caption("관리자 모드")
            if ac2.button("로그아웃", key="admin_logout", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()
            st.divider()
            st.caption("비밀번호 변경")
            pw_cur  = st.text_input("현재 비밀번호", type="password", key="pw_cur",  placeholder="현재 비밀번호")
            pw_new  = st.text_input("새 비밀번호",   type="password", key="pw_new",  placeholder="새 비밀번호")
            pw_new2 = st.text_input("새 비밀번호 확인", type="password", key="pw_new2", placeholder="새 비밀번호 재입력")
            if st.button("비밀번호 변경", use_container_width=True, key="change_pw_btn"):
                cur_hash = hashlib.sha256(pw_cur.encode()).hexdigest()
                if cur_hash != st.session_state.get("admin_pw_hash", DEFAULT_ADMIN_PW_HASH):
                    st.error("현재 비밀번호가 틀렸습니다.")
                elif len(pw_new) < 4:
                    st.error("새 비밀번호는 4자 이상이어야 합니다.")
                elif pw_new != pw_new2:
                    st.error("새 비밀번호가 일치하지 않습니다.")
                else:
                    new_hash = hashlib.sha256(pw_new.encode()).hexdigest()
                    st.session_state.admin_pw_hash = new_hash
                    save_menu_settings(
                        st.session_state.menu_order, st.session_state.menu_labels,
                        admin_pw_hash=new_hash
                    )
                    st.success("비밀번호가 변경되었습니다.")
            st.divider()
            st.caption("사이트명 변경")
            new_site_name    = st.text_input("사이트명", value=st.session_state.site_name,    key="input_site_name")
            new_site_caption = st.text_input("부제목",   value=st.session_state.site_caption, key="input_site_caption")
            if st.button("사이트명 저장", use_container_width=True, key="save_site"):
                st.session_state.site_name    = new_site_name.strip() or st.session_state.site_name
                st.session_state.site_caption = new_site_caption.strip() or st.session_state.site_caption
                save_menu_settings(
                    st.session_state.menu_order, st.session_state.menu_labels,
                    st.session_state.site_name, st.session_state.site_caption,
                    st.session_state.get("site_icon", DEFAULT_SITE_ICON)
                )
                st.rerun()
            st.divider()
            st.caption("파비콘 변경")
            _fav_path = Path(__file__).parent / "data" / "favicon.png"
            if _fav_path.exists():
                st.image(str(_fav_path), width=32, caption="현재 파비콘")
            else:
                st.caption(f"현재: {st.session_state.get('site_icon', DEFAULT_SITE_ICON)} (이모지)")
            uploaded_favicon = st.file_uploader(
                "파비콘 이미지 업로드", type=["png", "ico", "jpg", "jpeg"],
                key="favicon_uploader", label_visibility="collapsed"
            )
            fc1, fc2 = st.columns(2)
            if fc1.button("이미지 적용", key="apply_favicon", use_container_width=True, disabled=uploaded_favicon is None):
                _fav_path.parent.mkdir(exist_ok=True)
                _fav_path.write_bytes(uploaded_favicon.read())
                st.success("파비콘 변경 완료!")
                st.rerun()
            if fc2.button("기본 이모지로", key="reset_favicon", use_container_width=True, disabled=not _fav_path.exists()):
                _fav_path.unlink(missing_ok=True)
                st.rerun()
            st.divider()
            st.caption("탭 이름 · 순서 변경")
            for i, key in enumerate(order):
                if st.session_state.editing_menu == i:
                    new_val = st.text_input(
                        "새 이름", value=labels[key],
                        key=f"rename_input_{i}", label_visibility="collapsed"
                    )
                    sc1, sc2 = st.columns(2)
                    if sc1.button("저장", key=f"save_rename_{i}", use_container_width=True):
                        st.session_state.menu_labels[key] = new_val.strip() or labels[key]
                        st.session_state.editing_menu = None
                        save_menu_settings(st.session_state.menu_order, st.session_state.menu_labels)
                        st.rerun()
                    if sc2.button("취소", key=f"cancel_rename_{i}", use_container_width=True):
                        st.session_state.editing_menu = None
                        st.rerun()
                else:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.caption(labels[key])
                    if c2.button("✏️", key=f"me_{i}", use_container_width=True):
                        st.session_state.editing_menu = i
                        st.rerun()
                    if i > 0:
                        if c3.button("↑", key=f"mu_{i}", use_container_width=True):
                            order[i], order[i-1] = order[i-1], order[i]
                            save_menu_settings(order, st.session_state.menu_labels)
                            st.rerun()
                    if i < len(order) - 1:
                        if c4.button("↓", key=f"md_{i}", use_container_width=True):
                            order[i], order[i+1] = order[i+1], order[i]
                            save_menu_settings(order, st.session_state.menu_labels)
                            st.rerun()
            st.divider()
            if st.button("기본값으로 초기화", use_container_width=True):
                st.session_state.menu_order   = DEFAULT_MENU.copy()
                st.session_state.menu_labels  = DEFAULT_LABELS.copy()
                st.session_state.site_name    = DEFAULT_SITE_NAME
                st.session_state.site_caption = DEFAULT_SITE_CAPTION
                st.session_state.site_icon    = DEFAULT_SITE_ICON
                st.session_state.editing_menu = None
                save_menu_settings(DEFAULT_MENU, DEFAULT_LABELS, DEFAULT_SITE_NAME, DEFAULT_SITE_CAPTION, DEFAULT_SITE_ICON)
                st.rerun()

st.markdown("---")

PAGE_MAP = {
    "🏠 대시보드":          page_dashboard,
    "📦 매입 / 매출 입력":  page_stock_entry,
    "💰 미수금 현황":       page_receivables,
    "⚙️ 기초 데이터 관리": page_master,
}

nav_tabs = st.tabs([labels[k] for k in order])
for nav_tab, key in zip(nav_tabs, order):
    with nav_tab:
        st.title(labels[key])
        PAGE_MAP[key]()
