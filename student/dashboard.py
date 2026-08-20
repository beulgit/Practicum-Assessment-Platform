"""
student/dashboard.py
Streamlit UI for the Student role: view questions, submit code, see
results, and review submission history.
"""

import streamlit as st

from teacher.questions import get_active_questions, get_question, get_test_cases
from student.submission import grade_submission, attempts_remaining
from student.results import submission_history, get_submission_detail


def render(student):
    st.sidebar.markdown(f"**Logged in as:** {student['name']} (Student)")
    page = st.sidebar.radio("Student Menu", ["Solve a Question", "My Submission History"])

    if page == "Solve a Question":
        _solve_question(student)
    else:
        _history(student)


def _solve_question(student):
    st.header("📝 Programming Questions")
    questions = get_active_questions()
    if not questions:
        st.info("No questions have been published yet. Check back later.")
        return

    options = {f"[{q['question_id']}] {q['title']} ({q['difficulty']})": q["question_id"] for q in questions}
    choice = st.selectbox("Choose a question", list(options.keys()))
    qid = options[choice]
    question = get_question(qid)

    st.subheader(question["title"])
    st.caption(f"Category: {question.get('category') or '—'} | Difficulty: {question['difficulty']} | "
               f"Max marks: {question['max_marks']}")
    st.markdown(question["description"])

    with st.expander("ℹ️ Input / Output / Constraints"):
        st.markdown(f"**Input:** {question['input_description'] or '—'}")
        st.markdown(f"**Output:** {question['output_description'] or '—'}")
        st.markdown(f"**Constraints:** {question['constraints'] or '—'}")
        if question["sample_input"]:
            st.code(question["sample_input"], language="text")
        if question["sample_output"]:
            st.code(question["sample_output"], language="text")

    visible_tcs = [tc for tc in get_test_cases(qid) if not tc["is_hidden"]]
    if visible_tcs:
        with st.expander("👁 Visible test case(s)"):
            for tc in visible_tcs:
                st.markdown(f"**Input:**")
                st.code(tc["input_data"], language="text")

    remaining = attempts_remaining(student["student_id"], qid, question["max_attempts"])
    if remaining is not None:
        st.info(f"Attempts remaining: {remaining} of {question['max_attempts']}")
        if remaining <= 0:
            st.error("You have used all allowed attempts for this question.")
            return

    st.markdown("---")
    st.subheader("Your Solution")
    tab1, tab2 = st.tabs(["Paste Code", "Upload .py File"])
    code = ""
    with tab1:
        code_pasted = st.text_area("Python code", height=280, key=f"paste_{qid}")
        if code_pasted:
            code = code_pasted
    with tab2:
        uploaded = st.file_uploader("Upload a .py file", type=["py"], key=f"upload_{qid}")
        if uploaded is not None:
            code = uploaded.read().decode("utf-8")
            st.code(code, language="python")

    if st.button("▶ Run & Submit", type="primary", disabled=not code):
        if not get_test_cases(qid):
            st.error("This question has no test cases configured yet. Contact your teacher.")
            return
        with st.spinner("Running your program against the test cases..."):
            result = grade_submission(student["student_id"], qid, code, question["max_marks"])
        _render_result(result)


def _render_result(result):
    st.markdown("### Test Results")
    for r in result["results"]:
        icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️", "TIMEOUT": "⏱️"}.get(r["status"], "•")
        with st.container(border=True):
            st.markdown(f"**{icon} Test Case {r['test_case_id']} ({r['test_type']}) — {r['status']} "
                        f"— {r['marks']}/{r['max_marks']} marks**")
            if r["is_hidden"]:
                st.caption("Hidden test case — input/expected output not shown.")
            else:
                st.text(f"Input:\n{r['input_data']}")
                st.text(f"Expected Output:\n{r['expected_output']}")
            st.text(f"Your Output:\n{r['actual_output']}")
            if r["error_message"]:
                st.error(r["error_message"])
            st.caption(f"Execution time: {r['execution_time']}s")

    st.markdown("---")
    st.metric("Final Score", f"{result['total_score']}/{result['max_score']}",
               delta=f"{result['percentage']}%")


def _history(student):
    st.header("📜 My Submission History")
    subs = submission_history(student["student_id"])
    if not subs:
        st.info("You haven't submitted anything yet.")
        return

    for s in subs:
        pct = round((s["total_score"] / s["max_score"]) * 100, 1) if s["max_score"] else 0
        status = "Pass" if pct >= 50 else "Fail"
        with st.expander(f"{s['question_title']} — Attempt {s['attempt_number']} — "
                          f"{s['total_score']}/{s['max_score']} ({status}) — {s['submitted_at']}"):
            detail = get_submission_detail(s["submission_id"])
            for r in detail["results"]:
                icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️", "TIMEOUT": "⏱️"}.get(r["status"], "•")
                st.write(f"{icon} {r['test_type']} — {r['status']} — {r['marks']} marks")
            if detail["feedback"]:
                st.markdown("**Teacher feedback:**")
                for f in detail["feedback"]:
                    st.info(f"{f['feedback_text']}  \n*— {f['teacher_name']}, {f['created_at']}*")
