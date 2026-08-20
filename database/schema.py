"""
schema.py
Creates all SQLite tables used by the application.
"""

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS teachers (
        teacher_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT UNIQUE NOT NULL,
        name            TEXT NOT NULL,
        email           TEXT,
        password_hash   TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
        student_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT UNIQUE NOT NULL,
        name            TEXT NOT NULL,
        email           TEXT,
        course          TEXT,
        section         TEXT,
        password_hash   TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        question_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title                TEXT NOT NULL,
        description          TEXT NOT NULL,
        input_description    TEXT,
        output_description   TEXT,
        constraints           TEXT,
        sample_input          TEXT,
        sample_output         TEXT,
        category               TEXT,
        difficulty             TEXT DEFAULT 'Easy',
        max_marks               INTEGER DEFAULT 10,
        max_attempts             INTEGER DEFAULT 0,  -- 0 = unlimited
        input_spec_json           TEXT,               -- structured input definition (JSON)
        reference_solution         TEXT,               -- correct python program used to auto-derive expected outputs
        created_by                  INTEGER,
        active                        INTEGER DEFAULT 1,
        created_at                    TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (created_by) REFERENCES teachers(teacher_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS test_cases (
        test_case_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id     INTEGER NOT NULL,
        input_data      TEXT NOT NULL,
        expected_output TEXT NOT NULL,
        test_type       TEXT NOT NULL,      -- Basic / Boundary / Edge
        explanation     TEXT,
        marks           INTEGER DEFAULT 0,
        is_hidden       INTEGER DEFAULT 0,
        locked          INTEGER DEFAULT 0,
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS submissions (
        submission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL,
        question_id     INTEGER NOT NULL,
        code            TEXT NOT NULL,
        submitted_at    TEXT DEFAULT (datetime('now')),
        attempt_number  INTEGER DEFAULT 1,
        total_score     REAL DEFAULT 0,
        max_score       REAL DEFAULT 0,
        FOREIGN KEY (student_id) REFERENCES students(student_id),
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS test_results (
        result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id   INTEGER NOT NULL,
        test_case_id    INTEGER NOT NULL,
        actual_output   TEXT,
        expected_output TEXT,
        status          TEXT,     -- PASS / FAIL / ERROR / TIMEOUT
        execution_time  REAL,
        error_message   TEXT,
        marks           REAL DEFAULT 0,
        FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
        FOREIGN KEY (test_case_id) REFERENCES test_cases(test_case_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id   INTEGER NOT NULL,
        teacher_id      INTEGER NOT NULL,
        feedback_text   TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS question_assignments (
        assignment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id     INTEGER NOT NULL,
        section         TEXT,      -- NULL / '' means assigned to everyone
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    );
    """,
]
