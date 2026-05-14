import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "business.db"

def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            email TEXT,
            created_at TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            status TEXT DEFAULT '진행중',
            start_date TEXT,
            end_date TEXT,
            note TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            client_id INTEGER,
            issue_date TEXT,
            supply_amount INTEGER DEFAULT 0,
            tax_amount INTEGER DEFAULT 0,
            total_amount INTEGER DEFAULT 0,
            due_date TEXT,
            status TEXT DEFAULT '미수',
            note TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            paid_date TEXT,
            paid_amount INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
    """)
    conn.commit()
    conn.close()
