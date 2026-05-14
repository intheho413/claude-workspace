import sqlite3
from pathlib import Path
db = Path("data/cosmetics.db")
conn = sqlite3.connect(db)
conn.execute("UPDATE clients SET category='비네트워크' WHERE category IN ('개인병원A','개인병원B')")
conn.execute("UPDATE clients SET discount_rate=0.10 WHERE category='비네트워크' AND ROUND(discount_rate,2)!=0.10")
conn.commit()
rows = conn.execute("SELECT name, category, ROUND(discount_rate*100,1) FROM clients ORDER BY category, name").fetchall()
for r in rows:
    print(f"{r[1]:12} | {r[2]}% | {r[0]}")
conn.close()
print("OK: DB update complete")
