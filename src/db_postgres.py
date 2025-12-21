import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = st.secrets.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

def init_db():
    """
    Creates tables if they do not exist.
    Safe to call multiple times.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS meal_orders (
                email TEXT NOT NULL,
                meal_date DATE NOT NULL,
                opted BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (email, meal_date)
            );
        """))

def upsert_meal(email, meal_date, opted):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO meal_orders (email, meal_date, opted)
            VALUES (:email, :meal_date, :opted)
            ON CONFLICT (email, meal_date)
            DO UPDATE SET opted = EXCLUDED.opted;
        """), {
            "email": email,
            "meal_date": meal_date,
            "opted": opted
        })

def get_booking(email, meal_date):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT opted FROM meal_orders
            WHERE email = :email AND meal_date = :meal_date
        """), {
            "email": email,
            "meal_date": meal_date
        }).fetchone()
    return None if row is None else row[0]

def get_summary(meal_date):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT COUNT(*) FROM meal_orders
            WHERE meal_date = :meal_date AND opted = true
        """), {"meal_date": meal_date}).fetchone()
    return row[0]

def get_emails_for_date(meal_date):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT email
            FROM meal_orders
            WHERE meal_date = :meal_date AND opted = true
            ORDER BY email
        """), {"meal_date": meal_date}).fetchall()
    return [r[0] for r in rows]