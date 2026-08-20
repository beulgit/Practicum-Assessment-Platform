"""
authentication.py
Very simple username/password authentication using salted SHA-256 hashing.
(For a production/college-server deployment, swap this for bcrypt/argon2.)
"""

import hashlib
import os
import binascii

from database.db import run_query, run_write


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return dk == expected
    except Exception:
        return False


# ---------- Teacher ----------

def register_teacher(username, name, email, password):
    existing = run_query("SELECT teacher_id FROM teachers WHERE username = ?", (username,))
    if existing:
        return None, "Username already exists."
    pwd_hash = hash_password(password)
    tid = run_write(
        "INSERT INTO teachers (username, name, email, password_hash) VALUES (?, ?, ?, ?)",
        (username, name, email, pwd_hash),
    )
    return tid, None


def login_teacher(username, password):
    rows = run_query("SELECT * FROM teachers WHERE username = ?", (username,))
    if not rows:
        return None, "No such teacher account."
    row = rows[0]
    if verify_password(password, row["password_hash"]):
        return dict(row), None
    return None, "Incorrect password."


# ---------- Student ----------

def register_student(username, name, email, course, section, password):
    existing = run_query("SELECT student_id FROM students WHERE username = ?", (username,))
    if existing:
        return None, "Username already exists."
    pwd_hash = hash_password(password)
    sid = run_write(
        "INSERT INTO students (username, name, email, course, section, password_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, name, email, course, section, pwd_hash),
    )
    return sid, None


def login_student(username, password):
    rows = run_query("SELECT * FROM students WHERE username = ?", (username,))
    if not rows:
        return None, "No such student account."
    row = rows[0]
    if verify_password(password, row["password_hash"]):
        return dict(row), None
    return None, "Incorrect password."
