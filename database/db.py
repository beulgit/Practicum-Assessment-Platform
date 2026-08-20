"""
db.py
SQLite connection management + small generic helpers used across the app.
"""

import sqlite3
import os
from contextlib import contextmanager

from database.schema import SCHEMA_STATEMENTS

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "database.db")


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    """Context manager yielding a cursor; commits on success if requested."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if they do not already exist."""
    with db_cursor(commit=True) as cur:
        for statement in SCHEMA_STATEMENTS:
            cur.execute(statement)


def run_query(query: str, params: tuple = ()):
    """SELECT helper -> list of sqlite3.Row"""
    with db_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def run_write(query: str, params: tuple = ()):
    """INSERT/UPDATE/DELETE helper -> lastrowid"""
    with db_cursor(commit=True) as cur:
        cur.execute(query, params)
        return cur.lastrowid
