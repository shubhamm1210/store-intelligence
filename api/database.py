# database.py — shared DB connection for the API
# Reads from the same events.db that the pipeline writes to.

import sqlite3
import os

DB_PATH = os.environ.get("EVENTS_DB", "../pipeline/events.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params: tuple = ()):
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()):
    conn = get_conn()
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
