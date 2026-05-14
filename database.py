import psycopg2
import streamlit as st


class DBConn:
    """psycopg2 래퍼 — sqlite3 conn.execute() 인터페이스와 호환"""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        sql = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()


def get_conn():
    url = st.secrets["database"]["url"]
    return DBConn(psycopg2.connect(url))


def init_db():
    conn = get_conn()
    cur = conn._conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            email TEXT,
            created_at DATE DEFAULT CURRENT_DATE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            client_id INTEGER,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            status TEXT DEFAULT '진행중',
            start_date TEXT,
            end_date TEXT,
            note TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
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
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER,
            paid_date TEXT,
            paid_amount INTEGER DEFAULT 0,
            note TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    """)
    conn._conn.commit()
    conn.close()
