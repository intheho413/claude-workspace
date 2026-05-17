import sqlite3
from pathlib import Path
from datetime import date

DB = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(DB)

# LOT 형식: YYYY-MM 또는 YYYY-MMx → 입고월 + 24개월 = 유통기한
rows = conn.execute("SELECT id, lot_number FROM stock_in WHERE expiry_date IS NULL").fetchall()

updated = 0
for sid, lot in rows:
    if not lot:
        continue
    ym = lot[:7]  # YYYY-MM
    try:
        y, m = int(ym[:4]), int(ym[5:7])
        m += 24
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        expiry = f"{y}-{m:02d}-01"
        conn.execute("UPDATE stock_in SET expiry_date=? WHERE id=?", (expiry, sid))
        updated += 1
    except Exception:
        continue

conn.commit()
print(f"유통기한 {updated}건 업데이트 완료")

rows = conn.execute("""
    SELECT p.name, s.lot_number, s.expiry_date, s.remaining_qty
    FROM stock_in s JOIN products p ON s.product_id=p.id
    ORDER BY s.expiry_date ASC LIMIT 10
""").fetchall()
print("\n[유통기한 확인 (상위 10건)]")
for r in rows:
    print(f"  {r[0]} | LOT:{r[1]} | 만료:{r[2]} | 잔여:{int(r[3])}개")

conn.close()
