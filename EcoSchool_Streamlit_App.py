"""
EcoSchool — School Carbon Calculator (Streamlit single-file app)
Filename: EcoSchool_Streamlit_App.py

What this is
- A single-file Streamlit app you can open in VS Code and run with:
    pip install -r requirements.txt
    streamlit run EcoSchool_Streamlit_App.py

Features implemented
- Input form for categories: Paper (sheets), Plastic (kg), Food/Waste (kg), Transport (km)
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
import os
import streamlit as st 
import pandas as pd 
import sqlite3
from datetime import datetime, date, timedelta
import altair as alt 
import io
import base64
import random
import time

# -------------------------
# Constants & Defaults
# -------------------------
DB_FILE = "ecoschool.db"
ADMIN_PASSWORD = "schooladmin"  # change before deployment
DEFAULT_FACTORS = {
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
# -------------------------
# Suggestions to Reduce Emissions
# -------------------------
SUGGESTIONS = {
    "Paper (sheets)": [
        "Use both sides of the paper.",
        "Digitize notes instead of printing.",
        "Reuse scrap paper for drafts."
    ],
    "Plastic (kg)": [
        "Carry a reusable water bottle.",
        "Avoid single-use plastic packaging.",
        "Participate in school plastic recycling drives."
    ],
    "Food/Waste (kg)": [
        "Compost leftover food.",
        "Avoid food wastage by taking only what you need.",
        "Use reusable lunch containers instead of disposables."
    ],
    "Transport (km)": [
        "Walk or cycle for short distances.",
        "Use carpooling or public transport.",
        "Switch to electric or hybrid vehicles if possible."
    ]
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


# Flatten suggestions into (category, tip) tuples
ALL_TIPS = []
for cat, tips in SUGGESTIONS.items():
    for tip in tips:
        ALL_TIPS.append((cat, tip))

def get_image_base64(path):
    """Safely load an image as base64 string if it exists."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
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

def get_base64_logo(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

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
def sidebar_rotating_tip():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 Tip to Reduce Emissions")

    # Initialize index in session state
    if "tip_index" not in st.session_state:
        st.session_state.tip_index = random.randint(0, len(ALL_TIPS)-1)
        st.session_state.last_update = time.time()

    # Rotate tip every 60 seconds
    if time.time() - st.session_state.last_update > 60:
        st.session_state.tip_index = (st.session_state.tip_index + 1) % len(ALL_TIPS)
        st.session_state.last_update = time.time()
        st.rerun()  # Force rerun to update sidebar

    # Display current tip
    cat, tip = ALL_TIPS[st.session_state.tip_index]
    st.sidebar.markdown(f"**{cat}**")
    st.sidebar.markdown(f"- {tip}")


# -------------------------
# Streamlit App
# -------------------------
def main():
    st.set_page_config(page_title="EcoSchool", layout='wide', page_icon="app_icon.png")
    init_db()
    loc = sidebar_locale()
    sidebar_rotating_tip()
    st.markdown("""
<style>
/* hide label inside metric */
div[data-testid="stMetricLabel"] {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)
    st.markdown("""
<style>
div[data-testid="stMetricValue"] {
    font-size: 2.5rem;      /* Adjust number as you like */
    font-weight: 700;       /* Optional: make it bold */
    color: #4CAF50;         /* Optional: change text color */
}
</style>
""", unsafe_allow_html=True)
    logo_b64 = get_base64_logo("logo.png")
    st.markdown(f"""
<div style="display:flex; align-items:center;">
    <img src="data:image/png;base64,{logo_b64}" style="height:60px; margin-right:15px;">
    <h1 style="font-size:2.2rem; font-weight:700;">EcoSchool — School Carbon Calculator</h1>
</div>
""", unsafe_allow_html=True)
    
    tabs = st.tabs([loc['dashboard'], loc['add_entry'], loc['leaderboard'], loc['settings']])

    factors = get_factors()
    with tabs[0]:
        st.header(loc['dashboard'])
        entries = load_entries()
        if entries is not None and len(entries) > 0:
            df = pd.DataFrame(entries)
            df['date'] = pd.to_datetime(df['date'])
        else:
            st.info("No entries yet!")
            df = pd.DataFrame(columns=['date','student','class_name','category','quantity','unit','co2'])          
            # timeframe filters
            col1, col2 = st.columns([2,1])
            with col2:
                timeframe = st.selectbox("Timeframe", ['All', 'Last 7 days', 'Last 30 days', 'Last 365 days'])
            df = entries.copy()
            now = pd.Timestamp.now()
            if timeframe == 'Last 7 days':
                df = df[df['date'] >= now - pd.Timedelta(days=7)]
            elif timeframe == 'Last 30 days':
                df = df[df['date'] >= now - pd.Timedelta(days=30)]
            elif timeframe == 'Last 365 days':
                df = df[df['date'] >= now - pd.Timedelta(days=365)]

            # compute totals
            total_co2 = entries['co2'].sum()
            st.markdown('<div style="font-size:20px; font-weight:600; color:#ffffff;">Total Emissions(kg CO2)</div>', unsafe_allow_html=True)
            st.metric(label="", value=f"{total_co2:.2f}")

            # New: Expandable Class-wise Breakdown
            with st.expander("📊 Class-wise Breakdown / વર્ગ-વાર વિભાજન"):
                if df.empty:
                    st.info("No data for the selected timeframe.")
                else:
                    class_breakdown = df.groupby('class_name')['co2'].sum().reset_index().sort_values(by='co2', ascending=True)
                    if not class_breakdown.empty:
                        chart = alt.Chart(class_breakdown).mark_bar().encode(
                            x=alt.X('co2:Q', title='kg CO2'),
                            y=alt.Y('class_name:N', sort='-x', title='Class / Section')
                        )
                        st.altair_chart(chart, use_container_width=True)
                        # Optional: Show as table too
                        st.dataframe(class_breakdown.rename(columns={'class_name': 'Class / Section', 'co2': 'Total CO₂ (kg)'}).style.format({'Total CO₂ (kg)': '{:.2f}'}))
                    else:
                        st.info("No class data available.")

            # breakdown
            breakdown = df.groupby('category')['co2'].sum().reset_index()
            if not breakdown.empty:
                chart = alt.Chart(breakdown).mark_bar().encode(
                    x=alt.X('co2:Q', title='kg CO2'),
                    y=alt.Y('category:N', sort='-x', title=None)
                )
                st.altair_chart(chart, use_container_width=True)

            # Weekly Top 3 Leaderboard (added above Equivalents)
            st.markdown("""<h1>🏆 Weekly Top 3 / સાપ્તાહિક ટોપ 3</h1>""",unsafe_allow_html=True)
            weekly_entries = load_entries(only_verified=True)
            if not weekly_entries.empty:
                weekly_df = weekly_entries[weekly_entries['date'] >= now - pd.Timedelta(days=7)]
                if not weekly_df.empty:
                    weekly_leaderboard = weekly_df.groupby(['student', 'class_name']).agg({'co2':'sum'}).reset_index()
                    weekly_leaderboard = weekly_leaderboard.sort_values(by='co2', ascending=True).reset_index(drop=True).head(3)
                    weekly_leaderboard['rank'] = weekly_leaderboard.index + 1
                    for _, row in weekly_leaderboard.iterrows():
                        st.markdown(f"<p style='font-size: 30px;'><strong>{row['rank']}. {row['student']} ({row['class_name']})</strong> — {row['co2']:.2f} kg CO₂ emitted</p>", unsafe_allow_html=True)
                else:
                    st.info("No verified entries in the last 7 days.")
            else:
                st.info("No verified entries yet.")
            # equivalents
            st.markdown("""<hr>
            <h1>
            🌍 Equivalents / સમકક્ષ મૂલ્યો 
            </h1>
            """,unsafe_allow_html=True)
            st.markdown('<div style="font-size:20px; font-weight:600; color:#ffffff;">🌳 Trees Planted / વાવવામાં આવેલા વૃક્ષો</div>', unsafe_allow_html=True)
            st.metric(label="", value=round(total_co2 / 21, 2))  # 1 tree ≈ 21 kg CO₂/year
            st.markdown('<div style="font-size:20px; font-weight:600; color:#ffffff;">🚗 Car Kilometers Avoided / ટાળેલા કાર કિલોમીટર</div>', unsafe_allow_html=True)
            st.metric(label="", value=round(total_co2 / 0.25, 2))  # 1 km ≈ 0.25 kg CO₂
            st.markdown('<div style="font-size:20px; font-weight:600; color:#ffffff;">💡 Energy Conserved (kWh) / બચાવેલી ઊર્જા (કિલોવોટ કલાક)</div>', unsafe_allow_html=True)
            st.metric(label="", value=round(total_co2 / 0.92, 2))  # 1 kWh ≈ 0.92 kg CO₂
            st.markdown("""
<p style='font-size: 20px;'><b>ℹ️ About these equivalents / આ સમકક્ષ મૂલ્યો વિશે:</b></p>  
<div style='font-size: 20px;'>- 🌳 1 tree absorbs roughly 21 kg of CO₂ per year. </div>
  <div style='font-size: 20px;'>→ 1 વૃક્ષ દર વર્ષે આશરે 21 કિલોગ્રામ CO₂ શોષી લે છે.</div>
<div style='font-size: 20px;'>- 🚗 Driving 1 km in an average petrol car emits about 0.25 kg of CO₂. </div>
  <div style='font-size: 20px;'>→ સરેરાશ પેટ્રોલ કાર 1 કિ.મી. દોડે ત્યારે આશરે 0.25 કિલોગ્રામ CO₂ ઉત્સર્જિત કરે છે.</div>
<div style='font-size: 20px;'>- 💡 Using 1 kWh of electricity produces around 0.92 kg of CO₂.  </div>
  <div style='font-size: 20px;'>→ 1 કિલોવોટ કલાક વીજળીના ઉપયોગથી આશરે 0.92 કિલોગ્રામ CO₂ ઉત્પન્ન થાય છે.</div><br>
<p style='font-size: 20px;'>These values are approximate and meant to help visualize the environmental impact.  
→ આ મૂલ્યો અંદાજિત છે અને પર્યાવરણ પરના પ્રભાવને સમજવામાં મદદરૂપ છે.</p>
""", unsafe_allow_html=True)
            st.markdown("""<hr>
<h1>🏫 About EcoSchool / ઇકોસ્કૂલ વિશે</h1>

<p style='font-size: 20px;'><b>EcoSchool</b>(also called <i>EcoMeter for Schools</i>) is a simple, interactive platform designed to help students and teachers track and reduce their school's carbon footprint.  
Through small, everyday actions—like saving paper, reducing waste, or using eco-friendly transport—users can record their contributions and see how they make a difference for the planet.</p>

<h2>🌱 What the App Does</h2>
<div style='font-size: 20px;'>- <b>📊 Carbon Calculator:</b> Converts activities such as paper use, waste, and transport into CO₂ emissions (in kilograms).  
<div style='font-size: 20px;'>- <b>📈 Dashboard:</b> Displays total emissions, category-wise breakdown, and real-world equivalents like <i>trees planted</i> or <i>energy conserved</i>.  
<div style='font-size: 20px;'>- <b>🏆 Leaderboard:</b> Encourages friendly competition between classes to promote sustainability.  
<div style='font-size: 20px;'>- <b>🌐 Multi-language Support:</b> Available in <b>English and Gujarati</b>, making it inclusive for all students.  
<div style='font-size: 20px;'>- <b>📤 Reports & Admin Tools:</b> Teachers can verify entries, edit emission factors, and export reports for projects or fairs.

<h2>👩‍🏫 User Roles</h2>
<div style='font-size: 20px;'>- <b>Students:</b> Log daily eco-friendly actions and upload evidence. </div> 
<div style='font-size: 20px;'>- <b>Teachers:</b> Review and verify student submissions.  </div>
<div style='font-size: 20px;'>- <b>Admins:</b> Manage emission factors, export data, and set sustainability challenges.</div>

<h2>EcoSchool empowers every student to become a <i>climate champion</i>, one action at a time. 🌍✨</h2>
<hr>
""", unsafe_allow_html=True)

        # -----------------
    # Add entry
    # -----------------
    with tabs[1]:
        st.header(loc['add_entry'])
        with st.form("entry_form"):
            student = st.text_input(loc['student_name'] + " *", value="")
            class_name = st.text_input(loc['class_name'] + " *", value="")
            date_val = st.date_input(loc['date'], value=date.today())
            category_options = [c for c in factors.keys() if c != "Electricity"]
            category = st.selectbox(loc['category'], options=category_options)
            qty = st.number_input(loc['quantity'] + " *", min_value=0.0, value=0.0, step=0.1)
            unit = st.selectbox(loc['unit'], options=['sheets', 'kg', 'km', 'items'])
            photo = st.file_uploader(loc['photo'], type=['png','jpg','jpeg'])
            notes = st.text_area(loc['notes'])
            submitted = st.form_submit_button(loc['submit'])

            if submitted:
                # Validation for required fields
                if not student.strip():
                    st.error("Student name is required.")
                elif not class_name.strip():
                    st.error("Class/Section is required.")
                elif qty <= 0:
                    st.error("Quantity must be greater than 0.")
                else:
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
                    st.success(f"Response Saved — recorded {co2:.2f} kg CO₂ emitted")
                    st.markdown("### 💡 Suggestions to reduce CO₂ emissions:")
                    for tip in SUGGESTIONS.get(category, []):
                        st.markdown(f"- {tip}")


    # -----------------
    # Leaderboard / Challenges
    # -----------------
    with tabs[2]:
        st.header(loc['leaderboard'])# Timeframe filter
        st.markdown("### 🏫 Class / Section CO₂ Emitted Comparison")
        class_emissions = df.groupby('class_name')['co2'].sum().reset_index()
        class_emissions = class_emissions.sort_values(by='co2', ascending=True)
        st.dataframe(
            class_emissions.rename(columns={
                'class_name': 'Class / Section',
                'co2': 'Total CO₂ Emitted (kg)'
            }).style.background_gradient(subset=['Total CO₂ Emitted (kg)'], cmap='Reds').format({
                'Total CO₂ Emission (kg)': '{:.2f}'
            }),
            use_container_width=True
    )
        timeframe = st.selectbox("Select timeframe", ["All Time", "Last 7 Days", "Last 30 Days", "Last 365 Days"])
        entries = load_entries(only_verified=True)
        if entries.empty:
            st.info("No verified entries yet — teachers should verify first")
        else:
            df = entries.copy()
            now = pd.Timestamp.now()
            if timeframe == "Last 7 Days":
                df = df[df['date'] >= now - pd.Timedelta(days=7)]
            elif timeframe == "Last 30 Days":
                df = df[df['date'] >= now - pd.Timedelta(days=30)]
            elif timeframe == "Last 365 Days":
                df = df[df['date'] >= now - pd.Timedelta(days=365)]
            leaderboard = df.groupby(['student', 'class_name']).agg({'co2':'sum'}).reset_index()
            leaderboard = leaderboard.sort_values(by='co2', ascending=True).reset_index(drop=True)
            leaderboard['rank'] = leaderboard.index + 1
            def title_for_rank(rank):
                if rank == 1:
                    return "🌟 Carbon Star"
                elif rank <= 3:
                    return "🥈 Eco Champion"
                elif rank <= 10:
                    return "🌿 Green Hero"
                else:
                    return "🌱 Seedling"
            leaderboard['Title'] = leaderboard['rank'].apply(title_for_rank)  
            st.subheader(f"Leaderboard — {timeframe}")
            leaderboard = leaderboard.sort_values(by="rank", ascending=True)
            st.dataframe(
                leaderboard[["rank", "Title", "student", "class_name", "co2"]].rename(columns={
        "rank": "Rank",
        "Title": "Activity",
        "student": "Student",
        "class_name": "Class",
        "co2": "CO₂ Emitted (kg)"
    }),
    use_container_width=True
)

            
            # -----------------# Admin / Settings# -----------------
    with tabs[3]:
        st.header(loc['settings'])
        st.subheader(loc['admin_login'])
        pwd = st.text_input("Password", type='password')
        if pwd == ADMIN_PASSWORD:
            st.success("Admin authenticated")# Moved History / Teacher review section here
            st.subheader(loc['history'])
            entries = load_entries()
            if entries.empty:
                st.info("No entries yet")
            else:# show a simple feed
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
            st.subheader(loc['edit_factors'])
            factors_df = pd.DataFrame(list(factors.items()), columns=['category','factor'])
            edited = st.data_editor(
                factors_df,
                use_container_width=True,
                disabled=False)
            if st.button(loc['save']):
                for _, r in edited.iterrows():
                    set_factor(r['category'], r['factor'])
                st.success("Saved factors")
            st.subheader(loc['export_csv'])
            all_entries = load_entries()
            if not all_entries.empty:
                csv = all_entries.to_csv(index=False)
                st.download_button("Download CSV", data=csv, file_name='ecoschool_entries.csv', mime='text/csv')
                # New: Clear All Entries option
            st.subheader("Clear All Entries")
            st.warning("⚠️ This action will permanently delete all entries. Proceed with caution!")
            if st.button("Clear All Entries"):
                clear_all_entries()
                st.success("All entries have been cleared.")
                st.rerun()  # Refresh the page to update the view
        else:
            st.info("Enter admin password to edit factors or export data")
import streamlit as st

# Assuming you have a function to get base64 encoded images, e.g.:
# def get_image_base64(image_path):
#     # Your implementation here to return base64 string

# Load icons safely
icons = {
    "phone": get_image_base64("phone.png"),
    "email": get_image_base64("email.png"),
    "instagram": get_image_base64("instagram.png"),
    "facebook": get_image_base64("facebook.png")
}

# Fallback URLs (if local icons aren't found)
fallbacks = {
    "phone": "https://cdn-icons-png.flaticon.com/512/597/597177.png",
    "email": "https://cdn-icons-png.flaticon.com/512/561/561127.png",
    "instagram": "https://cdn-icons-png.flaticon.com/512/1384/1384031.png",
    "facebook": "https://cdn-icons-png.flaticon.com/512/1384/1384005.png"
}

def icon_html(name, href="#"):
    if icons[name]:
        src = f"data:image/png;base64,{icons[name]}"
    else:
        src = fallbacks[name]
    return f'<a href="{href}" target="_blank"><img src="{src}" height="28" style="margin:0 8px;"></a>'

# --- Sticky Footer ---
footer_html = f"""
<style>
footer {{
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f0f0f0;
    color: #333;
    text-align: center;
    padding: 12px 0;
    font-size: 14px;
    border-top: 1px solid #ccc;
    z-index: 100;
}}
footer img {{
    width: 28px;
    margin: 0 10px;
    vertical-align: middle;
}}
footer img:hover {{
    transform: scale(1.15);
    transition: 0.3s;
}}
</style>

<footer>
    <div>
        <strong style='font-size: 15px;'>EcoSchool — Building a Greener Tomorrow 🌿</strong>
    </div>
    <div style="margin-top:6px;">
        {icon_html('phone', 'tel:+918780695872')}
        {icon_html('email', 'mailto:nagarshaurya70@gmail.com')}
        {icon_html('instagram', 'https://www.instagram.com')}
        {icon_html('facebook', 'https://www.facebook.com')}
    </div>
    <div style="margin-top:6px;">
        Contact: <b>Shaurya Nagar</b> — +91 8780 69 5872
    </div>
    <div style="font-size:12px; margin-top:4px;">
        © 2025 EcoSchool | <a href="#" style="color:#2E8B57;">Privacy Policy</a> | 
        <a href="#" style="color:#2E8B57;">Terms of Use</a>
    </div>
</footer>
"""

st.markdown(footer_html, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
