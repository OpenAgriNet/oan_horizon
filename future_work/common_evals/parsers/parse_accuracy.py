"""
Sample Promptfoo Python assertion parser for accuracy rubric output.

Expected judge text shape:
SCORE: <1-5>
REASON: <text>

Adjust function signature based on your Promptfoo version if needed.
"""

import re


def _extract_score(text: str) -> int:
    m = re.search(r"SCORE:\s*([1-5])", text or "", re.IGNORECASE)
    return int(m.group(1)) if m else 0


def evaluate(output: str, context=None):
    score = _extract_score(output)
    passed = score >= 4
    return {
        "pass": passed,
        "score": (score / 5.0) if score else 0.0,
        "reason": f"Parsed accuracy score={score}",
    }
