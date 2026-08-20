"""
reports.py
Aggregate statistics, per-student analysis, and export helpers for the
teacher dashboard.
"""

import io
import pandas as pd
from database.db import run_query


def overall_statistics():
    students = run_query("SELECT COUNT(*) AS c FROM students")[0]["c"]
    submissions = run_query("SELECT COUNT(*) AS c FROM submissions")[0]["c"]
    scores = run_query(
        "SELECT total_score, max_score FROM submissions WHERE max_score > 0"
    )
    percentages = [ (r["total_score"] / r["max_score"]) * 100 for r in scores if r["max_score"] ]
    avg_score = round(sum(percentages) / len(percentages), 2) if percentages else 0
    highest = round(max(percentages), 2) if percentages else 0
    lowest = round(min(percentages), 2) if percentages else 0
    passed = sum(1 for p in percentages if p >= 50)
    failed = len(percentages) - passed
    return {
        "num_students": students,
        "num_submissions": submissions,
        "avg_percentage": avg_score,
        "highest_percentage": highest,
        "lowest_percentage": lowest,
        "num_passed": passed,
        "num_failed": failed,
    }


def submission_table(filters: dict = None):
    """
    Returns a pandas DataFrame joining submissions, students, and questions,
    with the most recent attempt per (student, question) marked, honoring
    optional filters: student_id, question_id, section, date_from, date_to,
    status ('Pass'/'Fail'), min_score, max_score.
    """
    query = """
        SELECT s.submission_id, s.student_id, st.name AS student_name, st.section,
               s.question_id, q.title AS question_title, s.submitted_at,
               s.attempt_number, s.total_score, s.max_score
        FROM submissions s
        JOIN students st ON st.student_id = s.student_id
        JOIN questions q ON q.question_id = s.question_id
        ORDER BY s.submitted_at DESC
    """
    rows = run_query(query)
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df

    df["percentage"] = (df["total_score"] / df["max_score"].replace(0, pd.NA) * 100).round(2)
    df["status"] = df["percentage"].apply(lambda p: "Pass" if pd.notna(p) and p >= 50 else "Fail")

    filters = filters or {}
    if filters.get("student_id"):
        df = df[df["student_id"] == filters["student_id"]]
    if filters.get("question_id"):
        df = df[df["question_id"] == filters["question_id"]]
    if filters.get("section"):
        df = df[df["section"] == filters["section"]]
    if filters.get("status") and filters["status"] != "All":
        df = df[df["status"] == filters["status"]]
    if filters.get("date_from"):
        df = df[df["submitted_at"] >= filters["date_from"]]
    if filters.get("date_to"):
        df = df[df["submitted_at"] <= filters["date_to"]]
    if filters.get("min_score") is not None:
        df = df[df["percentage"] >= filters["min_score"]]
    return df


def student_analysis(student_id: int):
    student_rows = run_query("SELECT * FROM students WHERE student_id = ?", (student_id,))
    if not student_rows:
        return None
    student = dict(student_rows[0])

    subs = run_query(
        """SELECT s.*, q.title AS question_title, q.max_marks
           FROM submissions s JOIN questions q ON q.question_id = s.question_id
           WHERE s.student_id = ? ORDER BY s.submitted_at""",
        (student_id,),
    )
    subs = [dict(r) for r in subs]

    per_question = {}
    for s in subs:
        qid = s["question_id"]
        if qid not in per_question or s["submitted_at"] > per_question[qid]["submitted_at"]:
            per_question[qid] = s

    percentages = [
        (s["total_score"] / s["max_score"]) * 100 for s in per_question.values() if s["max_score"]
    ]

    detail_rows = []
    for qid, s in per_question.items():
        results = run_query(
            """SELECT tr.status, tc.test_type
               FROM test_results tr JOIN test_cases tc ON tc.test_case_id = tr.test_case_id
               WHERE tr.submission_id = ? ORDER BY tc.test_case_id""",
            (s["submission_id"],),
        )
        row = {"question": s["question_title"]}
        for i, r in enumerate(results, start=1):
            row[f"TC{i} ({r['test_type']})"] = r["status"]
        row["score"] = f"{s['total_score']}/{s['max_score']}"
        detail_rows.append(row)

    return {
        "student": student,
        "questions_attempted": len(per_question),
        "questions_passed": sum(1 for p in percentages if p >= 50),
        "avg_percentage": round(sum(percentages) / len(percentages), 2) if percentages else 0,
        "highest_percentage": round(max(percentages), 2) if percentages else 0,
        "lowest_percentage": round(min(percentages), 2) if percentages else 0,
        "num_attempts_total": len(subs),
        "detail_table": pd.DataFrame(detail_rows) if detail_rows else pd.DataFrame(),
        "attempt_history": pd.DataFrame(subs)[
            ["question_title", "attempt_number", "total_score", "max_score", "submitted_at"]
        ] if subs else pd.DataFrame(),
    }


def export_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def export_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return buf.getvalue()
