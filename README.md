# Python Programming Auto-Verification & Assessment System

A Streamlit + SQLite web app for teachers to create Python programming
questions, auto-generate test cases, and let students submit code that is
graded automatically. Built as the MVP described in the project brief
(Section 26), covering items 1–13 end to end.

## 1. Install

Requires Python 3.9+.

```bash
cd python_auto_checker
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

## 2. Run

```bash
streamlit run app.py
```

This opens the app in your browser (usually `http://localhost:8501`). The
SQLite database is created automatically at `data/database.db` on first run,
along with one demo teacher and one demo student account:

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Teacher | teacher1  | teacher123  |
| Student | student1  | student123  |

A sample question ("Account Balance Calculator", from the brief) is seeded
automatically with 3 auto-generated test cases so you can try the full
workflow immediately.

## 3. How auto test-case generation works

Random/blind input generation was explicitly avoided. Instead:

1. When creating a question, the teacher can choose **"Structured"** mode and
   describe each input the student's program reads (name, type, valid
   range) — this is the *Structured Question Definition* option from the
   brief.
2. The teacher also pastes a **reference solution**: a correct Python
   program that reads those same inputs and prints the correct output.
3. Clicking **"Generate 3 Test Cases"** on the question (in *Manage
   Questions*) generates a Basic, a Boundary, and an Edge input from the
   spec, then *runs the reference solution itself* (through the same
   sandboxed runner used for grading) to capture the expected output.

This keeps grading fully deterministic — the expected output is never
guessed by an AI, it's produced by executing a program the teacher vouches
for as correct. If a question was created without a structured spec, the
teacher can still add/edit test cases manually.

## 4. Execution safety — read this

Student code is executed with plain Python `subprocess`, not a container.
On POSIX systems (Linux/macOS) we apply:
- a wall-clock timeout (default 6s)
- CPU time and memory `rlimit`s
- a restricted, temporary working directory
- a stripped-down environment (no secrets, minimal `PATH`)
- `python -I` (isolated mode)

**This is best-effort, not a true security boundary.** It is suitable for a
classroom setting where you trust students not to deliberately attack the
grading server, and mainly guards against *accidental* problems (infinite
loops, runaway memory, stray file writes in the sandboxed temp dir).

For a real production/college-server deployment, replace
`execution/runner.py`'s `subprocess.run(...)` call with a `docker run`
invocation using:
```
docker run --rm --network none --read-only --tmpfs /tmp \
  --memory=256m --cpus=0.5 --pids-limit=32 --user nobody \
  python:3.11-slim python -I submission.py < input.txt
```
`execution/sandbox.py` documents these limitations in code comments and is
the single place to change when swapping executors.

## 5. Project structure

```
python_auto_checker/
├── app.py                  # Streamlit entry point, login/routing
├── database/
│   ├── db.py                # SQLite connection + query helpers
│   └── schema.py             # CREATE TABLE statements
├── auth/
│   └── authentication.py      # password hashing, login/register
├── teacher/
│   ├── dashboard.py            # Teacher Streamlit pages
│   ├── questions.py             # Question + test case CRUD
│   └── reports.py                # Stats, filters, CSV/Excel export
├── student/
│   ├── dashboard.py               # Student Streamlit pages
│   ├── submission.py               # Grading workflow
│   └── results.py                   # History / feedback retrieval
├── execution/
│   ├── runner.py                     # Runs student code via subprocess
│   ├── sandbox.py                     # Resource limits, restricted env
│   └── comparator.py                   # Normalized output comparison
├── testcase/
│   └── generator.py                     # Rule-based 3-test-case generation
├── utils/
│   └── helpers.py                        # Sample data seeding
├── data/
│   └── database.db                        # created at runtime
├── requirements.txt
└── README.md
```

## 6. What's implemented (MVP scope)

- Teacher & student login/registration (hashed passwords)
- Teacher: create/edit/delete/activate questions, manual or structured
  question definition
- Auto-generation of 3 test cases (Basic / Boundary / Edge) from a
  structured spec + reference solution, with visible/hidden marking,
  editing, and locking
- Student: browse active questions, paste or upload `.py` code, submit
- Sandboxed execution with timeout + resource limits (see §4)
- Normalized output comparison with numeric tolerance (e.g. `12.5` ==
  `12.50`)
- Friendly error messages for common exceptions (SyntaxError, NameError,
  TypeError, ValueError, IndexError, ZeroDivisionError, etc.) without
  leaking hidden expected outputs
- Automatic scoring per test case and totals, with attempt limits
- Teacher dashboard: overall stats, filterable submission monitor, feedback,
  per-student drill-down showing per-test-case pass/fail across questions,
  CSV/Excel export
- Student dashboard: submission history with teacher feedback

## 7. Suggested manual test scenarios

Use the seeded "Account Balance Calculator" question and try:
1. **Correct program** — should pass all 3 test cases.
2. **Partially correct program** — e.g. forget to add interest, should fail
   the tests where interest_rate matters but may pass simpler ones.
3. **Incorrect program** — wrong formula, should fail.
4. **Syntax error** — e.g. missing colon, should show a friendly
   `SyntaxError` message.
5. **Infinite loop** — e.g. `while True: pass`, should be stopped by the
   timeout and reported as `TIMEOUT`.
6. **Prohibited operation** — e.g. `import os; os.system("ls")` — will run
   inside the restricted temp directory/environment described in §4; note
   the documented limitation that this is not a hard security boundary.

## 8. Extending later

The modular layout (Section 25 of the brief) makes it straightforward to
add: question categories filtering in the student view, richer analytics
charts, containerized execution, email notifications, LMS/SSO integration,
etc. `execution/sandbox.py` and `execution/runner.py` are the two files to
touch for a Docker-based executor upgrade.
