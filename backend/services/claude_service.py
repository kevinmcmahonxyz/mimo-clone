import json
from anthropic import Anthropic

from backend.config import settings


TIER_SPECS = {
    1: {"lines": "15-20", "steps": "4-6", "desc": "basic, focused on single concepts"},
    2: {"lines": "20-30", "steps": "6-8", "desc": "intermediate, combining 2-3 concepts"},
    3: {"lines": "30-70", "steps": "8-15", "desc": "capstone, integrating multiple levels"},
}


def _model_for_tier(tier: int) -> str:
    """Route to Opus for capstone (tier 3), Sonnet for basic/intermediate."""
    if tier >= 3 and settings.claude_model_heavy:
        return settings.claude_model_heavy
    return settings.claude_model


def generate_project(
    level_id: int,
    tier: int,
    concepts: list[str],
    theme: str | None = None,
    avoid_concepts: list[str] | None = None,
) -> dict | None:
    """Generate a project using Claude API."""
    if not settings.claude_api_key:
        return None

    spec = TIER_SPECS.get(tier, TIER_SPECS[1])
    avoid_str = ", ".join(avoid_concepts) if avoid_concepts else "none"

    prompt = f"""Generate a Python learning project for a Mimo-like learning app.

LEVEL: {level_id} - Concepts: {', '.join(concepts)}
TIER: {tier} ({spec['desc']})
TARGET: {spec['lines']} lines of code, {spec['steps']} steps
THEME: {theme or 'any practical, engaging topic'}
AVOID: {avoid_str}

Requirements:
1. Each step should have the user write 1-5 lines of code (free response)
2. Steps should build on each other logically — code accumulates across steps
3. Provide clear, beginner-friendly instructions
4. Include mock_inputs for any input() calls
5. expected_output must exactly match what the code produces when run
6. Make it practical and engaging, not just abstract exercises
7. The project description should explain what we're building, why, and how it uses key concepts
8. IMPORTANT: Instructions MUST specify the EXACT text for every print() and input() call. Never say "print a welcome message" — say "Print: Welcome to the Pizza Builder!" or "Use print() to display 'Welcome to the Pizza Builder!'". The user cannot guess what text you expect.
9. IMPORTANT: Instructions MUST specify the EXACT variable names to use. Never say "store it in a variable" — say "store it in a variable called name" or "save the result to a variable called total".
10. Avoid using apostrophes or single quotes INSIDE single-quoted Python strings. Use double quotes for strings containing apostrophes, e.g. print("Let's go!") not print('Let's go!').
11. Each step's mock_inputs must contain exactly the right number of entries for ALL input() calls in the accumulated code up to and including that step. For example, if step 1 has one input() and step 2 adds another, step 2's mock_inputs must have 2 entries (one for step 1's input, one for step 2's).
12. Never use vague words like "appropriate", "suitable", or "relevant" in instructions — always specify the exact value, text, or variable name.

CRITICAL RULES:
- The "solution" field for each step MUST contain ONLY the new code the user writes in that step — NOT the full accumulated program. For example if step 1 solution is "print('Hello')" and step 2 adds a variable, step 2 solution should be "name = input('Name: ')" NOT "print('Hello')\\nname = input('Name: ')".
- The "expected_output" for each step MUST be the COMPLETE output of running ALL accumulated code up to and including that step (not just the new step's output). Include all newlines exactly as they would appear.
- The "full_solution" at the end should be the complete program (all step solutions concatenated with newlines).

EXAMPLE of a well-structured step sequence (from a Level 1 Personal Greeter project):
Step 1:
  instruction: "Let's start by welcoming the user! Use print() to display the message: Welcome to the Personal Greeter!"
  solution: "print('Welcome to the Personal Greeter!')"
  expected_output: "Welcome to the Personal Greeter!\\n"
  mock_inputs: []
Step 2:
  instruction: "Now ask for the user's name. Use input() with the prompt 'What is your name? ' and store the result in a variable called name."
  solution: "name = input('What is your name? ')"
  expected_output: "Welcome to the Personal Greeter!\\nWhat is your name? "
  mock_inputs: ["Alice"]
Step 3:
  instruction: "Ask for the user's age. Use input() with the prompt 'How old are you? ' and store it in a variable called age."
  solution: "age = input('How old are you? ')"
  expected_output: "Welcome to the Personal Greeter!\\nWhat is your name? How old are you? "
  mock_inputs: ["Alice", "25"]

Notice: each step's solution is ONLY the new code, expected_output is cumulative, and mock_inputs grows as more input() calls accumulate.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "id": "level{level_id}_tier{tier}_<shortname>",
  "level_id": {level_id},
  "tier": {tier},
  "name": "<project name>",
  "description": "<what we're building and why>",
  "learning_goals": ["<goal1>", "<goal2>", ...],
  "concepts_used": ["<concept1>", ...],
  "total_lines": <number>,
  "difficulty_rating": <1-5>,
  "estimated_minutes": <number>,
  "steps": [
    {{
      "step_num": 1,
      "instruction": "<clear instruction>",
      "hint": "<helpful hint>",
      "expected_lines": <1-5>,
      "expected_output": "<COMPLETE output of all code up to this step>",
      "mock_inputs": ["<input1>", ...],
      "starter_code": "",
      "solution": "<ONLY the new code for this step, NOT cumulative>"
    }}
  ],
  "full_solution": "<complete working code>"
}}"""

    model = _model_for_tier(tier)
    client = Anthropic(api_key=settings.claude_api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]

    return json.loads(text)


def repair_project(project_data: dict, errors: list[str]) -> dict | None:
    """Ask Claude to fix specific quality issues in a generated project.

    Returns the repaired project dict, or None if the repair failed.
    """
    if not settings.claude_api_key:
        return None

    project_json = json.dumps(project_data, indent=2)
    error_list = "\n".join(f"- {e}" for e in errors)

    prompt = f"""You previously generated a Python learning project, but it has the following quality issues:

{error_list}

Here is the full project JSON:

{project_json}

Please fix ONLY the issues listed above. Keep the same project ID, name, structure, and number of steps. Do not add or remove steps.

Rules for fixes:
- If an instruction is "vague", rewrite it to specify the EXACT text for print()/input() and EXACT variable names. Look at the step's solution to determine what the instruction should say.
- If there's an apostrophe in a single-quoted string, change the outer quotes to double quotes.
- If mock_inputs count is wrong, provide the correct number of mock inputs for all input() calls in the accumulated code up to that step.
- If there's an output mismatch, update expected_output to match what the accumulated code actually produces.
- If there's an execution failure, fix the code in the solution field.
- Each step's "solution" must contain ONLY the new code for that step (not cumulative).
- The "expected_output" for each step must be the COMPLETE output of running ALL accumulated code up to that step.

Return ONLY the corrected JSON (no markdown fences, no explanation)."""

    tier = project_data.get("tier", 1)
    model = _model_for_tier(tier)
    client = Anthropic(api_key=settings.claude_api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]

        return json.loads(text)
    except Exception:
        return None


def generate_hint(
    instruction: str,
    code: str,
    error: str | None = None,
) -> str:
    """Generate a helpful hint for a stuck user."""
    if not settings.claude_api_key:
        return "Try re-reading the instruction carefully and check your syntax."

    context = f"Instruction: {instruction}\nUser's code:\n{code}"
    if error:
        context += f"\nError: {error}"

    prompt = f"""A Python beginner is stuck on this step. Give a short, helpful hint (2-3 sentences max). Don't give away the answer, but guide them in the right direction.

{context}

Hint:"""

    client = Anthropic(api_key=settings.claude_api_key)
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
