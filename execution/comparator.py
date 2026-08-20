"""
comparator.py
Normalized comparison between a student's actual output and the expected
output, with optional floating-point tolerance for numeric lines.
"""

import re

FLOAT_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def _normalize(text: str) -> list:
    """Strip trailing/leading whitespace per line, collapse internal runs of
    spaces/tabs to a single space, drop trailing blank lines."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    norm = []
    for line in lines:
        line = line.strip()
        line = re.sub(r"[ \t]+", " ", line)
        norm.append(line)
    while norm and norm[-1] == "":
        norm.pop()
    return norm


def compare_output(actual: str, expected: str, float_tolerance: float = 0.01,
                    case_sensitive: bool = True) -> bool:
    """
    Returns True if actual output matches expected output under normalization:
      - leading/trailing whitespace ignored
      - internal repeated whitespace collapsed
      - line-ending differences ignored
      - trailing blank lines ignored
      - numeric tokens compared with a tolerance (handles '12.5' vs '12.50')
    """
    a_lines = _normalize(actual)
    e_lines = _normalize(expected)

    if not case_sensitive:
        a_lines = [l.lower() for l in a_lines]
        e_lines = [l.lower() for l in e_lines]

    if len(a_lines) != len(e_lines):
        return False

    for a_line, e_line in zip(a_lines, e_lines):
        if a_line == e_line:
            continue
        a_tokens = a_line.split(" ")
        e_tokens = e_line.split(" ")
        if len(a_tokens) != len(e_tokens):
            return False
        for a_tok, e_tok in zip(a_tokens, e_tokens):
            if a_tok == e_tok:
                continue
            if FLOAT_RE.match(a_tok) and FLOAT_RE.match(e_tok):
                try:
                    if abs(float(a_tok) - float(e_tok)) <= float_tolerance:
                        continue
                except ValueError:
                    return False
            return False
    return True
