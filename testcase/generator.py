"""
generator.py

Automatic 3-test-case generation.

Design (deliberately NOT "ask an LLM to invent expected outputs" -- see
section 23 of the spec: scoring must be deterministic):

1. The teacher describes each input the program reads, as a structured spec:
     [{"name": "balance", "type": "int"|"float"|"string", "min": ..., "max": ...}, ...]
   (Method 2 / "Structured Question Definition" in the brief.)

2. The teacher also supplies a REFERENCE SOLUTION: a correct Python program
   that reads the same inputs (in the same order/format) and prints the
   correct output. This is required for auto-generation, because it is the
   only reliable, deterministic way to know the correct output for a
   generated input without a human or an untrusted AI guess.

3. Given the spec, we generate 3 valid inputs:
     - Basic:    typical mid-range values
     - Boundary: one value pushed to near the max/min while staying valid
     - Edge:     zero / equal / minimum values (or another documented edge
                 pattern for the type)
   Then we execute the reference solution against each generated input
   (using the same sandboxed runner used for students) to obtain the
   expected output.

4. If no reference solution is supplied, we fall back to leaving the
   expected output blank so the teacher can fill it in manually -- we never
   fabricate a plausible-looking but unverified expected output.

This keeps grading 100% deterministic: whatever the reference solution
prints for a given input IS the expected output, by construction.
"""

import random
import json
from typing import List, Dict, Any, Optional

from execution.runner import run_student_code


def _gen_int(spec: Dict[str, Any], mode: str) -> int:
    lo = int(spec.get("min", 0))
    hi = int(spec.get("max", 100))
    if lo > hi:
        lo, hi = hi, lo
    if mode == "basic":
        mid = (lo + hi) // 2
        # nudge off the exact midpoint a little for variety, staying in range
        jitter = max(1, (hi - lo) // 4)
        val = mid + random.randint(-jitter, jitter)
        return max(lo, min(hi, val))
    if mode == "boundary":
        # near the max, but not exactly (unless range is tiny)
        return hi if hi - lo < 2 else hi - random.randint(0, max(1, (hi - lo) // 10))
    if mode == "edge":
        # zero if in range, else the minimum value
        if lo <= 0 <= hi:
            return 0
        return lo
    return lo


def _gen_float(spec: Dict[str, Any], mode: str) -> float:
    lo = float(spec.get("min", 0.0))
    hi = float(spec.get("max", 1.0))
    if lo > hi:
        lo, hi = hi, lo
    if mode == "basic":
        val = round(random.uniform(lo, hi), 2)
        return val
    if mode == "boundary":
        return round(hi, 2)
    if mode == "edge":
        if lo <= 0.0 <= hi:
            return 0.0
        return round(lo, 2)
    return round(lo, 2)


def _gen_string(spec: Dict[str, Any], mode: str) -> str:
    choices = spec.get("choices")
    if choices:
        if mode == "basic":
            return str(random.choice(choices))
        if mode == "boundary":
            return str(choices[-1])
        return str(choices[0])
    samples = {
        "basic": "hello",
        "boundary": "x" * int(spec.get("max_length", 20)),
        "edge": "",
    }
    return samples.get(mode, "sample")


def _generate_value(spec: Dict[str, Any], mode: str):
    dtype = spec.get("type", "int").lower()
    if dtype == "int":
        return _gen_int(spec, mode)
    if dtype == "float":
        return _gen_float(spec, mode)
    return _gen_string(spec, mode)


def build_input_text(input_spec: List[Dict[str, Any]], mode: str) -> str:
    """Builds the stdin text (one value per line, matching the input_spec order)."""
    lines = [str(_generate_value(spec, mode)) for spec in input_spec]
    return "\n".join(lines) + "\n"


TEST_TYPES = [
    ("basic", "Basic", "Typical, valid mid-range input."),
    ("boundary", "Boundary", "Input pushed toward the maximum allowed value(s)."),
    ("edge", "Edge", "Zero / minimum / equal-value edge condition."),
]


def generate_test_cases(input_spec_json: str, reference_solution: Optional[str],
                         max_marks: int) -> List[Dict[str, Any]]:
    """
    Returns a list of 3 dicts: {input_data, expected_output, test_type,
    explanation, marks, generated_ok, generation_note}
    """
    try:
        input_spec = json.loads(input_spec_json) if input_spec_json else []
    except (json.JSONDecodeError, TypeError):
        input_spec = []

    if not input_spec:
        return [{
            "input_data": "",
            "expected_output": "",
            "test_type": label,
            "explanation": desc + " (No structured input spec provided -- "
                                  "fill in input/expected output manually.)",
            "marks": 0,
            "generated_ok": False,
        } for mode, label, desc in TEST_TYPES]

    # Distribute marks: edge case weighted slightly higher, matches spec example (3/3/4)
    n = len(TEST_TYPES)
    base = max_marks // n
    marks_list = [base] * n
    marks_list[-1] += max_marks - base * n  # remainder goes to the last (edge) case

    results = []
    for (mode, label, desc), marks in zip(TEST_TYPES, marks_list):
        input_text = build_input_text(input_spec, mode)
        expected_output = ""
        generated_ok = False
        note = None
        if reference_solution:
            exec_result = run_student_code(reference_solution, input_text)
            if exec_result.timed_out:
                note = "Reference solution timed out while generating this case."
            elif exec_result.returncode != 0:
                note = f"Reference solution raised an error: {exec_result.error_type}"
            else:
                expected_output = exec_result.stdout
                generated_ok = True
        else:
            note = "No reference solution supplied -- expected output left blank."

        results.append({
            "input_data": input_text,
            "expected_output": expected_output,
            "test_type": label,
            "explanation": desc,
            "marks": marks,
            "generated_ok": generated_ok,
            "generation_note": note,
        })

    return results
