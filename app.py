import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import sqlite3
from database import init_db, get_conn

st.set_page_config(page_title="업무 관리 대시보드", layout="wide", page_icon="📊")
init_db()

def fmt_money(v):
    return f"₩{int(v or 0):,}"

def days_left(due_date_str):
    if not due_date_str:
        return None
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        return (due - date.today()).days
    except:
        return None

def status_badge(days):
    if days is None:
        return ""
    if days < 0:
        return "🔴 연체"
    elif days <= 3:
        return "🔴 긴급"
    elif days <= 7:
        return "🟡 주의"
    else:
        return "🟢 여유"

# --- 사이드바 메뉴 ---
st.sidebar.title("📊 업무 관리")
menu = st.sidebar.radio("메뉴", ["🏠 대시보드", "🏢 거래처", "📁 프로젝트", "🧾 세금계산서", "💰 수금 관리"])

conn = get_conn()

# ===================== 대시보드 =====================
if menu == "🏠 대시보드":
    st.title("대시보드")

    inv_df = pd.read_sql("""
        SELECT i.*, c.name as client_name, p.name as project_name
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        LEFT JOIN projects p ON i.project_id = p.id
    """, conn)

    total_receivable = inv_df[inv_df["status"] == "미수"]["total_amount"].sum()
    this_month = date.today().strftime("%Y-%m")
    month_invoiced = inv_df[inv_df["issue_date"].str.startswith(this_month, na=False)]["total_amount"].sum()
    week_due = inv_df[
        (inv_df["status"] == "미수") &
        (inv_df["due_date"].apply(lambda x: 0 <= (days_left(x) or 999) <= 7))
    ]["total_amount"].sum()
    proj_count = pd.read_sql("SELECT COUNT(*) as cnt FROM projects WHERE status='진행중'", conn).iloc[0]["cnt"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("이번달 청구액", fmt_money(month_invoiced))
    c2.metric("미수금 합계", fmt_money(total_receivable))
    c3.metric("이번주 결제예정", fmt_money(week_due))
    c4.metric("진행중 프로젝트", f"{proj_count}건")

    st.divider()

    # 미수금 현황
    st.subheader("⚠️ 미수금 현황 (D-day 임박순)")
    unpaid = inv_df[inv_df["status"] == "미수"].copy()
    if not unpaid.empty:
        unpaid["D-day"] = unpaid["due_date"].apply(days_left)
        unpaid["상태"] = unpaid["D-day"].apply(status_badge)
        unpaid["청구액"] = unpaid["total_amount"].apply(fmt_money)
        unpaid = unpaid.sort_values("D-day")
        st.dataframe(
            unpaid[["client_name", "project_name", "청구액", "due_date", "D-day", "상태"]].rename(columns={
                "client_name": "거래처", "project_name": "프로젝트", "due_date": "결제예정일"
            }),
            use_container_width=True, hide_index=True
        )
    else:
        st.success("미수금이 없습니다.")

    st.divider()

    # 월별 청구 차트
    if not inv_df.empty and inv_df["issue_date"].notna().any():
        inv_df["월"] = inv_df["issue_date"].str[:7]
        monthly = inv_df.groupby("월")["total_amount"].sum().reset_index()
        fig = px.bar(monthly, x="월", y="total_amount", title="월별 청구액", labels={"total_amount": "금액(원)"})
        st.plotly_chart(fig, use_container_width=True)

# ===================== 거래처 =====================
elif menu == "🏢 거래처":
    st.title("거래처 관리")

    with st.expander("➕ 거래처 추가"):
        with st.form("add_client"):
            col1, col2 = st.columns(2)
            name = col1.text_input("거래처명 *")
            contact = col2.text_input("담당자")
            phone = col1.text_input("연락처")
            email = col2.text_input("이메일")
            if st.form_submit_button("추가"):
                if name:
                    conn.execute("INSERT INTO clients (name, contact, phone, email) VALUES (?,?,?,?)",
                                 (name, contact, phone, email))
                    conn.commit()
                    st.success(f"'{name}' 추가 완료")
                    st.rerun()

    df = pd.read_sql("""
        SELECT c.id, c.name as 거래처명, c.contact as 담당자, c.phone as 연락처, c.email as 이메일,
               COALESCE(SUM(i.total_amount),0) as 총청구액,
               COALESCE(SUM(CASE WHEN i.status='미수' THEN i.total_amount ELSE 0 END),0) as 미수금
        FROM clients c
        LEFT JOIN invoices i ON c.id = i.client_id
        GROUP BY c.id
    """, conn)

    if not df.empty:
        df["총청구액"] = df["총청구액"].apply(fmt_money)
        df["미수금"] = df["미수금"].apply(fmt_money)
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("등록된 거래처가 없습니다.")

# ===================== 프로젝트 =====================
elif menu == "📁 프로젝트":
    st.title("프로젝트 현황")

    clients_df = pd.read_sql("SELECT id, name FROM clients", conn)

    with st.expander("➕ 프로젝트 추가"):
        with st.form("add_project"):
            col1, col2 = st.columns(2)
            p_name = col1.text_input("프로젝트명 *")
            client_opt = {row["name"]: row["id"] for _, row in clients_df.iterrows()}
            selected_client = col2.selectbox("거래처", list(client_opt.keys()) if client_opt else ["거래처 없음"])
            amount = col1.number_input("계약금액", min_value=0, step=100000)
            status = col2.selectbox("상태", ["진행중", "검수중", "완료", "보류"])
            start = col1.date_input("시작일", value=date.today())
            end = col2.date_input("완료예정일", value=date.today())
            note = st.text_area("메모")
            if st.form_submit_button("추가"):
                if p_name and client_opt:
                    conn.execute("""INSERT INTO projects (client_id, name, amount, status, start_date, end_date, note)
                                    VALUES (?,?,?,?,?,?,?)""",
                                 (client_opt[selected_client], p_name, amount, status,
                                  str(start), str(end), note))
                    conn.commit()
                    st.success("프로젝트 추가 완료")
                    st.rerun()

    status_filter = st.selectbox("상태 필터", ["전체", "진행중", "검수중", "완료", "보류"])
    query = """SELECT p.id, c.name as 거래처, p.name as 프로젝트명, p.amount as 계약금액,
                      p.status as 상태, p.start_date as 시작일, p.end_date as 완료예정일, p.note as 메모
               FROM projects p LEFT JOIN clients c ON p.client_id = c.id"""
    if status_filter != "전체":
        query += f" WHERE p.status = '{status_filter}'"

    df = pd.read_sql(query, conn)
    if not df.empty:
        df["계약금액"] = df["계약금액"].apply(fmt_money)
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

        # 칸반 보드
        st.subheader("칸반 보드")
        statuses = ["진행중", "검수중", "완료"]
        cols = st.columns(3)
        all_proj = pd.read_sql("""SELECT p.name, p.status, p.amount, c.name as client
                                   FROM projects p LEFT JOIN clients c ON p.client_id=c.id""", conn)
        for i, s in enumerate(statuses):
            with cols[i]:
                st.markdown(f"**{s}**")
                filtered = all_proj[all_proj["status"] == s]
                for _, row in filtered.iterrows():
                    st.info(f"**{row['client']}**\n{row['name']}\n{fmt_money(row['amount'])}")
    else:
        st.info("등록된 프로젝트가 없습니다.")

# ===================== 세금계산서 =====================
elif menu == "🧾 세금계산서":
    st.title("세금계산서")

    clients_df = pd.read_sql("SELECT id, name FROM clients", conn)
    projects_df = pd.read_sql("SELECT id, name, client_id FROM projects", conn)

    with st.expander("➕ 세금계산서 발행"):
        with st.form("add_invoice"):
            col1, col2 = st.columns(2)
            client_opt = {row["name"]: row["id"] for _, row in clients_df.iterrows()}
            selected_client = col1.selectbox("거래처 *", list(client_opt.keys()) if client_opt else ["없음"])

            if client_opt and selected_client in client_opt:
                cid = client_opt[selected_client]
                proj_list = projects_df[projects_df["client_id"] == cid]
                proj_opt = {row["name"]: row["id"] for _, row in proj_list.iterrows()}
            else:
                proj_opt = {}

            selected_proj = col2.selectbox("프로젝트", list(proj_opt.keys()) if proj_opt else ["없음"])
            supply = col1.number_input("공급가액 *", min_value=0, step=100000)
            tax = col2.number_input("세액 (공급가액 10%)", value=int(supply * 0.1), step=10000)
            issue_date = col1.date_input("발행일", value=date.today())
            due_date = col2.date_input("결제예정일", value=date.today())
            note = st.text_area("메모")
            if st.form_submit_button("발행"):
                if supply > 0 and client_opt:
                    total = supply + tax
                    pid = proj_opt.get(selected_proj)
                    conn.execute("""INSERT INTO invoices (project_id, client_id, issue_date, supply_amount,
                                    tax_amount, total_amount, due_date, note)
                                    VALUES (?,?,?,?,?,?,?,?)""",
                                 (pid, client_opt[selected_client], str(issue_date),
                                  supply, tax, total, str(due_date), note))
                    conn.commit()
                    st.success(f"세금계산서 발행 완료 (합계: {fmt_money(total)})")
                    st.rerun()

    status_filter = st.selectbox("상태", ["전체", "미수", "완료"])
    query = """SELECT i.id, c.name as 거래처, p.name as 프로젝트,
                      i.issue_date as 발행일, i.supply_amount as 공급가액,
                      i.tax_amount as 세액, i.total_amount as 합계,
                      i.due_date as 결제예정일, i.status as 상태
               FROM invoices i
               LEFT JOIN clients c ON i.client_id = c.id
               LEFT JOIN projects p ON i.project_id = p.id"""
    if status_filter != "전체":
        query += f" WHERE i.status = '{status_filter}'"
    query += " ORDER BY i.issue_date DESC"

    df = pd.read_sql(query, conn)
    if not df.empty:
        df["공급가액"] = df["공급가액"].apply(fmt_money)
        df["세액"] = df["세액"].apply(fmt_money)
        df["합계"] = df["합계"].apply(fmt_money)
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("발행된 세금계산서가 없습니다.")

# ===================== 수금 관리 =====================
elif menu == "💰 수금 관리":
    st.title("수금 관리")

    unpaid_df = pd.read_sql("""
        SELECT i.id, c.name as 거래처, p.name as 프로젝트,
               i.total_amount as 청구액, i.due_date as 결제예정일, i.status as 상태
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        LEFT JOIN projects p ON i.project_id = p.id
        WHERE i.status = '미수'
        ORDER BY i.due_date ASC
    """, conn)

    if not unpaid_df.empty:
        unpaid_df["D-day"] = unpaid_df["결제예정일"].apply(days_left)
        unpaid_df["긴급도"] = unpaid_df["D-day"].apply(status_badge)
        unpaid_df["청구액"] = unpaid_df["청구액"].apply(fmt_money)

        st.subheader(f"미수금 {len(unpaid_df)}건")
        st.dataframe(unpaid_df.drop("id", axis=1), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("💳 입금 처리")
        inv_options = {f"{row['거래처']} - {row['프로젝트']} ({row['청구액']})": row["id"]
                       for _, row in unpaid_df.iterrows()}
        selected_inv = st.selectbox("입금할 건 선택", list(inv_options.keys()))
        paid_date = st.date_input("입금일", value=date.today())
        paid_note = st.text_input("메모")
        if st.button("입금 완료 처리"):
            inv_id = inv_options[selected_inv]
            inv_row = pd.read_sql(f"SELECT total_amount FROM invoices WHERE id={inv_id}", conn).iloc[0]
            conn.execute("INSERT INTO payments (invoice_id, paid_date, paid_amount, note) VALUES (?,?,?,?)",
                         (inv_id, str(paid_date), int(inv_row["total_amount"]), paid_note))
            conn.execute("UPDATE invoices SET status='완료' WHERE id=?", (inv_id,))
            conn.commit()
            st.success("입금 처리 완료!")
            st.rerun()
    else:
        st.success("모든 청구건이 입금 완료됐습니다.")

    st.divider()
    st.subheader("✅ 입금 완료 내역")
    done_df = pd.read_sql("""
        SELECT c.name as 거래처, p.name as 프로젝트,
               i.total_amount as 청구액, i.issue_date as 발행일,
               pay.paid_date as 입금일
        FROM payments pay
        JOIN invoices i ON pay.invoice_id = i.id
        LEFT JOIN clients c ON i.client_id = c.id
        LEFT JOIN projects p ON i.project_id = p.id
        ORDER BY pay.paid_date DESC
    """, conn)
    if not done_df.empty:
        done_df["청구액"] = done_df["청구액"].apply(fmt_money)
        st.dataframe(done_df, use_container_width=True, hide_index=True)

conn.close()
