"""
analyzer.py — Weakness Detection and Priority Ranking Engine
============================================================
Author: Adewale Samson Adeagbo
Project: Personalised Study Plan Generator

This module is the brain of the tool.
It takes student score data (either subject-level or topic-level),
classifies each entry by performance band, and produces a ranked
priority list that the scheduler will use to build the timetable.

No machine learning is used here — pure rule-based logic.
This keeps it fast, transparent, and easy to explain to students.
"""

import pandas as pd


# ─────────────────────────────────────────────
# SECTION 1: PERFORMANCE BAND THRESHOLDS
# ─────────────────────────────────────────────
# These are the cutoff scores that define how we label performance.
# They are defined as constants so they are easy to change in one place
# if you want to adjust them later (e.g. for a different exam system).

WEAK_THRESHOLD     = 50   # Below this score → WEAK (high priority)
STRONG_THRESHOLD   = 70   # At or above this score → STRONG (low priority)
# Between 50 and 69 (inclusive) → MODERATE (medium priority)


# ─────────────────────────────────────────────
# SECTION 2: STUDY TIME ALLOCATION (minutes)
# ─────────────────────────────────────────────
# How many minutes we assign per study session based on performance band.
# Weak areas get the most time. Strong areas just need light revision.

SESSION_DURATION = {
    "WEAK":     60,   # 1 hour — needs serious attention
    "MODERATE": 45,   # 45 minutes — needs reinforcement
    "STRONG":   20,   # 20 minutes — just keep it fresh
}

# How many sessions per week each band gets.
# Weak areas are spread across more days to ensure repetition.
SESSIONS_PER_WEEK = {
    "WEAK":     3,   # Appears 3 times in the weekly timetable
    "MODERATE": 2,   # Appears 2 times
    "STRONG":   1,   # Appears once (revision only)
}


# ─────────────────────────────────────────────
# SECTION 3: PERFORMANCE BAND CLASSIFIER
# ─────────────────────────────────────────────

def classify_performance(score: float) -> str:
    """
    Takes a score (0–100) and returns its performance band label.

    Parameters:
        score (float): The student's percentage score

    Returns:
        str: One of "WEAK", "MODERATE", or "STRONG"

    Example:
        classify_performance(38)  → "WEAK"
        classify_performance(65)  → "MODERATE"
        classify_performance(80)  → "STRONG"
    """
    if score < WEAK_THRESHOLD:
        return "WEAK"
    elif score < STRONG_THRESHOLD:
        return "MODERATE"
    else:
        return "STRONG"


def get_priority_score(score: float) -> float:
    """
    Converts a percentage score into a priority number.

    Lower actual score → Higher priority number → Appears earlier in timetable.

    We simply invert the score: priority = 100 - score
    So a score of 25% becomes priority 75 (very urgent).
    A score of 80% becomes priority 20 (not urgent).

    Parameters:
        score (float): The student's percentage score

    Returns:
        float: Priority value (higher = more urgent)
    """
    return round(100 - score, 2)


# ─────────────────────────────────────────────
# SECTION 4: SUBJECT-LEVEL ANALYSIS
# ─────────────────────────────────────────────

def analyze_subject_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyses subject-level performance data.

    Expects a DataFrame with these columns:
        - student_name  (str)
        - subject       (str)
        - score_percent (float)

    Returns a new DataFrame with added columns:
        - band          : WEAK / MODERATE / STRONG
        - priority      : Higher number = study this first
        - sessions_pw   : How many sessions per week to schedule
        - mins_per_sess : How many minutes per session

    The returned DataFrame is sorted by priority descending
    (weakest subjects appear at the top).
    """

    # Make a copy so we never modify the original data
    result = df.copy()

    # Apply the classifier to every row's score
    result["band"] = result["score_percent"].apply(classify_performance)

    # Apply the priority scorer to every row's score
    result["priority"] = result["score_percent"].apply(get_priority_score)

    # Look up how many sessions per week this band gets
    result["sessions_pw"] = result["band"].map(SESSIONS_PER_WEEK)

    # Look up how many minutes per session this band gets
    result["mins_per_sess"] = result["band"].map(SESSION_DURATION)

    # Sort: highest priority (weakest) first
    result = result.sort_values("priority", ascending=False).reset_index(drop=True)

    return result


# ─────────────────────────────────────────────
# SECTION 5: TOPIC-LEVEL ANALYSIS
# ─────────────────────────────────────────────

def analyze_topic_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyses topic-level performance data.

    Expects a DataFrame with these columns:
        - student_name  (str)
        - subject       (str)
        - topic         (str)
        - score_percent (float)

    Returns a new DataFrame with added columns:
        - band          : WEAK / MODERATE / STRONG
        - priority      : Higher = more urgent
        - sessions_pw   : Sessions per week for this topic
        - mins_per_sess : Minutes per session for this topic

    Also computes a subject_avg column — the average score across
    all topics within a subject — useful for giving the student
    a subject-level overview even in topic mode.

    Sorted by priority descending (weakest topics first).
    """

    result = df.copy()

    # Classify and prioritise each topic
    result["band"]          = result["score_percent"].apply(classify_performance)
    result["priority"]      = result["score_percent"].apply(get_priority_score)
    result["sessions_pw"]   = result["band"].map(SESSIONS_PER_WEEK)
    result["mins_per_sess"] = result["band"].map(SESSION_DURATION)

    # Compute average score per subject across all its topics
    # This gives a bird's-eye view alongside the detailed topic data
    subject_avg = (
        df.groupby("subject")["score_percent"]
        .mean()
        .round(1)
        .rename("subject_avg")
    )

    # Merge the subject averages back into the topic-level result
    result = result.merge(subject_avg, on="subject", how="left")

    # Sort: highest priority (weakest) topics first
    result = result.sort_values("priority", ascending=False).reset_index(drop=True)

    return result


# ─────────────────────────────────────────────
# SECTION 6: SUMMARY STATISTICS
# ─────────────────────────────────────────────

def generate_summary(analyzed_df: pd.DataFrame, mode: str) -> dict:
    """
    Produces a summary dictionary from the analyzed DataFrame.
    Used to display quick insights at the top of the student's report.

    Parameters:
        analyzed_df (pd.DataFrame): Output from analyze_subject_level or analyze_topic_level
        mode        (str)         : "subject" or "topic"

    Returns:
        dict with keys:
            - total_entries   : How many subjects or topics were analysed
            - weak_count      : Number flagged as WEAK
            - moderate_count  : Number flagged as MODERATE
            - strong_count    : Number flagged as STRONG
            - weakest_item    : The subject or topic with the lowest score
            - weakest_score   : That item's score
            - strongest_item  : The subject or topic with the highest score
            - strongest_score : That item's score
            - avg_score       : Overall average across all entries
    """

    # Identify the label column depending on mode
    item_col = "topic" if mode == "topic" else "subject"

    weak_df     = analyzed_df[analyzed_df["band"] == "WEAK"]
    moderate_df = analyzed_df[analyzed_df["band"] == "MODERATE"]
    strong_df   = analyzed_df[analyzed_df["band"] == "STRONG"]

    # Weakest entry is the first row (already sorted by priority desc)
    weakest_row   = analyzed_df.iloc[0]
    strongest_row = analyzed_df.iloc[-1]

    summary = {
        "total_entries"   : len(analyzed_df),
        "weak_count"      : len(weak_df),
        "moderate_count"  : len(moderate_df),
        "strong_count"    : len(strong_df),
        "weakest_item"    : weakest_row[item_col],
        "weakest_score"   : weakest_row["score_percent"],
        "strongest_item"  : strongest_row[item_col],
        "strongest_score" : strongest_row["score_percent"],
        "avg_score"       : round(analyzed_df["score_percent"].mean(), 1),
        "mode"            : mode,
    }

    return summary


# ─────────────────────────────────────────────
# SECTION 7: QUICK TEST (run this file directly)
# ─────────────────────────────────────────────
# When you run: python analyzer.py
# This section runs automatically so you can verify everything works.
# It will NOT run when analyzer.py is imported by another file.

if __name__ == "__main__":

    print("=" * 60)
    print("ANALYZER TEST — SUBJECT LEVEL")
    print("=" * 60)

    subject_df = pd.read_csv("sample_data/sample_subject_scores.csv")
    analyzed_subjects = analyze_subject_level(subject_df)
    print(analyzed_subjects[["subject", "score_percent", "band", "priority",
                              "sessions_pw", "mins_per_sess"]])

    summary_s = generate_summary(analyzed_subjects, mode="subject")
    print("\n--- SUMMARY ---")
    for key, val in summary_s.items():
        print(f"  {key}: {val}")

    print("\n" + "=" * 60)
    print("ANALYZER TEST — TOPIC LEVEL")
    print("=" * 60)

    topic_df = pd.read_csv("sample_data/sample_topic_scores.csv")
    analyzed_topics = analyze_topic_level(topic_df)
    print(analyzed_topics[["subject", "topic", "score_percent", "band",
                            "priority", "subject_avg"]].to_string())

    summary_t = generate_summary(analyzed_topics, mode="topic")
    print("\n--- SUMMARY ---")
    for key, val in summary_t.items():
        print(f"  {key}: {val}")
