"""
utils/helpers.py
Small shared helpers (seeding sample data for a fresh install, etc.)
"""

from database.db import run_query, run_write
from auth.authentication import hash_password
from teacher.questions import create_question, save_test_cases
from testcase.generator import generate_test_cases


SAMPLE_REFERENCE_SOLUTION = """\
initial_balance = float(input())
deposit = float(input())
withdrawal = float(input())
interest_rate = float(input())

account_balance = initial_balance + deposit
account_balance = account_balance - withdrawal
interest_earned = account_balance * interest_rate
final_balance = account_balance + interest_earned

print(f"Initial balance: {initial_balance:.2f}")
print(f"Deposit: {deposit:.2f}")
print(f"Withdrawal: {withdrawal:.2f}")
print(f"Balance after transactions: {account_balance:.2f}")
print(f"Interest earned: {interest_earned:.2f}")
print(f"Final balance: {final_balance:.2f}")
"""


def seed_sample_data():
    """Creates one sample teacher, one sample student, and the Account
    Balance Calculator example question (with auto-generated test cases),
    but only if the database is empty. Safe to call on every app start."""

    if run_query("SELECT teacher_id FROM teachers LIMIT 1"):
        return  # already seeded

    teacher_id = run_write(
        "INSERT INTO teachers (username, name, email, password_hash) VALUES (?,?,?,?)",
        ("teacher1", "Demo Teacher", "teacher1@example.com", hash_password("teacher123")),
    )
    run_write(
        "INSERT INTO students (username, name, email, course, section, password_hash) VALUES (?,?,?,?,?,?)",
        ("student1", "Demo Student", "student1@example.com", "BSc Computer Science", "A",
         hash_password("student123")),
    )

    input_spec = [
        {"name": "initial_balance", "type": "float", "min": 0, "max": 100000},
        {"name": "deposit", "type": "float", "min": 0, "max": 50000},
        {"name": "withdrawal", "type": "float", "min": 0, "max": 50000},
        {"name": "interest_rate", "type": "float", "min": 0, "max": 0.2},
    ]

    qid = create_question(
        title="Account Balance Calculator",
        description=(
            "Write a Python program to read an account's initial balance, a deposit "
            "amount, a withdrawal amount, and an interest rate, then calculate and "
            "display the final balance."
        ),
        input_description="Four values, one per line: initial_balance, deposit, withdrawal, interest_rate (as a decimal, e.g. 0.05 for 5%).",
        output_description="Print each labeled value as shown in the sample output, each rounded to 2 decimal places.",
        constraints="0 <= initial_balance <= 100000; 0 <= deposit, withdrawal <= 50000; 0 <= interest_rate <= 0.2",
        sample_input="1000\n500\n200\n0.05",
        sample_output=(
            "Initial balance: 1000.00\nDeposit: 500.00\nWithdrawal: 200.00\n"
            "Balance after transactions: 1300.00\nInterest earned: 65.00\nFinal balance: 1365.00"
        ),
        category="Operators",
        difficulty="Easy",
        max_marks=10,
        max_attempts=3,
        input_spec=input_spec,
        reference_solution=SAMPLE_REFERENCE_SOLUTION,
        created_by=teacher_id,
    )

    generated = generate_test_cases(
        __import__("json").dumps(input_spec), SAMPLE_REFERENCE_SOLUTION, 10
    )
    for tc in generated:
        tc["is_hidden"] = 1 if tc["test_type"] != "Basic" else 0
    save_test_cases(qid, generated, replace=True)
