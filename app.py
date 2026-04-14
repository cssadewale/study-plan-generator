import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# SECTION 1: CORE ENGINE (Formerly analyzer.py)
# ─────────────────────────────────────────────

WEAK_THRESHOLD = 50
STRONG_THRESHOLD = 70

SESSION_DURATION = {
    "WEAK": 60,
    "MODERATE": 45,
    "STRONG": 30,
}

SESSIONS_PER_WEEK = {
    "WEAK": 4,
    "MODERATE": 2,
    "STRONG": 1,
}

def analyze_subject_level(df):
    def classify(score):
        if score < WEAK_THRESHOLD: return "WEAK", 1
        if score >= STRONG_THRESHOLD: return "STRONG", 3
        return "MODERATE", 2

    df[["band", "priority"]] = df["score_percent"].apply(lambda x: pd.Series(classify(x)))
    df["sessions_pw"] = df["band"].map(SESSIONS_PER_WEEK)
    df["mins_per_sess"] = df["band"].map(SESSION_DURATION)
    return df.sort_values(by="priority")

def analyze_topic_level(df):
    # Calculate subject averages to identify context
    subj_avgs = df.groupby("subject")["score_percent"].mean().reset_index()
    subj_avgs.columns = ["subject", "subject_avg"]
    df = df.merge(subj_avgs, on="subject")
    
    def classify(score):
        if score < WEAK_THRESHOLD: return "WEAK", 1
        if score >= STRONG_THRESHOLD: return "STRONG", 3
        return "MODERATE", 2

    df[["band", "priority"]] = df["score_percent"].apply(lambda x: pd.Series(classify(x)))
    df["sessions_pw"] = df["band"].map(SESSIONS_PER_WEEK)
    df["mins_per_sess"] = df["band"].map(SESSION_DURATION)
    return df.sort_values(by=["priority", "score_percent"])

def generate_summary(analyzed_df, mode="subject"):
    item_col = "topic" if mode == "topic" else "subject"
    return {
        "weak_count": len(analyzed_df[analyzed_df["band"] == "WEAK"]),
        "moderate_count": len(analyzed_df[analyzed_df["band"] == "MODERATE"]),
        "strong_count": len(analyzed_df[analyzed_df["band"] == "STRONG"]),
        "avg_score": round(analyzed_df["score_percent"].mean(), 1),
        "weakest_item": analyzed_df.iloc[0][item_col],
        "weakest_score": analyzed_df.iloc[0]["score_percent"],
        "strongest_item": analyzed_df.iloc[-1][item_col],
        "strongest_score": analyzed_df.iloc[-1]["score_percent"],
    }

# ─────────────────────────────────────────────
# SECTION 2: SCHEDULER ENGINE (Formerly scheduler.py)
# ─────────────────────────────────────────────

DAILY_CONFIG = {
    "Monday": {"start": "16:00", "available_mins": 180},
    "Tuesday": {"start": "16:00", "available_mins": 180},
    "Wednesday": {"start": "16:00", "available_mins": 150},
    "Thursday": {"start": "16:00", "available_mins": 180},
    "Friday": {"start": "16:00", "available_mins": 120},
    "Saturday": {"start": "08:00", "available_mins": 300},
    "Sunday": {"start": "16:00", "available_mins": 60},
}

def generate_timetable(analyzed_df, mode="subject"):
    # Limit to 8 topics/subjects per week to prevent burnout
    MAX_ITEMS = 8
    deferred_df = pd.DataFrame()
    
    if len(analyzed_df) > MAX_ITEMS:
        deferred_df = analyzed_df.iloc[MAX_ITEMS:]
        working_df = analyzed_df.iloc[:MAX_ITEMS]
    else:
        working_df = analyzed_df.copy()

    # Build flat list of all sessions needed this week
    sessions = []
    item_name_col = "topic" if mode == "topic" else "subject"
    
    for _, row in working_df.iterrows():
        for i in range(int(row["sessions_pw"])):
            sessions.append({
                "label": f"{row['subject']}: {row[item_name_col]}" if mode == "topic" else row['subject'],
                "duration": row["mins_per_sess"],
                "priority": row["band"]
            })

    # Allocation Logic
    timetable = []
    days = list(DAILY_CONFIG.keys())
    day_idx = 0
    
    for sess in sessions:
        # Simple round-robin allocation to ensure even distribution
        current_day = days[day_idx % len(days)]
        
        # Calculate start/end times based on existing sessions that day
        day_sessions = [t for t in timetable if t["Day"] == current_day]
        start_time_str = DAILY_CONFIG[current_day]["start"]
        
        if day_sessions:
            last_end = datetime.strptime(day_sessions[-1]["End"], "%H:%M")
            start_time = last_end + timedelta(minutes=10) # 10min break
        else:
            start_time = datetime.strptime(start_time_str, "%H:%M")
            
        end_time = start_time + timedelta(minutes=sess["duration"])
        
        timetable.append({
            "Day": current_day,
            "Start": start_time.strftime("%H:%M"),
            "End": end_time.strftime("%H:%M"),
            "Subject / Topic": sess["label"],
            "Duration (mins)": sess["duration"],
            "Priority Level": sess["priority"],
            "Session Info": "Revision" if sess["priority"] == "STRONG" else "Deep Study"
        })
        day_idx += 1

    return pd.DataFrame(timetable), deferred_df

# ─────────────────────────────────────────────
# SECTION 3: UI & STYLING (Formerly app.py)
# ─────────────────────────────────────────────

st.set_page_config(page_title="Study Plan Generator", page_icon="📚", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #f8f6f1; }
    
    /* FIX: Ensure widget labels are dark and visible */
    div[data-testid="stWidgetLabel"] p {
        color: #1a3a2a !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }

    section[data-testid="stSidebar"] { background-color: #1a3a2a; color: #e8f5e9; }
    section[data-testid="stSidebar"] * { color: #e8f5e9 !important; }
    
    .hero-block {
        background: linear-gradient(135deg, #1a3a2a 0%, #2d6a4f 60%, #52b788 100%);
        border-radius: 16px; padding: 2rem; margin-bottom: 2rem; color: white;
    }
    .metric-card {
        background: white; border-radius: 12px; padding: 1rem; flex: 1;
        border-top: 4px solid #52b788; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .day-header { background: #1a3a2a; color: white; padding: 0.5rem 1rem; border-radius: 8px 8px 0 0; font-weight: 700; margin-top: 1rem; }
    .session-card { background: white; border-left: 5px solid #52b788; border-radius: 0 8px 8px 0; padding: 0.75rem; margin-bottom: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
    .session-card.weak { border-left-color: #e63946; }
    .session-card.moderate { border-left-color: #f4a261; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Logic ---
with st.sidebar:
    st.markdown("## 📚 Study Planner")
    student_name = st.text_input("Student Name", placeholder="e.g. Amaka Obi")
    mode = st.radio("Input Mode", ["Subject Level", "Topic Level"])
    input_method = st.radio("Input Method", ["Manual Entry", "Upload CSV"])
    mode_key = "subject" if mode == "Subject Level" else "topic"

# --- Main App Logic ---
name_display = student_name.strip() if student_name.strip() else "Student"
st.markdown(f'<div class="hero-block"><h1>📚 Personalised Study Plan</h1><p>Hello, <strong>{name_display}</strong>!</p></div>', unsafe_allow_html=True)

DEFAULT_TOPICS = {
    "Mathematics": ["Number Theory", "Algebra", "Geometry", "Statistics"],
    "Physics": ["Mechanics", "Waves", "Electricity"],
    "English Language": ["Comprehension", "Essay Writing", "Oral English"]
}

if input_method == "Manual Entry":
    st.subheader("① Enter Your Scores")
    if mode_key == "subject":
        subjects = st.multiselect("Select subjects:", ["Mathematics", "English", "Physics", "Chemistry"], default=["Mathematics"])
        rows = [{"student_name": name_display, "subject": s, "score_percent": float(st.number_input(s, 0, 100, 50))} for s in subjects]
    else:
        subj = st.selectbox("Select subject:", list(DEFAULT_TOPICS.keys()))
        rows = [{"student_name": name_display, "subject": subj, "topic": t, "score_percent": float(st.number_input(t, 0, 100, 50))} for t in DEFAULT_TOPICS[subj]]
    
    if st.button("🔍 Generate Study Plan"):
        raw_df = pd.DataFrame(rows)
        analyzed = analyze_topic_level(raw_df) if mode_key == "topic" else analyze_subject_level(raw_df)
        summary = generate_summary(analyzed, mode=mode_key)
        timetable, deferred = generate_timetable(analyzed, mode=mode_key)
        
        st.session_state.update({"timetable": timetable, "summary": summary, "analyzed": analyzed, "deferred": deferred})

# --- Display Results ---
if "timetable" in st.session_state:
    s = st.session_state.summary
    st.markdown(f"### Analysis Overview: Average Score {s['avg_score']}%")
    
    # Timetable Rendering
    for day in DAILY_CONFIG.keys():
        day_data = st.session_state.timetable[st.session_state.timetable["Day"] == day]
        if not day_data.empty:
            st.markdown(f'<div class="day-header">📅 {day}</div>', unsafe_allow_html=True)
            for _, row in day_data.iterrows():
                p_class = row["Priority Level"].lower()
                st.markdown(f'<div class="session-card {p_class}"><strong>{row["Start"]} - {row["End"]}</strong>: {row["Subject / Topic"]} ({row["Duration (mins)"]} mins)</div>', unsafe_allow_html=True)
