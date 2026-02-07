from difflib import SequenceMatcher


def validate_output(actual: str, expected: str) -> dict:
    """Compare actual output against expected output with flexible matching."""
    if not actual and not expected:
        return {"match": True, "feedback": "Perfect!"}

    if not actual and expected:
        return {
            "match": False,
            "feedback": "Your code didn't produce any output. Make sure you're using print().",
        }

    # Exact match
    if actual == expected:
        return {"match": True, "feedback": "Perfect!"}

    # Normalized match (trailing whitespace, trailing newlines)
    if _normalize(actual) == _normalize(expected):
        return {"match": True, "feedback": "Perfect!"}

    # Float-tolerant match
    if _float_tolerant_match(actual, expected):
        return {"match": True, "feedback": "Perfect!"}

    # No match — generate helpful feedback
    return {"match": False, "feedback": _generate_feedback(actual, expected)}


def _normalize(text: str) -> str:
    """Normalize whitespace: strip trailing spaces per line, normalize line endings."""
    lines = text.replace("\r\n", "\n").split("\n")
    # Strip trailing whitespace from each line, remove trailing empty lines
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _float_tolerant_match(actual: str, expected: str, tolerance: float = 0.001) -> bool:
    """Check if outputs match when allowing float precision differences."""
    actual_lines = _normalize(actual).split("\n")
    expected_lines = _normalize(expected).split("\n")

    if len(actual_lines) != len(expected_lines):
        return False

    for a_line, e_line in zip(actual_lines, expected_lines):
        if a_line == e_line:
            continue
        # Try parsing both as floats
        try:
            a_val = float(a_line.strip())
            e_val = float(e_line.strip())
            if abs(a_val - e_val) > tolerance:
                return False
        except ValueError:
            # Try to find floats within the lines
            if not _lines_float_close(a_line, e_line, tolerance):
                return False

    return True


def _lines_float_close(a: str, e: str, tolerance: float) -> bool:
    """Check if two lines are the same except for float precision."""
    import re

    float_pattern = r"-?\d+\.\d+"
    a_floats = re.findall(float_pattern, a)
    e_floats = re.findall(float_pattern, e)

    if len(a_floats) != len(e_floats):
        return False

    if not a_floats:
        return False

    # Replace floats with placeholders and compare the rest
    a_template = re.sub(float_pattern, "{}", a)
    e_template = re.sub(float_pattern, "{}", e)
    if a_template != e_template:
        return False

    for af, ef in zip(a_floats, e_floats):
        if abs(float(af) - float(ef)) > tolerance:
            return False

    return True


def _generate_feedback(actual: str, expected: str) -> str:
    """Generate helpful feedback based on how close the output is."""
    actual_norm = _normalize(actual)
    expected_norm = _normalize(expected)

    ratio = SequenceMatcher(None, actual_norm, expected_norm).ratio()

    actual_lines = actual_norm.split("\n")
    expected_lines = expected_norm.split("\n")

    if len(actual_lines) != len(expected_lines):
        line_diff = len(actual_lines) - len(expected_lines)
        direction = "more" if line_diff > 0 else "fewer"
        hint = f"Your output has {abs(line_diff)} {direction} line(s) than expected."
    elif ratio > 0.9:
        # Find the first differing line
        for i, (a, e) in enumerate(zip(actual_lines, expected_lines)):
            if a != e:
                hint = f"Almost there! Check line {i + 1} of your output. Expected: '{e}' but got: '{a}'"
                break
        else:
            hint = "Very close! Check for small differences in spacing or punctuation."
    elif ratio > 0.6:
        hint = "Right idea, but the output needs adjustment. Check your print statements carefully."
    elif ratio > 0.3:
        hint = "Your output is partially correct. Re-read the instructions and check each print statement."
    else:
        hint = "The output doesn't match what's expected. Review the instructions and try again."

    return hint
