# EcoSchool_Streamlit_App.py
# -------------------------
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import altair as alt

# -------------------------
# Configuration
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

# -------------------------
# Localization (English + Gujarati)
# -------------------------
LOCALES = {
    "en": {
        "app_title": "EcoSchool — School Carbon Calculator",
        "dashboard": "Dashboard",
        "add_entry": "Add Entry",
        "history": "History / Class Feed",
        "leaderboard": "Leaderboard",
        "settings": "Admin Settings",
        "student_name": "Student Name",
        "class_name": "Class / Section",
        "category": "Category",
        "quantity": "Quantity",
        "unit": "Unit",
        "date": "Date",
        "submit": "Submit",
        "verify": "Verify",
        "verified": "✅ Verified",
        "export_csv": "Export CSV",
        "clear_entries": "Clear all entries",
        "confirm_clear": "I understand this will permanently delete all entries",
        "danger_clear": "Yes, delete all entries",
        "units_options": ['sheets', 'kg', 'litres', 'items', 'km', 'units'],
        "equiv_explanation": "Equivalents show CO₂ impact in terms of tree seedlings grown for 1 year and km driven by a car.",
        "timeframe": "Select timeframe",
        "last_week": "Last 7 days",
        "last_month": "Last 30 days",
        "last_year": "Last 365 days",
        "all_time": "All time"
    },
    "gu": {
        "app_title": "ઇકોસ્કૂલ — સ્કૂલ કાર્બન કેલ્ક્યુલેટર",
        "dashboard": "ડેશબોર્ડ",
        "add_entry": "નવો દાખલો ઉમેરો",
        "history": "ઇતિહાસ / ક્લાસ ફીડ",
        "leaderboard": "લીડર્બોર્ડ",
        "settings": "એડમિન સેટિંગ્સ",
        "student_name": "વિદ્યાર્થીનું નામ",
        "class_name": "ક્લાસ / વિભાગ",
        "category": "શ્રેણી",
        "quantity": "પરિમાણ",
        "unit": "એકમ",
        "date": "તારીખ",
        "submit": "સબમિટ",
        "verify": "સત્યાપિત કરો",
        "verified": "✅ સત્યાપિત",
        "export_csv": "સી.એસ.વી. એક્સપોર્ટ",
        "clear_entries": "બધી એન્ટ્રી સાફ કરો",
        "confirm_clear": "મને ખબર છે કે આ સંપૂર્ણ રીતે ડિલીટ કરશે",
        "danger_clear": "હા, બધી એન્ટ્રી ડિલીટ કરો",
        "units_options": ['શીટ્સ', 'કિ.ગ્રા', 'લિટર', 'આઇટમ્સ', 'કિ.મી', 'એકમ'],
        "equiv_explanation": "એક્વિવલન્ટ્સ બતાવે છે CO₂નો પ્રભાવ 1 વર્ષના વૃક્ષ અને કાર દ્વારા ચાલેલા કિ.મીના રૂપમાં.",
        "timeframe": "સમયગાળો પસંદ કરો",
        "last_week": "છેલ્લા 7 દિવસ",
        "last_month": "છેલ્લા 30 દિવસ",
        "last_year": "છેલ્લા 365 દિવસ",
        "all_time": "બધું સમય"
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
        INSERT INTO entries (timestamp, date, student, class_name, category, quantity, unit, notes, verified, points, co2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (entry['timestamp'], entry['date'], entry['student'], entry['class_name'],
          entry['category'], entry['quantity'], entry['unit'], entry['notes'],
          entry['verified'], entry['points'], entry['co2']))
    conn.commit()
    conn.close()

def load_entries():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT * FROM entries ORDER BY timestamp DESC', conn)
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def verify_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE entries SET verified=1 WHERE id=?', (entry_id,))
    conn.commit()
    conn.close()

def clear_entries():
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
    return int(round(max(1, co2*2)))

# -------------------------
# Streamlit App
# -------------------------
def main():
    st.set_page_config(page_title="EcoSchool", layout="wide")
    init_db()

    # Sidebar for language and navigation
    lang_choice = st.sidebar.selectbox("Language / ભાષા", ['English', 'ગુજરાતી'])
    loc = LOCALES['en'] if lang_choice=='English' else LOCALES['gu']

    page = st.sidebar.radio("Navigation / નાવિગેશન", [loc['dashboard'], loc['add_entry'], loc['history'], loc['leaderboard'], loc['settings']])
    factors = get_factors()

    # ---------------- Dashboard ----------------
    if page == loc['dashboard']:
        st.header(loc['dashboard'])
        entries = load_entries()
        if entries.empty:
            st.info("No entries yet")
        else:
            # Timeframe filter for graph
            timeframe = st.selectbox(loc['timeframe'], [loc['all_time'], loc['last_week'], loc['last_month'], loc['last_year']])
            df = entries.copy()
            now = pd.Timestamp.now()
            if timeframe == loc['last_week']:
                df = df[df['date'] >= now - pd.Timedelta(days=7)]
            elif timeframe == loc['last_month']:
                df = df[df['date'] >= now - pd.Timedelta(days=30)]
            elif timeframe == loc['last_year']:
                df = df[df['date'] >= now - pd.Timedelta(days=365)]

            total_co2 = df['co2'].sum()
            st.metric("Total emissions (kg CO2)", f"{total_co2:.2f}")

            st.subheader("Equivalents / એક્વિવલન્ટ્સ")
            st.write(loc['equiv_explanation'])
            st.write(f"Tree seedlings (10yr eq): {total_co2 / EQUIVALENTS['tree_seedlings_1yr']:.1f}")
            st.write(f"Car km equivalent: {total_co2 / EQUIVALENTS['km_driven_car']:.1f} km")

            breakdown = df.groupby('category')['co2'].sum().reset_index()
            if not breakdown.empty:
                chart = alt.Chart(breakdown).mark_bar().encode(
                    x='co2:Q', y=alt.Y('category:N', sort='-x')
                )
                st.altair_chart(chart, use_container_width=True)

    # ---------------- Add Entry ----------------
    elif page == loc['add_entry']:
        st.header(loc['add_entry'])
        with st.form("entry_form"):
            student = st.text_input(loc['student_name'])
            class_name = st.text_input(loc['class_name'])
            date_val = st.date_input(loc['date'], value=date.today())
            category_options = [c for c in factors.keys()]
            category = st.selectbox(loc['category'], options=category_options)
            qty = st.number_input(loc['quantity'], min_value=0.0, value=0.0, step=0.1)
            unit = st.selectbox(loc['unit'], options=loc['units_options'])
            notes = st.text_area("Notes / ટિપ્પણી (optional)")
            submitted = st.form_submit_button(loc['submit'])
            if submitted:
                co2 = compute_co2(category, qty, factors)
                pts = points_for_co2(co2)
                entry = {'timestamp': datetime.now().isoformat(), 'date': date_val.isoformat(),
                         'student': student, 'class_name': class_name, 'category': category,
                         'quantity': qty, 'unit': unit, 'notes': notes, 'verified':0,
                         'points':pts, 'co2':co2}
                add_entry_to_db(entry)
                st.success(f"Saved — estimated {co2:.2f} kg CO2")

    # ---------------- History / Teacher Review ----------------
    elif page == loc['history']:
        st.header(loc['history'])
        entries = load_entries()
        if entries.empty:
            st.info("No entries yet")
        else:
            for _, row in entries.iterrows():
                cols = st.columns([3,1])
                with cols[0]:
                    st.write(f"**{row['student']}** — {row['class_name']} — {row['category']} — {row['quantity']} {row['unit']}")
                    st.write(f"CO2: {row['co2']:.2f} kg")
                    st.write(row['date'].strftime('%Y-%m-%d'))
                    if row['notes']:
                        st.write(row['notes'])
                with cols[1]:
                    if row['verified']==0:
                        if st.button(f"{loc['verify']} {row['id']}"):
                            verify_entry(row['id'])
                            st.experimental_rerun()
                    else:
                        st.write(loc['verified'])

    # ---------------- Leaderboard ----------------
    elif page == loc['leaderboard']:
        st.header(loc['leaderboard'])
        entries = load_entries()
        if entries.empty:
            st.info("No entries yet")
        else:
            df = entries[entries['verified']==1].copy()
            df['rank'] = df['co2'].rank(method='min', ascending=False)
            df = df.sort_values('rank')
            st.dataframe(df[['rank','student','class_name','co2']].rename(columns={'co2':'CO2_saved_kg'}))

    # ---------------- Admin Settings ----------------
    elif page == loc['settings']:
        st.header(loc['settings'])
        pwd = st.text_input("Password / પાસવર્ડ", type='password')
        if pwd==ADMIN_PASSWORD:
            st.success("Admin authenticated / એડમિન સત્તાવાર")
            all_entries = load_entries()
            if not all_entries.empty:
                csv = all_entries.to_csv(index=False)
                st.download_button(loc['export_csv'], data=csv, file_name='ecoschool_entries.csv', mime='text/csv')

            if st.button("Verify all entries / બધી સત્યાપિત કરો"):
                for _, row in all_entries.iterrows():
                    verify_entry(row['id'])
                st.success("All entries verified / બધી સત્યાપિત")

            if st.checkbox(loc['confirm_clear']):
                if st.button(loc['danger_clear']):
                    clear_entries()
                    st.success("All entries cleared / બધી એન્ટ્રી સાફ")

            st.subheader("Edit Conversion Factors / રૂપાંતરણ ફેક્ટર્સ સંપાદિત કરો")
            factors_df = pd.DataFrame(list(factors.items()), columns=['category','factor'])
            edited = st.data_editor(factors_df, use_container_width=True)
            if st.button("Save factors / સેવ કરો"):
                for _, r in edited.iterrows():
                    set_factor(r['category'], r['factor'])
                st.success("Factors saved / ફેક્ટર્સ સેવ થયા")
        else:
            st.info("Enter admin password to access settings / સેટિંગ્સ જોવા માટે પાસવર્ડ દાખલ કરો")

if __name__=="__main__":
    main()
