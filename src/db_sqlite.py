import sqlite3
import os
from datetime import datetime

# ---------- DB PATH SETUP ----------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DATABASE_DIR, "meals.db")

os.makedirs(DATABASE_DIR, exist_ok=True)


# ---------- CONNECTION ----------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ---------- INITIALIZE DB ----------

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_orders (
            email TEXT NOT NULL,
            meal_date TEXT NOT NULL,
            opted INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (email, meal_date)
        )
    """)

    conn.commit()
    conn.close()


# ---------- UPSERT BOOKING ----------

def upsert_meal(email, meal_date, opted):
    """
    opted: 1 = Yes, 0 = No
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO meal_orders (email, meal_date, opted, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email, meal_date)
        DO UPDATE SET opted = excluded.opted
    """, (
        email,
        meal_date,
        opted,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ---------- GET BOOKING FOR USER & DATE ----------

def get_booking(email, meal_date):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT opted FROM meal_orders
        WHERE email = ? AND meal_date = ?
    """, (email, meal_date))

    row = cur.fetchone()
    conn.close()

    return None if row is None else row[0]


# ---------- GET ALL BOOKINGS FOR USER ----------

def get_user_bookings(email):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT meal_date, opted
        FROM meal_orders
        WHERE email = ?
        ORDER BY meal_date
    """, (email,))

    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- ADMIN SUMMARY ----------

def get_summary(meal_date):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM meal_orders
        WHERE meal_date = ? AND opted = 1
    """, (meal_date,))

    count = cur.fetchone()[0]
    conn.close()
    return count

def get_emails_for_date(meal_date):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT email
        FROM meal_orders
        WHERE meal_date = ? AND opted = 1
        ORDER BY email
    """, (meal_date,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_booking(email, meal_date):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM meal_orders WHERE email = ? AND meal_date = ?",
        (email, meal_date)
    )
    conn.commit()
    conn.close()
