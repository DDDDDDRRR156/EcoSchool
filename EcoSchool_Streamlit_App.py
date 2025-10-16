import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# -----------------
# Database setup
# -----------------
DB_NAME = "eco_school.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
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
            verified INTEGER,
            points REAL,
            co2 REAL
        )
    """)
    conn.commit()
    conn.close()

def add_entry_to_db(entry):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO entries (timestamp, date, student, class_name, category, quantity, unit, photo, notes, verified, points, co2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry['timestamp'], entry['date'], entry['student'], entry['class_name'],
        entry['category'], entry['quantity'], entry['unit'], entry['photo'],
        entry['notes'], entry['verified'], entry['points'], entry['co2']
    ))
    conn.commit()
    conn.close()

def load_entries_from_db():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM entries", conn)
    conn.close()
    return df

def clear_entries_from_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM entries")
    conn.commit()
    conn.close()

def save_entries_to_csv(df):
    df.to_csv("eco_entries_saved.csv", index=False)

# -----------------
# Conversion Factors
# -----------------
factors = {
    "Paper": 0.004,        # kg CO2 per sheet
    "Plastic": 2.5,        # kg CO2 per kg
    "Food/Waste": 1.9,     # kg CO2 per kg
    "Transport": 0.12      # kg CO2 per km
}

def compute_co2(category, quantity, factors):
    return quantity * factors.get(category, 0)

def points_for_co2(co2):
    return max(0, 100 - co2)

# -----------------
# Localization
# -----------------
LOCALIZATION = {
    "English": {
        "dashboard": "Dashboard",
        "add_entry": "Add Entry",
        "admin": "Admin Settings",
        "about": "About",
        "student_name": "Student Name",
        "class_name": "Class",
        "date": "Date",
        "category": "Category",
        "quantity": "Quantity",
        "unit": "Unit",
        "photo": "Upload Photo (optional)",
        "notes": "Notes",
        "submit": "Submit Entry",
        "equivalents": "CO₂ Equivalents",
        "nav": "Navigation",
        "about_text": "EcoSchool helps track your school's environmental footprint.",
        "clear_entries": "Clear All Entries",
        "confirm_clear": "I understand this will permanently delete all entries",
    },
    "Gujarati": {
        "dashboard": "ડૅશબોર્ડ",
        "add_entry": "એન્ટ્રી ઉમેરો",
        "admin": "એડમિન સેટિંગ્સ",
        "about": "વિશે",
        "student_name": "વિદ્યાર્થીનું નામ",
        "class_name": "વર્ગ",
        "date": "તારીખ",
        "category": "વર્ગીકરણ",
        "quantity": "જથ્થો",
        "unit": "એકમ",
        "photo": "ફોટો અપલોડ કરો (વૈકલ્પિક)",
        "notes": "નોંધો",
        "submit": "સબમિટ કરો",
        "equivalents": "CO₂ સમકક્ષ",
        "nav": "નેવિગેશન",
        "about_text": "ઇકોસ્કૂલ તમારા શાળાના પર્યાવરણના ફૂટપ્રિન્ટને ટ્રૅક કરવામાં મદદ કરે છે.",
        "clear_entries": "બધી એન્ટ્રીઓ સાફ કરો",
        "confirm_clear": "હું સમજું છું કે આ બધા ડેટાને કાયમ માટે કાઢી નાખશે",
    }
}

# -----------------
# Main App
# -----------------
def main():
    st.set_page_config(page_title="EcoSchool App", page_icon="🌿", layout="wide")
    init_db()

    # Sidebar
    st.sidebar.title("EcoSchool 🌿")
    language = st.sidebar.selectbox("Language / ભાષા", ["English", "Gujarati"])
    loc = LOCALIZATION[language]

    st.sidebar.markdown("---")
    st.sidebar.write(loc['nav'])

    tabs = st.tabs([loc['dashboard'], loc['add_entry'], loc['admin'], loc['about']])

    # -----------------
    # Dashboard
    # -----------------
    with tabs[0]:
        st.header(loc['dashboard'])
        entries_df = load_entries_from_db()

        if not entries_df.empty:
            total_co2 = entries_df['co2'].sum()
            total_points = entries_df['points'].sum()

            st.metric("🌍 Total CO₂ Emitted", f"{total_co2:.2f} kg")
            st.metric("🏅 Total Points", int(total_points))

            st.subheader(loc['equivalents'])
            st.write("""
            🌿 These equivalents help you visualize your environmental impact:
            - 1 kg of CO₂ ≈ driving 4 km  
            - 1 kg of CO₂ ≈ 122 smartphone charges  
            - 1 tree absorbs ≈ 21.7 kg CO₂ per year
            """)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🚗 Equivalent Car Distance", f"{total_co2 * 4:.1f} km")
            with col2:
                st.metric("🔋 Equivalent Phone Charges", f"{total_co2 * 122:.0f} charges")
            with col3:
                st.metric("🌳 Equivalent Trees Needed", f"{total_co2 / 21.7:.1f} trees")

            st.bar_chart(entries_df.groupby("category")["co2"].sum())

            st.dataframe(entries_df)
        else:
            st.info("No entries yet. Add some from the 'Add Entry' tab!")

    # -----------------
    # Add Entry
    # -----------------
    with tabs[1]:
        st.header(loc['add_entry'])
        with st.form("entry_form"):
            student = st.text_input(loc['student_name'])
            class_name = st.text_input(loc['class_name'])
            date_val = st.date_input(loc['date'], value=date.today())

            category_options = [c for c in factors.keys() if c != "Electricity"]
            category = st.selectbox(loc['category'], options=category_options)

            qty = st.number_input(loc['quantity'], min_value=0.0, value=0.0, step=0.1)
            unit = st.selectbox(loc['unit'], options=['kg', 'liters', 'sheets', 'items', 'packets'])

            photo = st.file_uploader(loc['photo'], type=['png', 'jpg', 'jpeg'])
            notes = st.text_area(loc['notes'])
            submitted = st.form_submit_button(loc['submit'])

            if submitted:
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
                    'points': pts,
                    'co2': co2
                }
                add_entry_to_db(entry)
                st.success(f"✅ Entry saved! Estimated {co2:.2f} kg CO₂.")
                st.experimental_rerun()

    # -----------------
    # Admin Settings
    # -----------------
    with tabs[2]:
        st.header(loc['admin'])
        df = load_entries_from_db()

        if not df.empty:
            st.dataframe(df)

            # Save to CSV
            if st.button("💾 Save Entries to File"):
                save_entries_to_csv(df)
                st.success("Entries saved as eco_entries_saved.csv")

            # Download CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download data as CSV", data=csv, file_name="eco_entries.csv", mime="text/csv")

            st.markdown("---")

            # Clear Entries Section
            st.subheader(loc['clear_entries'])
            confirm = st.checkbox(loc['confirm_clear'])
            if confirm and st.button("🗑️ Clear All Entries", type="primary"):
                clear_entries_from_db()
                st.warning("All entries have been cleared from the database!")
                st.experimental_rerun()
        else:
            st.info("No entries yet!")

    # -----------------
    # About Tab
    # -----------------
    with tabs[3]:
        st.header(loc['about'])
        st.write(loc['about_text'])
        st.write("""
        Developed by students to promote sustainability.  
        Built with ❤️ using Python and Streamlit.
        """)

# -----------------
# Run app
# -----------------
if __name__ == "__main__":
    main()
