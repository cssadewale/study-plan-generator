"""
scheduler.py — Weekly Timetable Generation Engine
==================================================
Author: Adewale Samson Adeagbo
Project: Personalised Study Plan Generator

This module takes the priority-ranked output from analyzer.py
and builds a realistic 7-day weekly study timetable.

Key design decisions explained:
- Weekdays (Mon–Fri): study window is 4:00 PM – 9:00 PM (after school)
- Saturday: study window is 8:00 AM – 1:00 PM (free morning)
- Sunday: rest day — only very light revision if at all
- No subject appears twice on the same day (prevents burnout)
- Weakest subjects are scheduled earlier in the week (Monday/Tuesday)
  so the student tackles hard things while energy is highest
- A 10-minute break is inserted between every two sessions

All of this is rule-based. No randomness. The same input always
produces the same timetable, which is important for trust.
"""

import pandas as pd
from analyzer import SESSION_DURATION, SESSIONS_PER_WEEK


# ─────────────────────────────────────────────
# SECTION 1: DAILY TIME BLOCK CONFIGURATION
# ─────────────────────────────────────────────

# Each day has a start time (24hr format as string) and a total
# available study duration in minutes.

DAILY_CONFIG = {
    "Monday":    {"start": "16:00", "available_mins": 180},  # 4pm–7pm
    "Tuesday":   {"start": "16:00", "available_mins": 180},
    "Wednesday": {"start": "16:00", "available_mins": 150},  # shorter — midweek fatigue
    "Thursday":  {"start": "16:00", "available_mins": 180},
    "Friday":    {"start": "16:30", "available_mins": 150},  # later start — end of school week
    "Saturday":  {"start": "08:00", "available_mins": 300},  # 8am–1pm — longest study day
    "Sunday":    {"start": "16:00", "available_mins":  90},  # light revision — 2 short slots max
}

BREAK_DURATION_MINS = 10   # Break inserted between sessions
DAY_ORDER = list(DAILY_CONFIG.keys())   # Preserves Mon→Sun order


# ─────────────────────────────────────────────
# SECTION 2: TIME ARITHMETIC HELPERS
# ─────────────────────────────────────────────

def time_to_minutes(time_str: str) -> int:
    """
    Converts a "HH:MM" string to total minutes since midnight.

    Example:
        time_to_minutes("16:30")  → 990
        time_to_minutes("08:00")  → 480
    """
    hours, mins = map(int, time_str.split(":"))
    return hours * 60 + mins


def minutes_to_time(total_mins: int) -> str:
    """
    Converts total minutes since midnight back to "HH:MM" string.

    Example:
        minutes_to_time(990)  → "16:30"
        minutes_to_time(480)  → "08:00"
    """
    hours   = total_mins // 60
    minutes = total_mins % 60
    return f"{hours:02d}:{minutes:02d}"


# ─────────────────────────────────────────────
# SECTION 3: SESSION LIST BUILDER
# ─────────────────────────────────────────────

def build_session_list(analyzed_df: pd.DataFrame, mode: str) -> list:
    """
    Converts the analyzed DataFrame into a flat list of study sessions.

    Each session is a dictionary describing one study block:
        {
          "label"    : "Mathematics — Algebra"  (what to study)
          "band"     : "WEAK"
          "duration" : 60                        (minutes)
          "priority" : 70.0                      (higher = schedule earlier)
        }

    The session list will contain multiple entries for weak items
    (because they get 3 sessions per week) and fewer for strong items.

    Parameters:
        analyzed_df (pd.DataFrame): Output from analyzer.py
        mode        (str)         : "subject" or "topic"

    Returns:
        list of session dicts, sorted by priority descending
    """

    sessions = []

    for _, row in analyzed_df.iterrows():

        # Build a human-readable label for this session
        if mode == "topic":
            label = f"{row['subject']} — {row['topic']}"
        else:
            label = row["subject"]

        band          = row["band"]
        duration_mins = SESSION_DURATION[band]
        priority      = row["priority"]
        repeat_count  = SESSIONS_PER_WEEK[band]

        # Create one session entry per scheduled repetition this week
        # e.g. WEAK item → 3 sessions in the week
        for session_num in range(repeat_count):
            sessions.append({
                "label"    : label,
                "band"     : band,
                "duration" : duration_mins,
                "priority" : priority,
                # We track session_num so we can label them e.g. "Session 1 of 3"
                "session_num"  : session_num + 1,
                "total_sessions": repeat_count,
            })

    # Sort all sessions: highest priority first (weakest items go first)
    sessions.sort(key=lambda x: x["priority"], reverse=True)

    return sessions


# ─────────────────────────────────────────────
# SECTION 4: TIMETABLE SLOT ALLOCATOR
# ─────────────────────────────────────────────

def allocate_sessions_to_days(sessions: list) -> list:
    """
    Places study sessions into day slots, respecting:
      - Available minutes per day
      - No duplicate subjects on the same day
      - Breaks between sessions

    Strategy:
      - Go through sessions in priority order (weakest first)
      - For each session, find the earliest day that:
          (a) has enough time remaining
          (b) does not already contain this subject/topic

    This is a greedy algorithm — simple, fast, and predictable.

    Parameters:
        sessions (list): Output from build_session_list()

    Returns:
        list of timetable entry dicts, each containing:
            - day, start_time, end_time, label, band, duration
    """

    # Track remaining minutes and used labels per day
    # We copy DAILY_CONFIG so we do not modify the original
    day_remaining = {
        day: config["available_mins"]
        for day, config in DAILY_CONFIG.items()
    }
    day_current_time = {
        day: time_to_minutes(config["start"])
        for day, config in DAILY_CONFIG.items()
    }
    # Tracks which subject labels are already scheduled on each day
    day_labels_used = {day: set() for day in DAY_ORDER}

    timetable = []   # This is what we will return

    # Track sessions we could not fit (overflow)
    unscheduled = []

    for session in sessions:
        placed = False
        label    = session["label"]
        duration = session["duration"]
        # Total slot needed = study time + break after
        slot_needed = duration + BREAK_DURATION_MINS

        # Extract the base subject name (everything before " — " if topic mode)
        # We use base subject to avoid scheduling two topics of the same subject
        # on the same day, which would be overwhelming
        base_subject = label.split(" — ")[0]

        # Try each day in Mon → Sun order
        for day in DAY_ORDER:
            time_fits    = day_remaining[day] >= slot_needed
            subject_free = base_subject not in day_labels_used[day]

            if time_fits and subject_free:
                # Schedule this session here
                start_mins = day_current_time[day]
                end_mins   = start_mins + duration

                timetable.append({
                    "day"        : day,
                    "start_time" : minutes_to_time(start_mins),
                    "end_time"   : minutes_to_time(end_mins),
                    "label"      : label,
                    "band"       : session["band"],
                    "duration"   : duration,
                    "session_info": f"Session {session['session_num']} of {session['total_sessions']}",
                })

                # Update day state
                day_current_time[day] += slot_needed   # Advance clock (study + break)
                day_remaining[day]    -= slot_needed   # Reduce available time
                day_labels_used[day].add(base_subject) # Mark subject as used today

                placed = True
                break  # Move to the next session

        if not placed:
            unscheduled.append(session)

    # Warn if any sessions could not be scheduled
    if unscheduled:
        print(f"\n⚠️  WARNING: {len(unscheduled)} session(s) could not be scheduled "
              f"(week is full or no suitable day found).")
        for s in unscheduled:
            print(f"   → {s['label']} ({s['band']}, {s['duration']} mins)")

    return timetable


# ─────────────────────────────────────────────
# SECTION 5: TIMETABLE FORMATTER
# ─────────────────────────────────────────────

def format_timetable(timetable: list) -> pd.DataFrame:
    """
    Converts the raw timetable list into a clean, sorted DataFrame
    ready for display or export.

    Columns returned:
        Day | Start | End | Subject/Topic | Band | Duration (mins) | Session Info

    Parameters:
        timetable (list): Output from allocate_sessions_to_days()

    Returns:
        pd.DataFrame sorted by day (Mon→Sun) then by start time
    """

    if not timetable:
        return pd.DataFrame()

    df = pd.DataFrame(timetable)

    # Sort by day order (Mon first) then by start time within each day
    df["day_order"] = df["day"].map({day: i for i, day in enumerate(DAY_ORDER)})
    df = df.sort_values(["day_order", "start_time"]).drop(columns=["day_order"])

    # Rename columns to be student-friendly
    df = df.rename(columns={
        "day"         : "Day",
        "start_time"  : "Start",
        "end_time"    : "End",
        "label"       : "Subject / Topic",
        "band"        : "Priority Level",
        "duration"    : "Duration (mins)",
        "session_info": "Session Info",
    })

    return df.reset_index(drop=True)


# ─────────────────────────────────────────────
# SECTION 6: MASTER FUNCTION
# ─────────────────────────────────────────────

def generate_timetable(analyzed_df: pd.DataFrame, mode: str) -> tuple:
    """
    Master function — runs the full pipeline from analyzed data to timetable.

    Call this from app.py or from the test block below.

    WHY WE CAP TOPICS IN TOPIC MODE:
    A student may have 30+ topics across all subjects. If we try to schedule
    3 sessions for every weak topic, we would need 70+ slots — but a week
    only has room for about 17 sessions. Instead, we take the TOP 8 highest-
    priority topics for this week's plan. The rest are shown as "Next Week"
    items, giving the student a rolling study plan.

    Parameters:
        analyzed_df (pd.DataFrame): Output from analyzer.analyze_subject_level()
                                    or analyzer.analyze_topic_level()
        mode        (str)         : "subject" or "topic"

    Returns:
        tuple: (
            pd.DataFrame  — the formatted weekly timetable,
            pd.DataFrame  — topics/subjects deferred to next week (may be empty)
        )
    """
    MAX_TOPICS_THIS_WEEK = 8   # Realistic cap for topic mode; subjects mode handles itself

    deferred_df = pd.DataFrame()   # Will hold anything pushed to next week

    if mode == "topic":
        # Take only the top N topics for this week (already sorted by priority)
        this_week_df = analyzed_df.head(MAX_TOPICS_THIS_WEEK).copy()
        if len(analyzed_df) > MAX_TOPICS_THIS_WEEK:
            deferred_df = analyzed_df.iloc[MAX_TOPICS_THIS_WEEK:].copy()
    else:
        # Subject mode: all subjects fit in a week (typically 8–10 subjects)
        this_week_df = analyzed_df.copy()

    sessions  = build_session_list(this_week_df, mode)
    timetable = allocate_sessions_to_days(sessions)
    formatted = format_timetable(timetable)

    return formatted, deferred_df


# ─────────────────────────────────────────────
# SECTION 7: QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd
    from analyzer import analyze_subject_level, analyze_topic_level

    print("=" * 70)
    print("SCHEDULER TEST — SUBJECT LEVEL")
    print("=" * 70)

    subject_df        = pd.read_csv("sample_data/sample_subject_scores.csv")
    analyzed_subjects = analyze_subject_level(subject_df)
    timetable_s, deferred_s = generate_timetable(analyzed_subjects, mode="subject")

    print(timetable_s.to_string(index=False))
    if not deferred_s.empty:
        print(f"\n📋 {len(deferred_s)} subject(s) deferred to next week.")

    print("\n" + "=" * 70)
    print("SCHEDULER TEST — TOPIC LEVEL")
    print("=" * 70)

    topic_df       = pd.read_csv("sample_data/sample_topic_scores.csv")
    analyzed_topics = analyze_topic_level(topic_df)
    timetable_t, deferred_t = generate_timetable(analyzed_topics, mode="topic")

    print(timetable_t.to_string(index=False))

    if not deferred_t.empty:
        print(f"\n📋 {len(deferred_t)} topic(s) deferred to next week (shown below):")
        print(deferred_t[["subject", "topic", "score_percent", "band"]].to_string(index=False))
