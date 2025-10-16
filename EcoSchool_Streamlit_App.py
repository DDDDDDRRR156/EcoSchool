# EcoSchool_Streamlit_App.py
# Streamlit single-file app — School Carbon Calculator
# Features: dashboard, add entry, leaderboard, admin (password-protected), localization (English/Gujarati)

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import altair as alt

# -------------------------
# Configuration (change in code)
# -------------------------
DB_FILE = "ecoschool.db"
ADMIN_PASSWORD = "schooladmin"   # <-- change here if you want a different admin password

# Default conversion factors (category -> kg CO2 per unit)
DEFAULT_FACTORS = {
    "Paper (sheets)": 0.005,
    "Plastic (kg)": 6.0,
    "Food/Waste (kg)": 3.0,
    "Transport (km)": 0.21
}

EQUIVALENTS = {
    "tree_seedlings_1yr": 21.77,   # kg CO2 per seedling per year (example)
    "km_driven_car": 0.21          # kg CO2 per km driven (example)
}

# Localization strings (English + Gujarati)
LOCALES = {
    "en": {
        "app_title": "EcoSchool — School Carbon Calculator",
        "sidebar_title": "EcoSchool 🌿",
        "nav_dashboard": "Dashboard",
        "nav_add": "Add Entry",
        "nav_leaderboard": "Leaderboard",
        "nav_admin": "Admin Settings",
        "nav_about": "About",
        "language_label": "Language / ભાષા",
        "dashboard": "Dashboard",
        "add_entry": "Add Entry",
        "leaderboard": "Leaderboard",
        "settings": "Admin Settings",
        "about": "About",
        "category": "Category",
        "quantity": "Quantity",
        "unit": "Unit",
        "date": "Date",
        "student_name": "Student Name",
        "class_name": "Class / Section",
        "photo": "Photo (optional)",
        "notes": "Notes (optional)",
        "submit": "Submit",
        "saved": "Saved — estimated {co2:.2f} kg CO₂",
        "verify": "Verify",
        "verified": "✅ Verified",
        "export_csv": "Export CSV",
        "edit_factors": "Edit conversion factors",
        "save_factors": "Save factors",
        "clear_entries": "Clear all entries",
        "confirm_clear": "I understand this will permanently delete all entries",
        "danger_clear": "Yes, delete all entries",
        "equivalents_title": "Equivalents & Explanation",
        "equivalents_text": (
            "These equivalents help visualise what the CO₂ numbers mean. "
            f"For example, avoiding {EQUIVALENTS['tree_seedlings_1yr']} kg CO₂ roughly equals "
            "one tree seedling grown for a year. A typical car emits about "
            f"{EQUIVALENTS['km_driven_car']} kg CO₂ per km — use these to compare."
        ),
        "admin_password_prompt": "Enter admin password",
        "admin_auth_failed": "Incorrect admin password",
        "admin_auth_ok": "Admin authenticated",
        "no_entries": "No entries yet.",
        "about_text": "EcoSchool helps students log school activities and estimate greenhouse gas emissions (kg CO₂). Built with Streamlit.",
        "units_options": ['sheets', 'kg', 'litres', 'items', 'km', 'units'],
    },
    "gu": {
        "app_title": "ઇકોસ્કૂલ — સ્કૂલ કાર્બન કેલ્ક્યુલેટર",
        "sidebar_title": "ઇકોસ્કૂલ 🌿",
        "nav_dashboard": "ડૅશબોર્ડ",
        "nav_add": "એન્ટ્રી ઉમેરો",
        "nav_leaderboard": "લીડરબોર્ડ",
        "nav_admin": "એડમિન સેટિંગ્સ",
        "nav_about": "વિશે",
        "language_label": "Language / ભાષા",
        "dashboard": "ડેશબોર્ડ",
        "add_entry": "એન્ટ્રી ઉમેરો",
        "leaderboard": "લીડરબોર્ડ",
        "settings": "એડમિન સેટિંગ્સ",
        "about": "વિશે",
        "category": "શ્રેણી",
        "quantity": "પરિમાણ",
        "unit": "એકમ",
        "date": "તારીખ",
        "student_name": "વિદ્યાર્થીનું નામ",
        "class_name": "ક્લાસ / વિભાગ",
        "photo": "ફોટો (વૈકલ્પિક)",
        "notes": "ટિપ્પણી (વૈકલ્પિક)",
        "submit": "સબમિટ",
        "saved": "{co2:.2f} kg CO₂ અંદાજિત {co2:.2f}kg સાચવાયું",
        "verify": "સત્યાપિત કરો",
        "verified": "✅ સત્યાપિત",
        "export_csv": "CSV નિકાસ",
        "edit_factors": "રૂપાંતરણ ફેક્ટર્સ સંપાદિત કરો",
        "save_factors": "ફેક્ટર્સ સાચવો",
        "clear_entries": "બધી એન્ટ્રીઓ સાફ કરો",
        "confirm_clear": "હું સમજી ગયો છું કે આ તમામ એન્ટ્રીઓ કાયમ માટે કાઢી નાંખશે",
        "danger_clear": "હા, બધા દાખલા કાઢી દો",
        "equivalents_title": "સમાનતા અને وضاحت",
        "equivalents_text": (
            "આ સમકક્ષો CO₂ સંખ્યાંનો અર્થ બતાવે છે. ઉદાહરણ તરીકે, "
            f"{EQUIVALENTS['tree_seedlings_1yr']} kg CO₂ બચાવવું એક વૃક્ષની એક વર્ષની વૃદ્ધિનું અનુમાન છે. "
            f"એક સામાન્ય કાર લગભગ {EQUIVALENTS['km_driven_car']} kg CO₂ પ્રતિ કિમી ઉત્સર્જન કરે છે."
        ),
        "admin_password_prompt": "એડમિન પાસવર્ડ દાખલ કરો",
        "admin_auth_failed": "ખોટો એડમિન પાસવર્ડ",
        "admin_auth_ok": "એડમિન પ્રમાણિત",
        "no_entries": "હજી કોઈ એન્ટ્રી નથી.",
        "about_text": "ઇકોસ્કૂલ વિદ્યાર્થીઓને તેમની પ્રવૃત્તિઓમાં કાર્બન અનુમાન કરવા મદદ કરે છે. Streamlit વડે બનાવાયું.",
        "units_options": ['sheets', 'kg', 'litres', 'items', 'km', 'units'],
    }
}

# -------------------------
# Database helpers
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
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
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS factors (
            category TEXT PRIMARY KEY,
            factor REAL
        )
    """)
    # insert default factors if not present
    for cat, f in DEFAULT_FACTORS.items():
        c.execute("INSERT OR IGNORE INTO factors (category, factor) VALUES (?, ?)", (cat, f))
    conn.commit()
    conn.close()

def get_factors():
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT category, factor FROM factors", conn, index_col="category")
        factors = df['factor'].to_dict()
    except Exception:
        # if table empty or error, fall back to defaults
        factors = dict(DEFAULT_FACTORS)
    conn.close()
    return factors

def set_factor(category, factor):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO factors (category, factor) VALUES (?, ?)", (category, float(factor)))
    conn.commit()
    conn.close()

def add_entry_to_db(entry):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO entries (timestamp, date, student, class_name, category, quantity, unit, photo, notes, verified, points, co2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry['timestamp'], entry['date'], entry['student'], entry['class_name'],
        entry['category'], entry['quantity'], entry['unit'], entry.get('photo'),
        entry.get('notes'), entry.get('verified', 0), entry.get('points', 0), entry.get('co2', 0.0)
    ))
    conn.commit()
    conn.close()

def load_entries(all_rows=True, only_verified=None):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM entries ORDER BY timestamp DESC", conn)
    conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'])
    if only_verified is not None:
        df = df[df['verified'] == (1 if only_verified else 0)]
    return df

def verify_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE entries SET verified=1 WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

def clear_all_entries():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM entries")
    conn.commit()
    conn.close()

# -------------------------
# Business logic
# -------------------------
def compute_co2(category, quantity, factors):
    return float(quantity) * float(factors.get(category, 0))

def points_for_co2(co2):
    # simple points mapping: 1 point per 0.1 kg CO2 saved (example)
    return int(round(co2 * 10))

# -------------------------
# UI helpers
# -------------------------
def sidebar_nav(locale):
    st.sidebar.title(locale["sidebar_title"])
    st.sidebar.markdown("")  # small spacing
    choice = st.sidebar.radio(
        "Go to",
        (locale["nav_dashboard"], locale["nav_add"], locale["nav_leaderboard"], locale["nav_admin"], locale["nav_about"])
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("EcoSchool — track, learn, act 🌱")
    return choice

# -------------------------
# App
# -------------------------
def main():
    st.set_page_config(page_title="EcoSchool", layout="wide")
    init_db()
    # language selection
    lang_key = st.sidebar.selectbox(LOCALES['en']["language_label"] if 'language_label' in LOCALES['en'] else "Language / ભાષા",
                                    options=['en', 'gu'],
                                    format_func=lambda k: "English" if k == 'en' else "ગુજરાતી")
    loc = LOCALES[lang_key]

    # proper sidebar navigation
    st.sidebar.title(loc["app_title"])
    page = st.sidebar.radio(
        "",
        options=[loc["nav_dashboard"], loc["nav_add"], loc["nav_leaderboard"], loc["nav_admin"], loc["nav_about"]]
    )

    st.title(loc["app_title"])

    # load factors and entries
    factors = get_factors()

    # -------------------------
    # DASHBOARD
    # -------------------------
    if page == loc["nav_dashboard"]:
        st.header(loc["dashboard"])
        entries = load_entries()
        if entries.empty:
            st.info(loc.get("no_entries", "No entries yet."))
        else:
            total_co2 = entries['co2'].sum()
            total_points = entries['points'].sum() if 'points' in entries.columns else 0
            st.metric("Total emissions (kg CO₂)", f"{total_co2:.2f}")
            st.metric("Total points", int(total_points))

            # breakdown chart
            breakdown = entries.groupby('category')['co2'].sum().reset_index().sort_values('co2', ascending=False)
            if not breakdown.empty:
                chart = alt.Chart(breakdown).mark_bar().encode(
                    x=alt.X('co2:Q', title='kg CO₂'),
                    y=alt.Y('category:N', sort='-x', title=None)
                )
                st.altair_chart(chart, use_container_width=True)

            # equivalents section with explanation
            st.subheader(loc["equivalents_title"])
            st.write(loc["equivalents_text"])
            trees_eq = total_co2 / EQUIVALENTS['tree_seedlings_1yr'] if EQUIVALENTS['tree_seedlings_1yr'] else 0
            km_eq = total_co2 / EQUIVALENTS['km_driven_car'] if EQUIVALENTS['km_driven_car'] else 0
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tree-seedling-years (eq.)", f"{trees_eq:.1f}")
            with col2:
                st.metric("Car km (eq.)", f"{km_eq:.0f} km")

            # show recent entries
            st.subheader("Recent entries")
            st.dataframe(entries)

    # -------------------------
    # ADD ENTRY
    # -------------------------
    elif page == loc["nav_add"]:
        st.header(loc["add_entry"])
        with st.form("entry_form"):
            student = st.text_input(loc["student_name"])
            class_name = st.text_input(loc["class_name"])
            date_val = st.date_input(loc["date"], value=date.today())

            # show category options (exclude Electricity)
            category_options = [c for c in factors.keys() if "Electricity" not in c]
            if not category_options:
                st.warning("No categories available. Admin must set categories in Admin Settings.")
            category = st.selectbox(loc["category"], options=category_options)

            qty = st.number_input(loc["quantity"], min_value=0.0, value=0.0, step=0.1)
            unit = st.selectbox(loc["unit"], options=loc.get("units_options", ['sheets', 'kg', 'litres', 'items', 'km', 'units']))

            photo = st.file_uploader(loc["photo"], type=['png', 'jpg', 'jpeg'])
            notes = st.text_area(loc["notes"])
            submitted = st.form_submit_button(loc["submit"])

            if submitted:
                co2 = compute_co2(category, qty, factors)
                pts = points_for_co2(co2)
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "date": date_val.isoformat(),
                    "student": student,
                    "class_name": class_name,
                    "category": category,
                    "quantity": qty,
                    "unit": unit,
                    "photo": photo.getvalue() if photo else None,
                    "notes": notes,
                    "verified": 0,
                    "points": pts,
                    "co2": co2
                }
                add_entry_to_db(entry)
                # show equivalents for this entry
                trees_e = co2 / EQUIVALENTS['tree_seedlings_1yr'] if EQUIVALENTS['tree_seedlings_1yr'] else 0
                km_e = co2 / EQUIVALENTS['km_driven_car'] if EQUIVALENTS['km_driven_car'] else 0
                st.success(f"Saved — estimated {co2:.2f} kg CO₂.")
                st.info(f"Equivalent: {trees_e:.2f} tree-seedling-years, {km_e:.0f} km driving.")
                st.rerun()

    # -------------------------
    # LEADERBOARD
    # -------------------------
    elif page == loc["nav_leaderboard"]:
        st.header(loc["leaderboard"])
        entries = load_entries()
        if entries.empty:
            st.info(loc.get("no_entries", "No entries yet."))
        else:
            # Rank students by total CO2 saved (descending = top saved)
            leaderboard = (entries.groupby(['student', 'class_name'], dropna=False)
                           .agg(total_co2=('co2', 'sum'))
                           .reset_index())
            leaderboard['rank'] = leaderboard['total_co2'].rank(method='dense', ascending=False).astype(int)
            leaderboard = leaderboard.sort_values(['rank', 'total_co2'], ascending=[True, False])
            # Reorder columns for display
            leaderboard_display = leaderboard[['rank', 'student', 'class_name', 'total_co2']].rename(
                columns={'student': 'Student', 'class_name': 'Class/Section', 'total_co2': 'CO2 saved (kg)'}
            )
            st.dataframe(leaderboard_display)

    # -------------------------
    # ADMIN SETTINGS (password protected)
    # -------------------------
    elif page == loc["nav_admin"]:
        st.header(loc["settings"])
        pwd = st.text_input(loc["admin_password_prompt"], type="password")
        if pwd != ADMIN_PASSWORD:
            if pwd:
                st.error(loc["admin_auth_failed"])
            else:
                st.info("Admin access required to modify data.")
            return
        st.success(loc["admin_auth_ok"])

        # two-column layout: left = factors & verify; right = export & clear
        left, right = st.columns([2, 1])

        with left:
            st.subheader(loc["edit_factors"])
            factors_dict = get_factors()
            # show editable table using data_editor (returns edited DF)
            factors_df = pd.DataFrame(list(factors_dict.items()), columns=['category', 'factor'])
            edited = st.data_editor(factors_df, use_container_width=True, num_rows="dynamic")
            if st.button(loc["save_factors"]):
                # write back
                for _, row in edited.iterrows():
                    set_factor(row['category'], row['factor'])
                st.success("Factors saved.")
                st.experimental_rerun()

            # Verify entries list (unverified first)
            st.subheader("Verify student entries")
            entries = load_entries()
            if entries.empty:
                st.info(loc.get("no_entries", "No entries yet."))
            else:
                # show unverified entries first
                for _, row in entries.sort_values(['verified', 'timestamp']).iterrows():
                    cols = st.columns([4, 1])
                    with cols[0]:
                        verified_tag = "" if row['verified'] == 0 else "✅"
                        st.write(f"**{row['student']}** — {row['class_name']} — {row['category']} — {row['quantity']} {row['unit']} {verified_tag}")
                        st.write(f"CO₂: {row['co2']:.2f} kg — {row['date'].strftime('%Y-%m-%d') if not pd.isna(row['date']) else row['date']}")
                        if row.get('notes'):
                            st.write(row.get('notes'))
                    with cols[1]:
                        if row['verified'] == 0:
                            if st.button(f"Verify {int(row['id'])}", key=f"verify_{int(row['id'])}"):
                                verify_entry(int(row['id']))
                                st.success("Entry verified.")
                                st.rerun()
                        else:
                            st.write(loc["verified"])

        with right:
            st.subheader(loc["export_csv"])
            entries = load_entries()
            if not entries.empty:
                csv = entries.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, file_name="ecoschool_entries.csv", mime="text/csv")

            st.markdown("---")
            st.subheader(loc["clear_entries"])
            confirm = st.checkbox(loc["confirm_clear"])
            if confirm:
                if st.button(loc["danger_clear"]):
                    clear_all_entries()
                    st.warning("All entries deleted.")
                    st.rerun()

    # -------------------------
    # ABOUT
    # -------------------------
    elif page == loc["nav_about"]:
        st.header(loc["about"])
        st.write(loc["about_text"])
        st.write("Built with Python + Streamlit. Keep improving and learning!")

if __name__ == "__main__":
    main()
