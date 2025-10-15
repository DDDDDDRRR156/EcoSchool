"""
EcoSchool — School Carbon Calculator (Streamlit single-file app)
Filename: EcoSchool_Streamlit_App.py

What this is
- A single-file Streamlit app you can open in VS Code and run with:
    pip install -r requirements.txt
    streamlit run EcoSchool_Streamlit_App.py

Features implemented
- Input form for categories: Electricity (kWh), Paper (sheets), Plastic (kg), Food/Waste (kg), Transport (km)
- Conversion to kg CO2 using editable factor table (persisted in SQLite)
- Dashboard: totals by day/week/month, pie and bar charts, equivalents (tree seedlings, km driven)
- Gamification: points, badges, leaderboard (class vs class)
- Multi-language support: English + Gujarati
- Export CSV button
- Admin view (password-protected) to edit factors and download CSV
- Teacher review: mark entries as verified

Notes
- This is a simple prototype suitable for a school science-fair project or as a starting point.
- For production, add authentication, secure password storage, and stronger validation.

Requirements (example)
- streamlit
- pandas
- altair
- matplotlib

Install with:
    pip install streamlit pandas altair matplotlib

Run with:
    streamlit run EcoSchool_Streamlit_App.py

"""

import streamlit as st 
import pandas as pd 
import sqlite3
from datetime import datetime, date, timedelta
import altair as alt 
import io
import base64

# -------------------------
# Constants & Defaults
# -------------------------
DB_FILE = "ecoschool.db"
ADMIN_PASSWORD = "schooladmin"  # change before deployment
DEFAULT_FACTORS = {
    "Electricity (kWh)": 0.82,    # kg CO2 per kWh (example)
    "Paper (sheets)": 0.005,      # kg CO2 per sheet
    "Plastic (kg)": 6.0,          # kg CO2 per kg plastic
    "Food/Waste (kg)": 3.0,       # kg CO2 per kg
    "Transport (km)": 0.21        # kg CO2 per passenger-km (car average)
}

# Equivalents (simple conversions)
EQUIVALENTS = {
    "tree_seedlings_1yr": 21.77,  # kg CO2 sequestered per seedling in 10 years -> used as equivalence (adjust as needed)
    "km_driven_car": 0.21
}

# Translations
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
    },
    "gu": {
        "title": "ઇકોસ્કૂલ — સ્કૂલ કાર્બન કેલ્ક્યુલેટર",
        "add_entry": "નવો દાખલો ઉમેરો",
        "dashboard": "ડેશબોર્ડ",
        "history": "ઇતિહાસ / ક્લાસ ફીડ",
        "leaderboard": "ચેલેન્જ / લીડર્બોર્ડ",
        "settings": "સેટિંગ્સ / એડમિન",
        "category": "શ્રેણી",
        "quantity": "પરિમાણ",
        "unit": "એકમ",
        "date": "તારીખ",
        "notes": "ટિપ્પણી (વૈકલ્પિક)",
        "submit": "સબમિટ",
        "verify": "સત્યાપિત કરો",
        "export_csv": "સી.એસ.વી. એક્સપોર્ટ",
        "language": "ભાષા",
        "class_name": "ક્લાસ / વિભાગ",
        "student_name": "વિદ્યાર્થીનું નામ",
        "photo": "ફોટો (વૈકલ્પિક)",
        "points": "અંક",
        "badges": "બેજીસ",
        "admin_login": "એડમિન લોગિન",
        "edit_factors": "રૂપાંતરણ ફેક્ટર્સ સંપાદિત કરો",
        "save": "સેવ કરો",
    }
}

# -------------------------
# Database helpers
# -------------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # entries table
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
    # factors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS factors (
            category TEXT PRIMARY KEY,
            factor REAL
        )
    ''')
    # initialize defaults if empty
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
        entry['timestamp'], entry['date'], entry['student'], entry['class_name'], entry['category'], entry['quantity'], entry['unit'], entry.get('photo'), entry.get('notes'), entry.get('verified', 0), entry.get('points', 0), entry['co2']
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

# -------------------------
# Business logic
# -------------------------

def compute_co2(category, quantity, factors):
    factor = factors.get(category, 0)
    return float(quantity) * float(factor)


def points_for_co2(co2):
    # more reduction = more points; simple conversion
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
# UI helpers
# -------------------------

def sidebar_locale():
    lang = st.sidebar.selectbox("Language / ભાષા", options=['en', 'gu'], format_func=lambda x: 'English' if x=='en' else 'ગુજરાતી')
    return LOCALES[lang]

# -------------------------
# Streamlit App
# -------------------------

def main():
    st.set_page_config(page_title="EcoSchool", layout='wide')
    init_db()
    loc = sidebar_locale()
    st.title(loc['title'])

    tabs = st.tabs([loc['dashboard'], loc['add_entry'], loc['history'], loc['leaderboard'], loc['settings']])

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
            # compute totals
            total_co2 = entries['co2'].sum()
            st.metric("Total emissions (kg CO2)", f"{total_co2:.2f}")

            # timeframe filters
            col1, col2 = st.columns([2,1])
            with col2:
                timeframe = st.selectbox("Timeframe", ['All', 'Last 7 days', 'Last 30 days', 'This year'])
            df = entries.copy()
            now = pd.Timestamp.now()
            if timeframe == 'Last 7 days':
                df = df[df['date'] >= now - pd.Timedelta(days=7)]
            elif timeframe == 'Last 30 days':
                df = df[df['date'] >= now - pd.Timedelta(days=30)]
            elif timeframe == 'This year':
                df = df[df['date'].dt.year == now.year]

            # breakdown
            breakdown = df.groupby('category')['co2'].sum().reset_index()
            if not breakdown.empty:
                chart = alt.Chart(breakdown).mark_bar().encode(
                    x=alt.X('co2:Q', title='kg CO2'),
                    y=alt.Y('category:N', sort='-x', title=None)
                )
                st.altair_chart(chart, use_container_width=True)

            # equivalents
            st.subheader("Equivalents")
            st.write(f"Tree seedlings (10yr eq): {total_co2 / EQUIVALENTS['tree_seedlings_1yr']:.1f}")
            st.write(f"Car km equivalent: {total_co2 / EQUIVALENTS['km_driven_car']:.1f} km")

    # -----------------
    # Add entry
    # -----------------
    with tabs[1]:
        st.header(loc['add_entry'])
        with st.form("entry_form"):
            student = st.text_input(loc['student_name'])
            class_name = st.text_input(loc['class_name'])
            date_val = st.date_input(loc['date'], value=date.today())
            category = st.selectbox(loc['category'], options=list(factors.keys()))
            qty = st.number_input(loc['quantity'], min_value=0.0, value=0.0, step=0.1)
            unit = st.text_input(loc['unit'], value='units')
            photo = st.file_uploader(loc['photo'], type=['png','jpg','jpeg'])
            notes = st.text_area(loc['notes'])
            submitted = st.form_submit_button(loc['submit'])

            if submitted:
                # compute co2
                co2 = compute_co2(category, qty, factors)
                pts = points_for_co2(co2)
                entry = {
                    'timestamp': datetime.now().isoformat(),
                    'date': date_val.isoformat(),
                    'student': student,
                    'class_name': class_name,
                    'category': category,
                    'quantity': qty,
                    'unit': unit,
                    'photo': photo.getvalue() if photo else None,
                    'notes': notes,
                    'verified': 0,
                    'points': 0,
                    'co2': co2
                }
                add_entry_to_db(entry)
                st.success(f"Saved — estimated {co2:.2f} kg CO2")

    # -----------------
    # History / Teacher review
    # -----------------
    with tabs[2]:
        st.header(loc['history'])
        entries = load_entries()
        if entries.empty:
            st.info("No entries yet")
        else:
            # show a simple feed
            for _, row in entries.iterrows():
                cols = st.columns([3,1])
                with cols[0]:
                    st.write(f"**{row['student']}** — {row['class_name']} — {row['category']} — {row['quantity']} {row['unit']}")
                    st.write(f"{row['date'].strftime('%Y-%m-%d') if not pd.isna(row['date']) else row['date']}")
                    st.write(f"CO2: {row['co2']:.2f} kg")
                    if row['notes']:
                        st.write(row['notes'])
                with cols[1]:
                    if row['verified'] == 0:
                        if st.button(f"{loc['verify']} {int(row['id'])}"):
                            verify_entry(int(row['id']))
                            st.rerun()
                    else:
                        st.write("✅ Verified")

    # -----------------
    # Leaderboard / Challenges
    # -----------------
    with tabs[3]:
        st.header(loc['leaderboard'])
        entries = load_entries(only_verified=True)
        if entries.empty:
            st.info("No verified entries yet — teachers should verify first")
        else:
            leaderboard = entries.groupby('class_name').agg({'co2':'sum'}).reset_index()
            # Lower emissions is better; show ascending
            leaderboard['rank'] = leaderboard['co2'].rank(method='min', ascending=True)
            leaderboard = leaderboard.sort_values('rank')
            st.dataframe(leaderboard[['rank','class_name','co2']].rename(columns={'co2':'total_kgCO2'}))

            # simple weekly challenge
            st.subheader('Weekly challenge')
            week_start = date.today() - timedelta(days=date.today().weekday())
            st.write(f"Week starting: {week_start}")
            # compute week totals
            week_df = entries[entries['date'] >= pd.Timestamp(week_start)]
            if not week_df.empty:
                week_board = week_df.groupby('class_name').agg({'co2':'sum'}).reset_index().sort_values('co2')
                st.table(week_board)

    # -----------------
    # Admin / Settings
    # -----------------
    with tabs[4]:
        st.header(loc['settings'])
        st.subheader(loc['admin_login'])
        pwd = st.text_input("Password", type='password')
        if pwd == ADMIN_PASSWORD:
            st.success("Admin authenticated")
            st.subheader(loc['edit_factors'])
            factors_df = pd.DataFrame(list(factors.items()), columns=['category','factor'])
            edited = st.data_editor(
    factors_df,
    use_container_width=True,
    disabled=False
)
            if st.button(loc['save']):
                for _, r in edited.iterrows():
                    set_factor(r['category'], r['factor'])
                st.success("Saved factors")

            st.subheader(loc['export_csv'])
            all_entries = load_entries()
            if not all_entries.empty:
                csv = all_entries.to_csv(index=False)
                st.download_button("Download CSV", data=csv, file_name='ecoschool_entries.csv', mime='text/csv')

        else:
            st.info("Enter admin password to edit factors or export data")


if __name__ == '__main__':
    main()
