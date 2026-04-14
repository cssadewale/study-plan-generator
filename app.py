"""
app.py — Streamlit UI for the Personalised Study Plan Generator
===============================================================
Author: Adewale Samson Adeagbo
Project: Personalised Study Plan Generator — Phase 1

This is the front door of the application.
It collects student data, calls the analyzer and scheduler,
and displays the results in a clean, readable format.

Structure:
  1. Page config and custom CSS styling
  2. Sidebar: student info + mode selection
  3. Section A: Score Input (manual form OR CSV upload)
  4. Section B: Analysis Results (weakness breakdown)
  5. Section C: Weekly Timetable (with deferred list if any)
  6. Section D: Export (download timetable as CSV)

Run this file with:
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io

# Import our custom modules
from analyzer import (
    analyze_subject_level,
    analyze_topic_level,
    generate_summary,
)
from scheduler import generate_timetable


# ─────────────────────────────────────────────
# SECTION 1: PAGE CONFIG AND STYLING
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Study Plan Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — warm, student-friendly design
# Colours: deep green (trust, growth) + amber (energy, urgency) + soft white bg
st.markdown("""
<style>
    /* ── Google Font import ── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ── Main background ── */
    .stApp {
        background-color: #f8f6f1;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
    background-color: #1a3a2a !important;
    }

    /* Specifically target text inside the sidebar without affecting main area widgets */
    [data-testid="stSidebarContent"] .stMarkdown, 
    [data-testid="stSidebarContent"] p, 
    [data-testid="stSidebarContent"] h2 {
    color: #e8f5e9 !important;
    }

    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stRadio label {
        color: #b2dfdb !important;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Hero header ── */
    .hero-block {
        background: linear-gradient(135deg, #1a3a2a 0%, #2d6a4f 60%, #52b788 100%);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        margin-bottom: 2rem;
        color: white;
    }
    .hero-block h1 {
        font-size: 2rem;
        font-weight: 800;
        margin: 0 0 0.4rem 0;
        color: white !important;
        line-height: 1.2;
    }
    .hero-block p {
        font-size: 1rem;
        color: #b7e4c7;
        margin: 0;
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a3a2a;
        border-left: 4px solid #52b788;
        padding-left: 0.75rem;
        margin: 1.5rem 0 1rem 0;
    }

    /* ── Metric cards (summary row) ── */
    .metric-row {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        flex: 1;
        min-width: 130px;
        border-top: 4px solid #52b788;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .metric-card.weak   { border-top-color: #e63946; }
    .metric-card.mod    { border-top-color: #f4a261; }
    .metric-card.strong { border-top-color: #52b788; }
    .metric-card .num {
        font-size: 2rem;
        font-weight: 800;
        color: #1a3a2a;
        line-height: 1;
    }
    .metric-card .label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    /* ── Band colour pills ── */
    .band-weak     { background: #fde8ea; color: #c1121f; padding: 2px 10px;
                     border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
    .band-moderate { background: #fff3e0; color: #e65100; padding: 2px 10px;
                     border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
    .band-strong   { background: #e8f5e9; color: #2e7d32; padding: 2px 10px;
                     border-radius: 20px; font-size: 0.78rem; font-weight: 700; }

    /* ── Timetable day headers ── */
    .day-header {
        background: #1a3a2a;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px 8px 0 0;
        font-weight: 700;
        font-size: 0.9rem;
        margin-top: 1.2rem;
    }
    .session-card {
        background: white;
        border-left: 5px solid #52b788;
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem;
        margin-bottom: 4px;
        display: flex;
        gap: 1rem;
        align-items: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .session-card.weak     { border-left-color: #e63946; }
    .session-card.moderate { border-left-color: #f4a261; }
    .session-card.strong   { border-left-color: #52b788; }
    .session-time {
        font-family: 'DM Mono', monospace;
        font-size: 0.82rem;
        color: #6b7280;
        min-width: 110px;
    }
    .session-label {
        font-weight: 600;
        color: #1a3a2a;
        font-size: 0.92rem;
        flex: 1;
    }
    .session-meta {
        font-size: 0.75rem;
        color: #9ca3af;
    }

    /* ── Info/warning boxes ── */
    .info-box {
        background: #e8f5e9;
        border: 1px solid #a5d6a7;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-size: 0.88rem;
        color: #2e7d32;
        margin-bottom: 1rem;
    }
    .warn-box {
        background: #fff8e1;
        border: 1px solid #ffe082;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-size: 0.88rem;
        color: #e65100;
        margin-bottom: 1rem;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #2d6a4f;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.55rem 1.5rem;
        font-weight: 700;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.9rem;
        cursor: pointer;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background-color: #1a3a2a;
    }

    /* ── Score input number fields ── */
    input[type="number"] {
        font-family: 'DM Mono', monospace !important;
    }

    /* ── Hide Streamlit default branding ── */
    #MainMenu, footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 2: SIDEBAR — Student Info + Mode
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📚 Study Planner")
    st.markdown("---")

    student_name = st.text_input(
        "Student Name",
        placeholder="e.g. Amaka Obi",
        help="Enter the student's full name"
    )

    st.markdown("---")
    st.markdown("**Input Mode**")

    # The student chooses whether they want subject-level or topic-level
    mode = st.radio(
        "Choose how detailed your scores are:",
        options=["Subject Level", "Topic Level"],
        help=(
            "Subject Level: One score per subject (e.g. Mathematics: 45%)\n\n"
            "Topic Level: Scores per topic within each subject (e.g. Algebra: 30%, Trigonometry: 58%)"
        )
    )
    mode_key = "subject" if mode == "Subject Level" else "topic"

    st.markdown("---")
    st.markdown("**How to enter scores:**")
    input_method = st.radio(
        "Input method:",
        options=["Manual Entry", "Upload CSV"],
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#81c784'>Built for Nigerian secondary school students.<br>"
        "Phase 1 — Rule-Based Edition</small>",
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────

name_display = student_name.strip() if student_name.strip() else "Student"

st.markdown(f"""
<div class="hero-block">
    <h1>📚 Personalised Study Plan</h1>
    <p>Hello, <strong>{name_display}</strong> — let us find out what to study this week.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 3A: SUBJECTS LIST (used in both modes)
# ─────────────────────────────────────────────

SUBJECTS = [
    "Mathematics",
    "Further Mathematics",
    "English Language",
    "Physics",
    "Chemistry",
    "Biology",
    "Economics",
    "Government",
    "Literature in English",
    "Agricultural Science",
    "Financial Accounting",
    "Commerce",
    "Geography",
    "Christian Religious Studies",
    "Islamic Religious Studies",
    "Civic Education",
    "Technical Drawing",
    "Food and Nutrition",
    "Computer Studies",
]

# ─────────────────────────────────────────────
# SECTION 3B: MANUAL ENTRY — SUBJECT LEVEL
# ─────────────────────────────────────────────

def manual_subject_entry() -> pd.DataFrame:
    """
    Renders a form where the student selects subjects and enters
    one score per subject.

    Returns a DataFrame (or None if the form is not yet submitted).
    """
    st.markdown('<div class="section-header">① Enter Your Subject Scores</div>',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="info-box">Select the subjects you wrote in your exam, '
        'then enter your percentage score (0–100) for each one.</div>',
        unsafe_allow_html=True
    )

    selected_subjects = st.multiselect(
        "Select your subjects:",
        options=SUBJECTS,
        default=["Mathematics", "English Language", "Physics", "Chemistry"],
        help="You can select as many subjects as you sat"
    )

    if not selected_subjects:
        st.warning("Please select at least one subject.")
        return None

    st.markdown("**Enter your score (%) for each subject:**")

    rows = []
    # Lay out score inputs in two columns for space efficiency
    col_pairs = [selected_subjects[i:i+2] for i in range(0, len(selected_subjects), 2)]

    for pair in col_pairs:
        cols = st.columns(2)
        for col, subject in zip(cols, pair):
            with col:
                score = st.number_input(
                    label=subject,
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=1,
                    key=f"subj_{subject}"
                )
                rows.append({
                    "student_name": name_display,
                    "subject": subject,
                    "score_percent": float(score),
                })

    if st.button("🔍 Generate My Study Plan", key="btn_subject_manual"):
        return pd.DataFrame(rows)

    return None


# ─────────────────────────────────────────────
# SECTION 3C: MANUAL ENTRY — TOPIC LEVEL
# ─────────────────────────────────────────────

# Default topics for common subjects
# Teachers/students can add their own via the CSV upload instead
DEFAULT_TOPICS = {
    "Mathematics": [
        "Number Theory", "Algebra", "Quadratic Equations", "Geometry",
        "Trigonometry", "Statistics", "Probability", "Coordinate Geometry",
    ],
    "Further Mathematics": [
        "Calculus", "Matrices", "Complex Numbers", "Vectors",
        "Sequences and Series", "Permutation and Combination",
    ],
    "English Language": [
        "Comprehension", "Summary Writing", "Essay Writing",
        "Lexis and Structure", "Oral English",
    ],
    "Physics": [
        "Mechanics", "Waves", "Electricity", "Optics",
        "Thermodynamics", "Atomic Physics",
    ],
    "Chemistry": [
        "Atomic Structure", "Bonding", "Acids and Bases",
        "Organic Chemistry", "Electrochemistry", "Rates of Reaction",
    ],
    "Biology": [
        "Cell Biology", "Genetics", "Ecology", "Nutrition",
        "Reproduction", "Evolution",
    ],
    "Economics": [
        "Demand and Supply", "Market Structures", "National Income",
        "Money and Banking", "Trade",
    ],
    "Government": [
        "Constitution", "Electoral Systems", "Federalism",
        "Arms of Government", "Political Parties",
    ],
}

def manual_topic_entry() -> pd.DataFrame:
    """
    Renders a form where the student selects subjects, then enters
    a score for each topic within those subjects.

    Returns a DataFrame (or None if not yet submitted).
    """
    st.markdown('<div class="section-header">① Enter Your Topic Scores</div>',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="info-box">Select your subjects, then enter your score for each topic. '
        'Only subjects with pre-loaded topics are shown below. '
        'For other subjects, use CSV upload.</div>',
        unsafe_allow_html=True
    )

    available_subjects = list(DEFAULT_TOPICS.keys())
    selected_subjects = st.multiselect(
        "Select subjects to enter topic scores for:",
        options=available_subjects,
        default=["Mathematics", "Physics"],
    )

    if not selected_subjects:
        st.warning("Please select at least one subject.")
        return None

    rows = []

    for subject in selected_subjects:
        st.markdown(f"**{subject}**")
        topics = DEFAULT_TOPICS.get(subject, [])

        col_pairs = [topics[i:i+2] for i in range(0, len(topics), 2)]
        for pair in col_pairs:
            cols = st.columns(2)
            for col, topic in zip(cols, pair):
                with col:
                    score = st.number_input(
                        label=topic,
                        min_value=0,
                        max_value=100,
                        value=50,
                        step=1,
                        key=f"topic_{subject}_{topic}"
                    )
                    rows.append({
                        "student_name": name_display,
                        "subject": subject,
                        "topic": topic,
                        "score_percent": float(score),
                    })
        st.markdown("---")

    if st.button("🔍 Generate My Study Plan", key="btn_topic_manual"):
        return pd.DataFrame(rows)

    return None


# ─────────────────────────────────────────────
# SECTION 3D: CSV UPLOAD HANDLER
# ─────────────────────────────────────────────

def csv_upload_entry(mode_key: str) -> pd.DataFrame:
    """
    Renders a CSV upload widget and validates the uploaded file.

    Expected columns for subject mode:
        student_name, subject, score_percent

    Expected columns for topic mode:
        student_name, subject, topic, score_percent

    Returns a DataFrame (or None if upload not yet complete).
    """
    st.markdown('<div class="section-header">① Upload Your Score Sheet (CSV)</div>',
                unsafe_allow_html=True)

    # Tell the student exactly what format to use
    if mode_key == "subject":
        st.markdown(
            '<div class="info-box">Your CSV must have these columns: '
            '<strong>student_name, subject, score_percent</strong><br>'
            'Download the sample file from the sidebar to use as a template.</div>',
            unsafe_allow_html=True
        )
        required_cols = {"student_name", "subject", "score_percent"}
    else:
        st.markdown(
            '<div class="info-box">Your CSV must have these columns: '
            '<strong>student_name, subject, topic, score_percent</strong><br>'
            'Download the sample file from the sidebar to use as a template.</div>',
            unsafe_allow_html=True
        )
        required_cols = {"student_name", "subject", "topic", "score_percent"}

    uploaded_file = st.file_uploader(
        "Upload your CSV file:",
        type=["csv"],
        help="Make sure the file is saved as .csv (not .xlsx)"
    )

    if uploaded_file is None:
        return None

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"❌ Could not read the file: {e}")
        return None

    # Strip whitespace from column names (common issue with CSV exports)
    df.columns = df.columns.str.strip()

    # Validate required columns
    missing = required_cols - set(df.columns)
    if missing:
        st.error(f"❌ Missing columns in your CSV: {', '.join(missing)}")
        return None

    # Validate score range
    invalid_scores = df[(df["score_percent"] < 0) | (df["score_percent"] > 100)]
    if not invalid_scores.empty:
        st.warning(
            f"⚠️ {len(invalid_scores)} row(s) have scores outside 0–100. "
            "These rows will be skipped."
        )
        df = df[(df["score_percent"] >= 0) & (df["score_percent"] <= 100)]

    if df.empty:
        st.error("❌ No valid rows found after validation.")
        return None

    st.success(f"✅ File loaded: {len(df)} rows found.")
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("🔍 Generate My Study Plan", key="btn_csv"):
        return df

    return None


# ─────────────────────────────────────────────
# SECTION 4: ANALYSIS DISPLAY
# ─────────────────────────────────────────────

def display_analysis(summary: dict, analyzed_df: pd.DataFrame, mode_key: str):
    """
    Shows the weakness breakdown — summary cards and detailed table.
    """
    st.markdown('<div class="section-header">② Your Performance Analysis</div>',
                unsafe_allow_html=True)

    # Summary metric cards
    avg  = summary["avg_score"]
    weak = summary["weak_count"]
    mod  = summary["moderate_count"]
    strg = summary["strong_count"]

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="num">{avg}%</div>
            <div class="label">Overall Average</div>
        </div>
        <div class="metric-card weak">
            <div class="num">{weak}</div>
            <div class="label">Weak Areas<br><small>(below 50%)</small></div>
        </div>
        <div class="metric-card mod">
            <div class="num">{mod}</div>
            <div class="label">Moderate Areas<br><small>(50–69%)</small></div>
        </div>
        <div class="metric-card strong">
            <div class="num">{strg}</div>
            <div class="label">Strong Areas<br><small>(70% and above)</small></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Weakest and strongest callout
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="warn-box">🔴 Most urgent: '
            f'<strong>{summary["weakest_item"]}</strong> — '
            f'{summary["weakest_score"]}%</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div class="info-box">🟢 Strongest: '
            f'<strong>{summary["strongest_item"]}</strong> — '
            f'{summary["strongest_score"]}%</div>',
            unsafe_allow_html=True
        )

    # Detailed breakdown table
    with st.expander("📋 See full score breakdown", expanded=False):
        if mode_key == "topic":
            display_cols = ["subject", "topic", "score_percent", "band",
                            "subject_avg", "sessions_pw", "mins_per_sess"]
        else:
            display_cols = ["subject", "score_percent", "band",
                            "sessions_pw", "mins_per_sess"]

        # Only show columns that actually exist in the df
        display_cols = [c for c in display_cols if c in analyzed_df.columns]
        st.dataframe(
            analyzed_df[display_cols].rename(columns={
                "subject"      : "Subject",
                "topic"        : "Topic",
                "score_percent": "Score (%)",
                "band"         : "Level",
                "subject_avg"  : "Subject Avg (%)",
                "sessions_pw"  : "Sessions/Week",
                "mins_per_sess": "Mins/Session",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ─────────────────────────────────────────────
# SECTION 5: TIMETABLE DISPLAY
# ─────────────────────────────────────────────

BAND_CLASS = {
    "WEAK": "weak",
    "MODERATE": "moderate",
    "STRONG": "strong",
}

def display_timetable(timetable_df: pd.DataFrame, deferred_df: pd.DataFrame):
    """
    Renders the weekly timetable as day-by-day session cards.
    Also shows the deferred topics list if any exist.
    """
    st.markdown('<div class="section-header">③ Your Weekly Study Timetable</div>',
                unsafe_allow_html=True)

    if timetable_df.empty:
        st.error("❌ Could not generate a timetable. Please check your score input.")
        return

    st.markdown(
        '<div class="info-box">📌 This timetable is built around your Nigerian school schedule. '
        'Weekdays start at 4:00 PM (after school). Saturday is your main study day. '
        'Sunday is light revision only.</div>',
        unsafe_allow_html=True
    )

    # Group by day and render each day's sessions
    days_in_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]

    for day in days_in_order:
        day_sessions = timetable_df[timetable_df["Day"] == day]
        if day_sessions.empty:
            continue

        # Day header
        st.markdown(f'<div class="day-header">📅 {day}</div>', unsafe_allow_html=True)

        # Each session as a card
        for _, row in day_sessions.iterrows():
            band_class = BAND_CLASS.get(row["Priority Level"], "strong")
            duration   = row["Duration (mins)"]
            info       = row["Session Info"]
            label      = row["Subject / Topic"]
            start      = row["Start"]
            end        = row["End"]

            st.markdown(f"""
            <div class="session-card {band_class}">
                <div class="session-time">🕐 {start} – {end}</div>
                <div class="session-label">{label}</div>
                <div class="session-meta">{duration} mins &nbsp;|&nbsp; {info}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Deferred topics (next week) ──
    if deferred_df is not None and not deferred_df.empty:
        st.markdown("---")
        st.markdown(
            f'<div class="warn-box">📋 <strong>{len(deferred_df)} topic(s)</strong> could not '
            f'fit into this week\'s schedule. They are your <strong>Next Week</strong> priority. '
            f'Once you finish this week\'s weak topics, move to these.</div>',
            unsafe_allow_html=True
        )
        with st.expander("📋 See next week's topics", expanded=False):
            show_cols = ["subject", "topic", "score_percent", "band"] \
                        if "topic" in deferred_df.columns \
                        else ["subject", "score_percent", "band"]
            st.dataframe(
                deferred_df[show_cols].rename(columns={
                    "subject"      : "Subject",
                    "topic"        : "Topic",
                    "score_percent": "Score (%)",
                    "band"         : "Level",
                }),
                use_container_width=True,
                hide_index=True,
            )


# ─────────────────────────────────────────────
# SECTION 6: EXPORT TO CSV
# ─────────────────────────────────────────────

def export_timetable(timetable_df: pd.DataFrame, student_name: str):
    """
    Renders a download button that exports the timetable as a CSV file.
    """
    st.markdown('<div class="section-header">④ Download Your Timetable</div>',
                unsafe_allow_html=True)

    # Convert DataFrame to CSV bytes in memory (no temp file needed)
    csv_buffer = io.StringIO()
    timetable_df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    safe_name = student_name.strip().replace(" ", "_") if student_name.strip() else "student"
    filename  = f"{safe_name}_study_timetable.csv"

    st.download_button(
        label="⬇️ Download Timetable as CSV",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        help="Open this file in Excel, Google Sheets, or print it out"
    )

    st.markdown(
        '<div class="info-box">💡 Tip: Open the CSV in Google Sheets or Excel, '
        'then print it to paste in your notebook.</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# SECTION 7: SAMPLE FILE DOWNLOADS (sidebar)
# ─────────────────────────────────────────────
# We also give students sample CSV templates to download from the sidebar

with st.sidebar:
    st.markdown("---")
    st.markdown("**📥 Download Sample CSV Templates**")

    # Subject-level sample
    sample_subject = pd.DataFrame({
        "student_name": ["Your Name"] * 4,
        "subject"     : ["Mathematics", "English Language", "Physics", "Chemistry"],
        "score_percent": [45, 60, 38, 72],
    })
    subj_csv = sample_subject.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Subject-level template",
        data=subj_csv,
        file_name="sample_subject_scores.csv",
        mime="text/csv",
        key="dl_subject_template"
    )

    # Topic-level sample
    sample_topic = pd.DataFrame({
        "student_name": ["Your Name"] * 4,
        "subject"     : ["Mathematics", "Mathematics", "Physics", "Physics"],
        "topic"       : ["Algebra", "Trigonometry", "Waves", "Electricity"],
        "score_percent": [30, 58, 45, 38],
    })
    topic_csv = sample_topic.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Topic-level template",
        data=topic_csv,
        file_name="sample_topic_scores.csv",
        mime="text/csv",
        key="dl_topic_template"
    )


# ─────────────────────────────────────────────
# SECTION 8: MAIN FLOW — WIRE EVERYTHING TOGETHER
# ─────────────────────────────────────────────

def main():
    """
    Orchestrates the full UI flow:
    Input → Analyze → Display → Export

    We use Streamlit's session_state to hold the results after the
    button is clicked, so they persist when the user interacts with
    other widgets (e.g. opening the expander).
    """

    # Initialise session state keys if they don't exist yet
    if "timetable_df" not in st.session_state:
        st.session_state.timetable_df = None
    if "deferred_df" not in st.session_state:
        st.session_state.deferred_df  = None
    if "analyzed_df" not in st.session_state:
        st.session_state.analyzed_df  = None
    if "summary" not in st.session_state:
        st.session_state.summary      = None
    if "active_mode" not in st.session_state:
        st.session_state.active_mode  = None

    # ── Step 1: Collect scores ──
    raw_df = None

    if input_method == "Manual Entry":
        if mode_key == "subject":
            raw_df = manual_subject_entry()
        else:
            raw_df = manual_topic_entry()
    else:
        raw_df = csv_upload_entry(mode_key)

    # ── Step 2: Run analysis + scheduling when data arrives ──
    if raw_df is not None:
        with st.spinner("Analysing your scores and building your timetable..."):
            try:
                if mode_key == "subject":
                    analyzed = analyze_subject_level(raw_df)
                else:
                    analyzed = analyze_topic_level(raw_df)

                summary            = generate_summary(analyzed, mode=mode_key)
                timetable, deferred = generate_timetable(analyzed, mode=mode_key)

                # Store in session state so results persist
                st.session_state.analyzed_df  = analyzed
                st.session_state.summary      = summary
                st.session_state.timetable_df = timetable
                st.session_state.deferred_df  = deferred
                st.session_state.active_mode  = mode_key

            except Exception as e:
                st.error(f"❌ Something went wrong: {e}")
                st.stop()

    # ── Step 3: Display results if they exist ──
    if st.session_state.timetable_df is not None:
        st.markdown("---")
        display_analysis(
            st.session_state.summary,
            st.session_state.analyzed_df,
            st.session_state.active_mode,
        )
        st.markdown("---")
        display_timetable(
            st.session_state.timetable_df,
            st.session_state.deferred_df,
        )
        st.markdown("---")
        export_timetable(
            st.session_state.timetable_df,
            student_name,
        )


# ── Entry point ──
main()
