"""
teacher/dashboard.py
Streamlit UI for the Teacher role: question management, test-case
generation, monitoring, student analysis, feedback, export.
"""

import json
import streamlit as st
import pandas as pd

from teacher import questions as q_repo
from teacher import reports
from testcase.generator import generate_test_cases
from database.db import run_query, run_write

CATEGORIES = [
    "Variables", "Data Types", "Operators", "Conditional Statements", "Loops",
    "Strings", "Lists", "Tuples", "Dictionaries", "Functions", "Recursion",
    "File Handling", "Exception Handling", "Object-Oriented Programming",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
DTYPES = ["int", "float", "string"]


def render(teacher):
    st.sidebar.markdown(f"**Logged in as:** {teacher['name']} (Teacher)")
    page = st.sidebar.radio(
        "Teacher Menu",
        ["Overview", "Manage Questions", "Create Question", "Monitor Submissions",
         "Student Analysis", "Export Results"],
    )

    if page == "Overview":
        _overview()
    elif page == "Manage Questions":
        _manage_questions(teacher)
    elif page == "Create Question":
        _create_question(teacher)
    elif page == "Monitor Submissions":
        _monitor_submissions()
    elif page == "Student Analysis":
        _student_analysis()
    elif page == "Export Results":
        _export_results()


def _overview():
    st.header("📊 Overview")
    stats = reports.overall_statistics()
    c1, c2, c3 = st.columns(3)
    c1.metric("Students", stats["num_students"])
    c2.metric("Submissions", stats["num_submissions"])
    c3.metric("Avg Score", f"{stats['avg_percentage']}%")
    c4, c5, c6 = st.columns(3)
    c4.metric("Highest Score", f"{stats['highest_percentage']}%")
    c5.metric("Lowest Score", f"{stats['lowest_percentage']}%")
    c6.metric("Pass / Fail", f"{stats['num_passed']} / {stats['num_failed']}")


def _create_question(teacher):
    st.header("➕ Create a New Question")

    method = st.radio("Question creation method", ["Manual", "Structured (enables auto test-case generation)"])

    with st.form("create_question_form", clear_on_submit=False):
        title = st.text_input("Question title *")
        description = st.text_area("Problem statement *")
        input_description = st.text_area("Input description")
        output_description = st.text_area("Output description")
        constraints = st.text_area("Constraints")
        sample_input = st.text_area("Sample input")
        sample_output = st.text_area("Sample output")
        category = st.selectbox("Category", CATEGORIES)
        difficulty = st.selectbox("Difficulty", DIFFICULTIES)
        max_marks = st.number_input("Maximum marks", min_value=1, value=10)
        max_attempts = st.number_input("Maximum attempts (0 = unlimited)", min_value=0, value=0)

        input_spec = []
        reference_solution = ""
        if method.startswith("Structured"):
            st.markdown("**Structured input definition** (one row per input the student's program reads, in order)")
            num_inputs = st.number_input("Number of inputs", min_value=1, max_value=10, value=2, key="num_inputs")
            for i in range(int(num_inputs)):
                cols = st.columns([2, 2, 2, 2])
                name = cols[0].text_input(f"Name #{i+1}", value=f"input_{i+1}", key=f"name_{i}")
                dtype = cols[1].selectbox(f"Type #{i+1}", DTYPES, key=f"dtype_{i}")
                min_v = cols[2].text_input(f"Min #{i+1}", value="0", key=f"min_{i}")
                max_v = cols[3].text_input(f"Max #{i+1}", value="100", key=f"max_{i}")
                spec = {"name": name, "type": dtype}
                if dtype in ("int", "float"):
                    try:
                        spec["min"] = float(min_v) if dtype == "float" else int(min_v)
                        spec["max"] = float(max_v) if dtype == "float" else int(max_v)
                    except ValueError:
                        pass
                input_spec.append(spec)

            reference_solution = st.text_area(
                "Reference solution (a CORRECT Python program that reads these inputs "
                "via input() in order, and prints the correct output). Used to "
                "auto-derive expected outputs for generated test cases.",
                height=200,
                placeholder="a = int(input())\nb = int(input())\nprint(a + b)",
            )

        submitted = st.form_submit_button("Save Question")

    if submitted:
        if not title or not description:
            st.error("Title and problem statement are required.")
            return
        qid = q_repo.create_question(
            title=title, description=description, input_description=input_description,
            output_description=output_description, constraints=constraints,
            sample_input=sample_input, sample_output=sample_output, category=category,
            difficulty=difficulty, max_marks=int(max_marks), max_attempts=int(max_attempts),
            input_spec=input_spec if method.startswith("Structured") else None,
            reference_solution=reference_solution or None,
            created_by=teacher["teacher_id"],
        )
        st.success(f"Question '{title}' created (ID {qid}). Now add or generate its 3 test cases below in 'Manage Questions'.")


def _manage_questions(teacher):
    st.header("📋 Manage Questions")
    all_qs = q_repo.get_all_questions()
    if not all_qs:
        st.info("No questions yet. Create one from 'Create Question'.")
        return

    options = {f"[{r['question_id']}] {r['title']}": r["question_id"] for r in all_qs}
    choice = st.selectbox("Select a question", list(options.keys()))
    qid = options[choice]
    question = q_repo.get_question(qid)

    col1, col2, col3 = st.columns(3)
    if col1.button("Activate" if not question["active"] else "Deactivate"):
        q_repo.set_active(qid, not question["active"])
        st.rerun()
    if col2.button("Delete Question", type="secondary"):
        q_repo.delete_question(qid)
        st.warning("Question deleted.")
        st.rerun()

    st.subheader(question["title"])
    st.write(question["description"])
    with st.expander("Edit question details"):
        with st.form(f"edit_q_{qid}"):
            title = st.text_input("Title", value=question["title"])
            description = st.text_area("Problem statement", value=question["description"])
            max_marks = st.number_input("Max marks", min_value=1, value=question["max_marks"])
            max_attempts = st.number_input("Max attempts (0=unlimited)", min_value=0, value=question["max_attempts"] or 0)
            save = st.form_submit_button("Save Changes")
        if save:
            q_repo.update_question(qid, title=title, description=description,
                                    max_marks=int(max_marks), max_attempts=int(max_attempts))
            st.success("Updated.")
            st.rerun()

    st.markdown("---")
    st.subheader("🧪 Test Cases")
    tcs = q_repo.get_test_cases(qid)

    gen_col1, gen_col2 = st.columns([1, 1])
    if gen_col1.button("⚙️ Generate 3 Test Cases"):
        if not question["input_spec_json"]:
            st.error("This question has no structured input spec. Edit it as a "
                      "'Structured' question (recreate it) or add test cases manually below.")
        else:
            generated = generate_test_cases(question["input_spec_json"],
                                             question["reference_solution"],
                                             question["max_marks"])
            for tc in generated:
                tc["is_hidden"] = 1 if tc["test_type"] != "Basic" else 0
            q_repo.save_test_cases(qid, generated, replace=True)
            st.success("Generated 3 test cases. Review them below before locking.")
            st.rerun()

    tcs = q_repo.get_test_cases(qid)
    if not tcs:
        st.info("No test cases yet.")
    for tc in tcs:
        with st.expander(f"Test Case {tc['test_case_id']} — {tc['test_type']} "
                          f"{'🔒' if tc['locked'] else ''} {'🙈 Hidden' if tc['is_hidden'] else '👁 Visible'}"):
            with st.form(f"tc_form_{tc['test_case_id']}"):
                input_data = st.text_area("Input", value=tc["input_data"], key=f"in_{tc['test_case_id']}")
                expected_output = st.text_area("Expected output", value=tc["expected_output"], key=f"out_{tc['test_case_id']}")
                explanation = st.text_input("Explanation", value=tc["explanation"] or "", key=f"exp_{tc['test_case_id']}")
                marks = st.number_input("Marks", min_value=0, value=tc["marks"], key=f"marks_{tc['test_case_id']}")
                is_hidden = st.checkbox("Hidden from students", value=bool(tc["is_hidden"]), key=f"hid_{tc['test_case_id']}")
                c1, c2 = st.columns(2)
                update = c1.form_submit_button("Update")
                delete = c2.form_submit_button("Delete")
            if update:
                q_repo.update_test_case(tc["test_case_id"], input_data=input_data,
                                         expected_output=expected_output, explanation=explanation,
                                         marks=int(marks), is_hidden=int(is_hidden))
                st.success("Test case updated.")
                st.rerun()
            if delete:
                q_repo.delete_test_case(tc["test_case_id"])
                st.warning("Test case deleted.")
                st.rerun()

    if tcs and not all(tc["locked"] for tc in tcs):
        if st.button("🔒 Lock/Finalize Test Cases"):
            q_repo.lock_test_cases(qid)
            st.success("Test cases locked.")
            st.rerun()


def _monitor_submissions():
    st.header("🖥️ Monitor Submissions")
    students = run_query("SELECT student_id, name FROM students ORDER BY name")
    qs = run_query("SELECT question_id, title FROM questions ORDER BY title")
    sections = run_query("SELECT DISTINCT section FROM students WHERE section IS NOT NULL AND section != ''")

    c1, c2, c3, c4 = st.columns(4)
    student_filter = c1.selectbox("Student", ["All"] + [s["name"] for s in students])
    question_filter = c2.selectbox("Question", ["All"] + [q["title"] for q in qs])
    section_filter = c3.selectbox("Section", ["All"] + [s["section"] for s in sections])
    status_filter = c4.selectbox("Status", ["All", "Pass", "Fail"])

    filters = {}
    if student_filter != "All":
        filters["student_id"] = next(s["student_id"] for s in students if s["name"] == student_filter)
    if question_filter != "All":
        filters["question_id"] = next(q["question_id"] for q in qs if q["title"] == question_filter)
    if section_filter != "All":
        filters["section"] = section_filter
    if status_filter != "All":
        filters["status"] = status_filter

    df = reports.submission_table(filters)
    if df.empty:
        st.info("No submissions match the filters yet.")
        return
    st.dataframe(
        df[["submission_id", "student_name", "section", "question_title",
            "attempt_number", "total_score", "max_score", "percentage", "status", "submitted_at"]],
        use_container_width=True,
    )

    st.subheader("Add Feedback to a Submission")
    sub_id = st.number_input("Submission ID", min_value=0, step=1)
    feedback_text = st.text_area("Feedback")
    if st.button("Submit Feedback") and sub_id:
        teacher_id = st.session_state.get("user", {}).get("teacher_id")
        run_write(
            "INSERT INTO feedback (submission_id, teacher_id, feedback_text) VALUES (?, ?, ?)",
            (sub_id, teacher_id, feedback_text),
        )
        st.success("Feedback saved.")


def _student_analysis():
    st.header("🎓 Individual Student Analysis")
    students = run_query("SELECT student_id, name FROM students ORDER BY name")
    if not students:
        st.info("No students registered yet.")
        return
    options = {s["name"]: s["student_id"] for s in students}
    choice = st.selectbox("Select student", list(options.keys()))
    analysis = reports.student_analysis(options[choice])
    if not analysis:
        st.info("No data.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions Attempted", analysis["questions_attempted"])
    c2.metric("Questions Passed", analysis["questions_passed"])
    c3.metric("Avg %", analysis["avg_percentage"])
    c4.metric("Attempts (total)", analysis["num_attempts_total"])

    st.subheader("Per-question test case performance")
    if not analysis["detail_table"].empty:
        st.dataframe(analysis["detail_table"], use_container_width=True)
    else:
        st.info("No submissions yet.")

    st.subheader("Attempt history (score improvement)")
    if not analysis["attempt_history"].empty:
        st.dataframe(analysis["attempt_history"], use_container_width=True)


def _export_results():
    st.header("📤 Export Results")
    df = reports.submission_table()
    if df.empty:
        st.info("Nothing to export yet.")
        return
    st.dataframe(df, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.download_button("Download CSV", data=reports.export_csv(df),
                        file_name="results.csv", mime="text/csv")
    c2.download_button("Download Excel", data=reports.export_excel(df),
                        file_name="results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
