import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")

DB_PATH = os.path.join(DATABASE_DIR, "meals.db")
EMP_XLSX = os.path.join(DATABASE_DIR, "employee_db.xlsx")

STORAGE_MODE = "postgres"   # change to "postgres" to use PostgreSQL

if STORAGE_MODE == "postgres":
    from db_postgres import upsert_meal, get_booking, get_summary, init_db, get_emails_for_date, delete_booking,get_user_bookings
else:
    from db_sqlite import upsert_meal, get_booking, get_summary, get_user_bookings, init_db, get_conn, get_emails_for_date, delete_booking


# def get_booking_for_date(email: str, meal_date_iso: str):
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("""
#         SELECT opted FROM meal_orders
#         WHERE email = ? AND meal_date = ?;
#     """, (email, meal_date_iso))
#     row = cur.fetchone()
#     conn.close()
#     if row is None:
#         return None
#     return row[0]

# def get_summary_for_date(meal_date_iso: str):
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("""
#         SELECT email, opted
#         FROM meal_orders
#         WHERE meal_date = ? AND opted = 1
#         ORDER BY email;
#     """, (meal_date_iso,))
#     rows_yes = cur.fetchall()

#     cur.execute("""
#         SELECT COUNT(*) FROM meal_orders
#         WHERE meal_date = ? AND opted = 1;
#     """, (meal_date_iso,))
#     (count_yes,) = cur.fetchone()

#     conn.close()
#     return count_yes, rows_yes

# ========== Excel-based auth ==========

@st.cache_data
def load_users_from_excel():
    df = pd.read_excel(EMP_XLSX)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Check required columns exist
    required_cols = {"email", "userid", "name"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"Excel must contain columns: {required_cols}, found: {df.columns}")

    # Normalize content
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["userid"] = df["userid"].astype(str).str.strip().str.lower()   # treat userid as lowercase text
    df["full_name"] = df["name"].astype(str).str.strip()

    # Determine role from userid
    df["role"] = df["userid"].apply(lambda uid: "admin" if uid == "admin" else "user")

    return df


def authenticate_email(email: str):
    df = load_users_from_excel()
    email_norm = email.strip().lower()
    row = df[df["email"] == email_norm]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "email": r["email"],
        "full_name": r.get("full_name", r["email"]),
        "role": r.get("role", "user")
    }

# ========== UI helpers ==========

def show_login_page():
    st.title("🍲 Book Your Meal")
    st.subheader("Login with your office email")

    with st.form("login_form"):
        email = st.text_input("Email ID")
        submitted = st.form_submit_button("Continue")

    if submitted:
        user = authenticate_email(email)
        if user:
            st.session_state["user"] = user
            st.success(f"Welcome, {user['full_name']} 👋")
            st.rerun()
        else:
            st.error("Email not found in allowed list. Please contact admin.")

def show_top_bar():
    user = st.session_state.get("user")
    if user:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"Logged in as **{user['full_name']}** ({user['email']}) – {user['role']}")
        with col2:
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

# ========== User view ==========

def show_user_home():
    show_top_bar()
    user = st.session_state["user"]   # contains email, full_name, role, userid

    st.markdown("### 📅 Book your meals")

    today = date.today()
    max_day = today + timedelta(days=60)   # allow booking next 60 days (change if you want)

    # 1️⃣ Calendar for choosing a date
    selected_date = st.date_input(
        "Select a date to book/cancel",
        value=today + timedelta(days=1),
        min_value=today,
        max_value=max_day,
    )

    meal_date_iso = selected_date.isoformat()
    meal_date_str = selected_date.strftime("%d-%m-%Y")

    st.caption(f"Selected date: **{meal_date_str}**")

    # 2️⃣ Show current status for that date
    # current_opt = get_booking_for_date(user["email"], meal_date_iso)
    current_opt = get_booking(user["email"], meal_date_iso)

    if current_opt is None:
        st.info("You have not booked anything for this date yet.")
    elif current_opt == 1:
        st.success("✅ You have booked a meal for this date.")
    else:
        st.warning("You have marked **No meal** for this date.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Yes, book meal for this date"):
            upsert_meal(user["email"], meal_date_iso, 1)
            st.success(f"Meal booked for {meal_date_str}.")
            st.rerun()
    with col2:
        if st.button("No meal on this date"):
            upsert_meal(user["email"], meal_date_iso, 0)
            st.info(f"Marked as no meal for {meal_date_str}.")
            st.rerun()
    # with col3:
    #     if st.button("Clear choice for this date"):
    #         # Optional: remove booking entirely
    #         conn = get_conn()
    #         cur = conn.cursor()
    #         cur.execute("DELETE FROM meal_orders WHERE email = ? AND meal_date = ?",
    #                     (user["email"], meal_date_iso))
    #         conn.commit()
    #         conn.close()
    #         st.info(f"Cleared booking for {meal_date_str}.")
    #         st.rerun()

    with col3:
        if st.button("Clear choice for this date"):
            delete_booking(user["email"], meal_date_iso)
            st.info(f"Cleared booking for {meal_date_str}.")
            st.rerun()

    # 3️⃣ Show upcoming bookings table
    st.markdown("---")
    st.markdown("#### 🕒 Your upcoming bookings")

    rows = get_user_bookings(user["email"])
    if rows:
        df = pd.DataFrame(rows, columns=["Date", "Meal"])
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        # Show only today onwards
        df = df[df["Date"] >= today]

        if df.empty:
            st.write("No future bookings yet.")
        else:
            df["Meal"] = df["Meal"].map({1: "Yes", 0: "No"})
            st.dataframe(df, use_container_width=True)
    else:
        st.write("No bookings yet.")

# ========== Admin view ==========

def show_admin_home():
    show_top_bar()
    st.markdown("### 🧾 Admin – Meal Summary")

    default_day = date.today() + timedelta(days=1)
    picked = st.date_input("Select date", value=default_day)
    meal_date_iso = picked.isoformat()
    meal_date_str = picked.strftime("%d-%m-%Y")

    count_yes = get_summary(meal_date_iso)
    emails = get_emails_for_date(meal_date_iso)

    st.metric(label=f"Total meals for {meal_date_str}", value=count_yes)

    if count_yes > 0:
        st.markdown("#### Emails opted for meal")
        df = pd.DataFrame(emails, columns=["Email"])
        # df = df.drop(columns=["Opted"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No one has booked a meal for this date yet.")

# ========== Main ==========

def main():
    st.set_page_config(page_title="Book Your Meal", page_icon="🍲", layout="centered")
    init_db()

    user = st.session_state.get("user")

    if not user:
        show_login_page()
    else:
        if user["role"] == "admin":
            show_admin_home()
        else:
            show_user_home()

if __name__ == "__main__":
    main()
