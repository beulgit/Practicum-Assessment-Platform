"""
app.py
Main entry point: run with `streamlit run app.py`

Handles:
  - DB initialization + sample data seeding
  - Login / registration for Teacher and Student roles
  - Routing to the correct dashboard
"""

import streamlit as st

from database.db import init_db
from auth.authentication import (
    login_teacher, login_student, register_teacher, register_student,
)
from utils.helpers import seed_sample_data
from teacher import dashboard as teacher_dashboard
from student import dashboard as student_dashboard

st.set_page_config(page_title="Python Auto-Checker", page_icon="🐍", layout="wide")

init_db()
seed_sample_data()

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None


def logout():
    st.session_state.user = None
    st.session_state.role = None


def login_page():
    st.title("🐍 Python Programming Auto-Verification & Assessment System")
    st.caption("Demo accounts — Teacher: `teacher1` / `teacher123`   |   Student: `student1` / `student123`")

    role = st.radio("I am a:", ["Student", "Teacher"], horizontal=True)
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary"):
            if role == "Teacher":
                user, err = login_teacher(username, password)
            else:
                user, err = login_student(username, password)
            if err:
                st.error(err)
            else:
                st.session_state.user = user
                st.session_state.role = role
                st.rerun()

    with tab_register:
        if role == "Teacher":
            with st.form("register_teacher"):
                r_username = st.text_input("Username")
                r_name = st.text_input("Full name")
                r_email = st.text_input("Email")
                r_password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Register as Teacher")
            if submitted:
                tid, err = register_teacher(r_username, r_name, r_email, r_password)
                st.error(err) if err else st.success("Registered! Please log in.")
        else:
            with st.form("register_student"):
                r_username = st.text_input("Username")
                r_name = st.text_input("Full name")
                r_email = st.text_input("Email")
                r_course = st.text_input("Course")
                r_section = st.text_input("Section")
                r_password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Register as Student")
            if submitted:
                sid, err = register_student(r_username, r_name, r_email, r_course, r_section, r_password)
                st.error(err) if err else st.success("Registered! Please log in.")


def main():
    if st.session_state.user is None:
        login_page()
        return

    st.sidebar.title("🐍 Auto-Checker")
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()
    st.sidebar.markdown("---")

    if st.session_state.role == "Teacher":
        teacher_dashboard.render(st.session_state.user)
    else:
        student_dashboard.render(st.session_state.user)


if __name__ == "__main__":
    main()
