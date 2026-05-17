# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

print("=== 전체 클라이언트 목록 (DB) ===")
clients = conn.execute("SELECT id, name, category, discount_rate FROM clients ORDER BY id").fetchall()
for c in clients:
    print(f"  id={c[0]} | {c[1]} | {c[2]} | 할인율={c[3]}")

print("\n=== 전체 출고 내역 (거래처별 합계) ===")
totals = conn.execute("""
    SELECT c.name, c.id,
           COUNT(*) as 건수,
           SUM(o.supply_amount) as 공급가합계,
           SUM(o.total_amount) as 총액합계
    FROM stock_out o
    JOIN clients c ON o.client_id = c.id
    WHERE o.type='출고'
    GROUP BY c.id, c.name
    ORDER BY c.id
""").fetchall()

for t in totals:
    print(f"  {t[1]:2d}. {t[0]} | 건수={t[2]} | 공급가={t[3]:,} | 총액={t[4]:,}")

print("\n=== 스프레드시트 거래처명 vs DB 거래처명 비교 ===")
sheet_clients = [
    "세라미크 강남",
    "벨리셀의원",
    "온리프 성형외과",
    "리진의원",
    "셀린의원 수원망포",
    "데이뷰 안양점",
    "셀린의원 연신내점",
    "셀린의원 명동점",
    "셀린의원 하남미사점",
    "데이뷰 명동점",
    "힐세리온 의원",
    "셀린의원 청주점",
    "데이뷰 광주상무점",
    "셀린의원 다산점",
    "셀린의원 수원점",
    "셀린의원 홍대점",
    "셀렌의원 명동점",
]
db_names = [c[1] for c in clients]
for sc in sheet_clients:
    if sc in db_names:
        print(f"  ✓ {sc}")
    else:
        print(f"  ✗ 불일치: 시트='{sc}' → DB에 없음")

print("\n추가로 DB에만 있는 이름:")
for dn in db_names:
    if dn not in sheet_clients:
        print(f"  DB에만 있음: '{dn}'")

conn.close()
