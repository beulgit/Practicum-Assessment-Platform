"""
student/submission.py
Handles the full grading workflow for a student's code submission:
run against each test case, compare output, score, and persist results.
"""

from database.db import run_query, run_write
from execution.runner import run_student_code
from execution.comparator import compare_output


def get_attempt_number(student_id, question_id):
    rows = run_query(
        "SELECT COUNT(*) AS c FROM submissions WHERE student_id = ? AND question_id = ?",
        (student_id, question_id),
    )
    return rows[0]["c"] + 1


def attempts_remaining(student_id, question_id, max_attempts):
    """
    Attempt limits are disabled platform-wide: students always have
    unlimited attempts, regardless of a question's configured max_attempts.
    Attempt history/counters are still tracked (see get_attempt_number)
    for teacher analytics -- this only removes the blocking behavior.
    """
    return None  # None == unlimited, always

def grade_submission(student_id, question_id, code, max_marks):
    """
    Executes `code` against every test case of `question_id`, stores the
    submission + per-test-case results, and returns a rich result dict for
    the UI to render (respecting hidden-test-case output secrecy).
    """
    test_cases = run_query(
        "SELECT * FROM test_cases WHERE question_id = ? ORDER BY test_case_id", (question_id,)
    )

    attempt_number = get_attempt_number(student_id, question_id)

    submission_id = run_write(
        """INSERT INTO submissions (student_id, question_id, code, attempt_number, total_score, max_score)
           VALUES (?, ?, ?, ?, 0, ?)""",
        (student_id, question_id, code, attempt_number, max_marks),
    )

    total_score = 0
    display_results = []

    for tc in test_cases:
        exec_result = run_student_code(code, tc["input_data"])

        if exec_result.timed_out:
            status, marks, error_message = "TIMEOUT", 0, "Program did not finish in time (possible infinite loop)."
        elif exec_result.returncode != 0:
            status, marks = "ERROR", 0
            error_message = f"{exec_result.error_type}: " + (exec_result.stderr.strip().splitlines()[-1]
                                                               if exec_result.stderr.strip() else "Runtime error")
        else:
            is_correct = compare_output(exec_result.stdout, tc["expected_output"])
            status = "PASS" if is_correct else "FAIL"
            marks = tc["marks"] if is_correct else 0
            error_message = None

        total_score += marks

        run_write(
            """INSERT INTO test_results
               (submission_id, test_case_id, actual_output, expected_output, status,
                execution_time, error_message, marks)
               VALUES (?,?,?,?,?,?,?,?)""",
            (submission_id, tc["test_case_id"], exec_result.stdout, tc["expected_output"],
             status, exec_result.execution_time, error_message, marks),
        )

        display_results.append({
            "test_case_id": tc["test_case_id"],
            "test_type": tc["test_type"],
            "is_hidden": bool(tc["is_hidden"]),
            "input_data": tc["input_data"] if not tc["is_hidden"] else None,
            "expected_output": tc["expected_output"] if not tc["is_hidden"] else None,
            "actual_output": exec_result.stdout,
            "status": status,
            "marks": marks,
            "max_marks": tc["marks"],
            "error_message": error_message,
            "execution_time": exec_result.execution_time,
        })

    run_write("UPDATE submissions SET total_score = ? WHERE submission_id = ?", (total_score, submission_id))

    return {
        "submission_id": submission_id,
        "attempt_number": attempt_number,
        "total_score": total_score,
        "max_score": max_marks,
        "percentage": round((total_score / max_marks) * 100, 2) if max_marks else 0,
        "results": display_results,
    }
