# -*- coding: utf-8 -*-
import sys, ast, sqlite3
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

OK = "✓"; NG = "✗"

# ── 1. 문법 검사 ──────────────────────────────────────────────────
print("=" * 60)
print("[1] cosmetics.py 문법 검사")
app = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\cosmetics.py")
try:
    ast.parse(app.read_text(encoding="utf-8"))
    print(f"  {OK} 문법 오류 없음")
except SyntaxError as e:
    print(f"  {NG} 문법 오류: {e}")

# ── 2. DB 연결 및 기본 테이블 확인 ───────────────────────────────
print("\n[2] DB 테이블 & 컬럼 확인")
db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

for tbl, expected_cols in [
    ("products",  ["id","name","spec","purchase_price","sale_price","min_stock","settlement_price"]),
    ("stock_in",  ["id","product_id","date","quantity","purchase_price","remaining_qty"]),
    ("stock_out", ["id","client_id","product_id","date","type","quantity","discount_rate",
                   "supply_amount","vat_amount","total_amount","fifo_purchase_price",
                   "margin_amount","margin_rate","note"]),
    ("clients",   ["id","name","category","discount_rate"]),
    ("payments",  ["id","client_id","date","amount"]),
]:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})")]
    missing = [c for c in expected_cols if c not in cols]
    if missing:
        print(f"  {NG} {tbl}: 누락 컬럼 {missing}")
    else:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {OK} {tbl}: {cnt}건")

# ── 3. 핵심 KPI 쿼리 ─────────────────────────────────────────────
print("\n[3] 리포트 KPI 쿼리 (total_amount 기준)")
total_sales = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM stock_out WHERE type='출고'").fetchone()[0]
total_pay   = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0]
미수금      = total_sales - total_pay
print(f"  납품금액 합계 (VAT포함): {total_sales:,}원")
print(f"  수금액 합계:             {total_pay:,}원")
print(f"  미수금 합계:             {미수금:,}원")
if total_sales > 0:
    print(f"  {OK} KPI 쿼리 정상")
else:
    print(f"  {NG} total_amount 합계 0 — 재계산 필요")

# supply_amount vs total_amount 비교
sa = conn.execute("SELECT COALESCE(SUM(supply_amount),0) FROM stock_out WHERE type='출고'").fetchone()[0]
ta = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM stock_out WHERE type='출고'").fetchone()[0]
print(f"\n  supply_amount 합계: {sa:,}원")
print(f"  total_amount  합계: {ta:,}원")
if sa == ta:
    print(f"  {OK} supply = total (일치)")
else:
    print(f"  ⚠ supply ≠ total — 재계산 버튼 필요 (차이 {ta-sa:+,}원)")

# ── 4. 미수금 서브쿼리 ────────────────────────────────────────────
print("\n[4] 거래처별 미수금 (서브쿼리 방식)")
rows = conn.execute("""
    SELECT c.name,
           COALESCE(s.ts,0) as 총매출,
           COALESCE(p.tp,0) as 총수금,
           COALESCE(s.ts,0)-COALESCE(p.tp,0) as 미수금
    FROM clients c
    LEFT JOIN (SELECT client_id, SUM(total_amount) as ts FROM stock_out WHERE type='출고' GROUP BY client_id) s ON c.id=s.client_id
    LEFT JOIN (SELECT client_id, SUM(amount) as tp FROM payments GROUP BY client_id) p ON c.id=p.client_id
    WHERE COALESCE(s.ts,0) > 0
    ORDER BY 미수금 DESC
""").fetchall()
for r in rows:
    mark = OK if r["미수금"] >= 0 else NG
    print(f"  {mark} {r['name']}: 납품{r['총매출']:,} - 수금{r['총수금']:,} = 미수금{r['미수금']:,}")

# ── 5. 출고 수정 탭 쿼리 (total_amount as 납품금액) ─────────────
print("\n[5] 출고 수정 탭 — NULL 체크")
rows = conn.execute("""
    SELECT o.id,
           COALESCE(o.fifo_purchase_price,0) * o.quantity as 공급가액,
           o.total_amount as 납품금액,
           o.margin_amount as 마진액
    FROM stock_out o WHERE o.type='출고'
    ORDER BY o.id
""").fetchall()
null_cnt = sum(1 for r in rows if r["납품금액"] is None or r["납품금액"] == 0)
print(f"  total_amount=0 또는 NULL 건수: {null_cnt}건  {'⚠ 재계산 필요' if null_cnt > 0 else OK}")
print(f"  전체 출고 건수: {len(rows)}건")

# ── 6. 제품 관리 purchase_price NULL 체크 ────────────────────────
print("\n[6] 제품 관리 — purchase_price NULL 체크")
nulls = conn.execute("SELECT name FROM products WHERE purchase_price IS NULL").fetchall()
zeros = conn.execute("SELECT name FROM products WHERE purchase_price = 0").fetchall()
if nulls:
    print(f"  {NG} NULL 제품: {[r[0] for r in nulls]}")
else:
    print(f"  {OK} NULL 없음")
if zeros:
    print(f"  ⚠ 공급가 0원 제품: {[r[0] for r in zeros]}")
else:
    print(f"  {OK} 0원 제품 없음")

# ── 7. FIFO 재고 현황 ─────────────────────────────────────────────
print("\n[7] FIFO 재고 현황")
stocks = conn.execute("""
    SELECT p.name, COALESCE(SUM(s.remaining_qty),0) as 재고
    FROM products p LEFT JOIN stock_in s ON p.id=s.product_id
    GROUP BY p.id ORDER BY p.name
""").fetchall()
for s in stocks:
    warn = " ⚠ 재고없음" if s[1] == 0 else ""
    print(f"  {s['name']}: {int(s[1])}개{warn}")

conn.close()
print("\n" + "=" * 60)
print("검증 완료")
print("=" * 60)
