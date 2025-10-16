"""
EcoSchool — School Carbon Calculator (Streamlit single-file app)
Filename: EcoSchool_Streamlit_App.py
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import altair as alt

# -------------------------
# Constants & Defaults
# -------------------------
DB_FILE = "ecoschool.db"
ADMIN_PASSWORD = "schooladmin"
DEFAULT_FACTORS = {
    "Paper (sheets)": 0.005,
    "Plastic (kg)": 6.0,
    "Food/Waste (kg)": 3.0,
    "Transport (km)": 0.21
}

EQUIVALENTS = {
    "tree_seedlings_1yr": 21.77,
    "km_driven_car": 0.21
}

LOCALES = {
    "en": {
        "title": "EcoSchool — School Carbon Calculator",
        "add_entry": "Add Entry",
        "dashboard": "Dashboard",
        "history": "History / Class Feed",
        "leaderboard": "Challenges / Leaderboard",
        "settings": "Settings / Admin",
        "category": "Category",
        "quantity": "Quantity",
        "unit": "Unit",
        "date": "Date",
        "notes": "Notes (optional)",
        "submit": "Submit",
        "verify": "Verify",
        "export_csv": "Export CSV",
        "language": "Language",
        "class_name": "Class / Section",
        "student_name": "Student Name",
        "photo": "Photo (optional)",
        "points": "Points",
        "badges": "Badges",
        "admin_login": "Admin Login",
        "edit_factors": "Edit conversion factors",
        "save": "Save",
        "clear_entries": "Clear all entries",
        "confirm_clear": "⚠️ Are you sure you want to delete all entries? This cannot be undone.",
        "verify_section": "Verify student entries",
        "equivalents_note": "💡 *The equivalents below help visualize CO₂ savings — for example, avoiding 21.77 kg CO₂ equals planting one tree seedling for a year, or saving 100 km worth of car travel!*"
    }
}

# -------------------------
# Database helpers
# -------------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            date TEXT,
            student TEXT,
            class_name TEXT,
            category TEXT,
            quantity REAL,
            unit TEXT,
            photo BLOB,
            notes TEXT,
            verified INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            co2 REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS factors (
            category TEXT PRIMARY KEY,
            factor REAL
        )
    ''')
    for cat, f in DEFAULT_FACTORS.items():
        c.execute('INSERT OR IGNORE INTO factors (category, factor) VALUES (?, ?)', (cat, f))
    conn.commit()
    conn.close()


def get_factors():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT category, factor FROM factors', conn, index_col='category')
    conn.close()
    return df['factor'].to_dict()


def set_factor(category, factor):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('REPLACE INTO factors (category, factor) VALUES (?, ?)', (category, float(factor)))
    conn.commit()
    conn.close()


def add_entry_to_db(entry):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO entries (timestamp, date, student, class_name, category, quantity, unit, photo, notes, verified, points, co2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        entry['timestamp'], entry['date'], entry['student'], entry['class_name'], entry['category'],
        entry['quantity'], entry['unit'], entry.get('photo'), entry.get('notes'),
        entry.get('verified', 0), entry.get('points', 0), entry['co2']
    ))
    conn.commit()
    conn.close()


def load_entries(only_verified=None):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT * FROM entries ORDER BY timestamp DESC', conn)
    conn.close()
    if only_verified is not None:
        df = df[df['verified'] == (1 if only_verified else 0)]
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df


def verify_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE entries SET verified=1 WHERE id=?', (entry_id,))
    conn.commit()
    conn.close()


def clear_all_entries():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM entries')
    conn.commit()
    conn.close()

# -------------------------
# Business logic
# -------------------------

def compute_co2(category, quantity, factors):
    factor = factors.get(category, 0)
    return float(quantity) * float(factor)


def points_for_co2(co2):
    return int(round(max(1, co2 * 2)))


def badge_for_total(total_kg):
    if total_kg < 5:
        return "Seedling"
    if total_kg < 20:
        return "Green Hero"
    if total_kg < 50:
        return "Eco Champion"
    return "Carbon Star"

# -------------------------
# Streamlit App
# -------------------------

def main():
    st.set_page_config(page_title="EcoSchool", layout='wide')
    init_db()
    loc = LOCALES['en']
    st.title(loc['title'])

    tabs = st.tabs([loc['dashboard'], loc['add_entry'], loc['leaderboard'], loc['settings']])
    factors = get_factors()

    # -----------------
    # Dashboard
    # -----------------
    with tabs[0]:
        st.header(loc['dashboard'])
        entries = load_entries()
        if entries.empty:
            st.info("No entries yet — ask students to add today's activities!")
        else:
            total_co2 = entries['co2'].sum()
            st.metric("Total emissions (kg CO2)", f"{total_co2:.2f}")
            breakdown = entries.groupby('category')['co2'].sum().reset_index()
            chart = alt.Chart(breakdown).mark_bar().encode(
                x=alt.X('co2:Q', title='kg CO2'),
                y=alt.Y('category:N', sort='-x', title=None)
            )
            st.altair_chart(chart, use_container_width=True)
            st.markdown(loc['equivalents_note'])   # <--- NEW INFO SECTION

    # -----------------
    # Add entry
    # -----------------
    with tabs[1]:
        st.header(loc['add_entry'])
        with st.form("entry_form"):
            student = st.text_input(loc['student_name'])
            class_name = st.text_input(loc['class_name'])
            date_val = st.date_input(loc['date'], value=date.today())

            # Remove Electricity
            category_options = [c for c in factors.keys() if c != "Electricity"]
            category = st.selectbox(loc['category'], options=category_options)

            qty = st.number_input(loc['quantity'], min_value=0.0, value=0.0, step=0.1)

            # --- CHANGED: Dropdown for units
            unit_options = ['sheets', 'kg', 'litres', 'items', 'km', 'units']
            unit = st.selectbox(loc['unit'], options=unit_options, index=0)

            notes = st.text_area(loc['notes'])
            submitted = st.form_submit_button(loc['submit'])

            if submitted:
                co2 = compute_co2(category, qty, factors)
                entry = {
                    'timestamp': datetime.now().isoformat(),
                    'date': date_val.isoformat(),
                    'student': student,
                    'class_name': class_name,
                    'category': category,
                    'quantity': qty,
                    'unit': unit,
                    'notes': notes,
                    'verified': 0,
                    'points': 0,
                    'co2': co2
                }
                add_entry_to_db(entry)
                st.success(f"Saved — estimated {co2:.2f} kg CO2")

    # -----------------
    # Admin / Settings
    # -----------------
    with tabs[3]:
        st.header(loc['settings'])
        pwd = st.text_input("Password", type='password')
        if pwd == ADMIN_PASSWORD:
            st.success("Admin authenticated")

            # Clear entries (fixed)
            st.subheader(loc['clear_entries'])
            if 'confirm_clear' not in st.session_state:
                st.session_state.confirm_clear = False

            if not st.session_state.confirm_clear:
                if st.button("⚠️ " + loc['clear_entries']):
                    st.session_state.confirm_clear = True
                    st.rerun()
            else:
                st.warning(loc['confirm_clear'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, delete all data"):
                        clear_all_entries()
                        st.session_state.confirm_clear = False
                        st.success("All entries cleared successfully!")
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state.confirm_clear = False
                        st.rerun()

        else:
            st.info("Enter admin password to manage settings")

if __name__ == '__main__':
    main()
