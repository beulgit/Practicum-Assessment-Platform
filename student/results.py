"""
student/results.py
Retrieval helpers for a student's own submission history and feedback.
"""

from database.db import run_query


def submission_history(student_id):
    return run_query(
        """SELECT s.submission_id, q.title AS question_title, s.attempt_number,
                  s.total_score, s.max_score, s.submitted_at
           FROM submissions s JOIN questions q ON q.question_id = s.question_id
           WHERE s.student_id = ? ORDER BY s.submitted_at DESC""",
        (student_id,),
    )


def get_feedback_for_submission(submission_id):
    return run_query(
        """SELECT f.feedback_text, f.created_at, t.name AS teacher_name
           FROM feedback f JOIN teachers t ON t.teacher_id = f.teacher_id
           WHERE f.submission_id = ? ORDER BY f.created_at DESC""",
        (submission_id,),
    )


def get_submission_detail(submission_id):
    sub_rows = run_query(
        """SELECT s.*, q.title AS question_title FROM submissions s
           JOIN questions q ON q.question_id = s.question_id
           WHERE s.submission_id = ?""",
        (submission_id,),
    )
    if not sub_rows:
        return None
    submission = dict(sub_rows[0])
    results = run_query(
        """SELECT tr.*, tc.test_type, tc.is_hidden FROM test_results tr
           JOIN test_cases tc ON tc.test_case_id = tr.test_case_id
           WHERE tr.submission_id = ? ORDER BY tr.result_id""",
        (submission_id,),
    )
    submission["results"] = [dict(r) for r in results]
    submission["feedback"] = [dict(f) for f in get_feedback_for_submission(submission_id)]
    return submission
