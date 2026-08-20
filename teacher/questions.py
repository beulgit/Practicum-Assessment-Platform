"""
questions.py
Teacher-side CRUD for questions and their test cases.
"""

import json
from database.db import run_query, run_write


def create_question(title, description, input_description, output_description,
                     constraints, sample_input, sample_output, category,
                     difficulty, max_marks, max_attempts, input_spec, reference_solution,
                     created_by):
    input_spec_json = json.dumps(input_spec) if input_spec else None
    qid = run_write(
        """INSERT INTO questions
           (title, description, input_description, output_description, constraints,
            sample_input, sample_output, category, difficulty, max_marks, max_attempts,
            input_spec_json, reference_solution, created_by, active)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
        (title, description, input_description, output_description, constraints,
         sample_input, sample_output, category, difficulty, max_marks, max_attempts,
         input_spec_json, reference_solution, created_by),
    )
    return qid


def update_question(question_id, **fields):
    if not fields:
        return
    if "input_spec" in fields:
        fields["input_spec_json"] = json.dumps(fields.pop("input_spec"))
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    params = tuple(fields.values()) + (question_id,)
    run_write(f"UPDATE questions SET {set_clause} WHERE question_id = ?", params)


def delete_question(question_id):
    run_write("DELETE FROM test_results WHERE test_case_id IN "
              "(SELECT test_case_id FROM test_cases WHERE question_id = ?)", (question_id,))
    run_write("DELETE FROM test_cases WHERE question_id = ?", (question_id,))
    run_write("DELETE FROM submissions WHERE question_id = ?", (question_id,))
    run_write("DELETE FROM questions WHERE question_id = ?", (question_id,))


def set_active(question_id, active: bool):
    run_write("UPDATE questions SET active = ? WHERE question_id = ?", (1 if active else 0, question_id))


def get_all_questions(teacher_id=None):
    if teacher_id:
        return run_query("SELECT * FROM questions WHERE created_by = ? ORDER BY created_at DESC", (teacher_id,))
    return run_query("SELECT * FROM questions ORDER BY created_at DESC")


def get_active_questions():
    return run_query("SELECT * FROM questions WHERE active = 1 ORDER BY created_at DESC")


def get_question(question_id):
    rows = run_query("SELECT * FROM questions WHERE question_id = ?", (question_id,))
    return dict(rows[0]) if rows else None


# ---------- Test cases ----------

def save_test_cases(question_id, test_cases, replace=True):
    """test_cases: list of dicts with input_data, expected_output, test_type,
    explanation, marks, is_hidden(optional, default 1 for edge/boundary)."""
    if replace:
        run_write("DELETE FROM test_cases WHERE question_id = ?", (question_id,))
    for tc in test_cases:
        run_write(
            """INSERT INTO test_cases
               (question_id, input_data, expected_output, test_type, explanation,
                marks, is_hidden, locked)
               VALUES (?,?,?,?,?,?,?,0)""",
            (question_id, tc["input_data"], tc["expected_output"], tc["test_type"],
             tc.get("explanation", ""), tc.get("marks", 0), tc.get("is_hidden", 0)),
        )


def get_test_cases(question_id):
    return run_query("SELECT * FROM test_cases WHERE question_id = ? ORDER BY test_case_id", (question_id,))


def update_test_case(test_case_id, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    params = tuple(fields.values()) + (test_case_id,)
    run_write(f"UPDATE test_cases SET {set_clause} WHERE test_case_id = ?", params)


def lock_test_cases(question_id):
    run_write("UPDATE test_cases SET locked = 1 WHERE question_id = ?", (question_id,))


def delete_test_case(test_case_id):
    run_write("DELETE FROM test_cases WHERE test_case_id = ?", (test_case_id,))
