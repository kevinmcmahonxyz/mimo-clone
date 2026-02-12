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
    generation_context: str = "",
    theme: str | None = None,
    avoid_concepts: list[str] | None = None,
) -> dict | None:
    """Generate a project using Claude API."""
    if not settings.claude_api_key:
        return None

    spec = TIER_SPECS.get(tier, TIER_SPECS[1])
    avoid_str = ", ".join(avoid_concepts) if avoid_concepts else "none"

    # Add tier-specific concept requirements based on actual Mimo curriculum
    tier_requirements = ""
    if level_id == 1:
        # Level 1 Mimo progression: Variables (01-02) → Booleans/Comparisons (03-04) → Formatting (05) → Bot Part 1 (07) → More Comparisons (08-09) → Types (10) → Input (12) → Bot Part 2 (13)
        if tier == 1:
            # Basic: Core fundamentals (lessons 1-6 focus)
            tier_requirements = "\n- MUST use: Variables, print(), input(), string concatenation OR f-strings, at least one comparison (==, !=, <, >)"
            tier_requirements += "\n- Focus on: Getting user input, storing in variables, displaying output with basic formatting"
            tier_requirements += "\n- Keep it simple: 3-4 core concepts combined"
        elif tier == 2:
            # Intermediate: More concepts combined (lessons 1-11)
            tier_requirements = "\n- MUST use: Variables, print(), input() with type conversion (int(input()) or float(input())), f-strings, multiple comparisons, basic arithmetic"
            tier_requirements += "\n- Should demonstrate: Working with different data types (strings, integers, floats), converting user input"
            tier_requirements += "\n- Focus on: Combining 5-6 concepts in a practical way"
        elif tier == 3:
            # Capstone: Full level (all lessons 1-13)
            tier_requirements = "\n- MUST use: Variables (multiple), print(), input() with conversions, f-strings, comparisons (multiple types), type() function or explicit type awareness, booleans"
            tier_requirements += "\n- Should include: Multiple data types (str, int, float, bool), type conversions, formatted output, user interaction"
            tier_requirements += "\n- Focus on: Building a complete interactive program using all Level 1 concepts"
    elif level_id == 6:
        # Level 6 Mimo progression: Modules (01-02) → Errors/Exceptions (03-05) → APIs/Requests (06-09)
        if tier == 1:
            # Basic: Lessons 01-02 (Modules basics)
            tier_requirements = "\n- MUST use: import statement (import random, import json, or import math), 1-2 module functions"
            tier_requirements += "\n- Focus on: Understanding what modules are and basic import syntax"
        elif tier == 2:
            # Intermediate: Lessons 01-05 (Modules + Error Handling)
            tier_requirements = "\n- MUST use: import AND from...import syntax, try/except for error handling"
            tier_requirements += "\n- Should use: Multiple modules (e.g., random + json), handle potential errors gracefully"
            tier_requirements += "\n- Focus on: Combining modules with error handling for robust programs"
        elif tier == 3:
            # Capstone: All lessons (Modules + Exceptions + simulated API workflow)
            tier_requirements = "\n- MUST use: import and from...import, try/except with specific exception types, simulated API-style data workflow"
            tier_requirements += "\n- Should include: Working with JSON data (parse responses), error handling for missing data/invalid input, multiple modules working together"
            tier_requirements += "\n- Focus on: Complete workflow like fetching/parsing data, handling errors, processing results (simulate API pattern even without actual requests)"
            tier_requirements += "\n- NOTE: Do NOT use requests.get() as network is disabled in sandbox. Simulate API data with JSON strings or dictionaries."

    context_section = f"\n\nLEVEL CONTEXT:\n{generation_context}" if generation_context else ""

    prompt = f"""Generate a Python learning project for a Mimo-like learning app.

LEVEL: {level_id} - Concepts: {', '.join(concepts)}
TIER: {tier} ({spec['desc']})
TARGET: {spec['lines']} lines of code, {spec['steps']} steps
THEME: {theme or 'any practical, engaging topic'}
AVOID: {avoid_str}{tier_requirements}{context_section}

PROJECT QUALITY GUIDELINES:

DO create projects that:
- Solve real-world problems (budgets, trip planning, recipe scaling, game stats, workout tracking)
- Use modules to accomplish something practical, not just demonstrate syntax
- Build toward a complete, working application
- Teach concepts through purposeful application (not contrived examples)
- For tier 2-3: combine multiple module features in meaningful ways

AVOID lazy patterns:
- Simple "random X generator" projects (fortune teller, quote picker, name generator)
- Projects that just call random.choice() once and print the result
- JSON usage that only dumps data without loading it back
- Import statements that don't serve a clear purpose in the app

GOOD tier 3 example (Level 6): "Movie Database Search" - simulates API data with JSON string, uses json.loads() to parse, try/except to handle missing fields, searches through data, uses both import json and from json import loads syntax.

BAD tier 3 example: "Fortune Generator" - just random.choice() from a fortune list. Too simple, no error handling, doesn't match Level 6 curriculum focus.

PROJECT IDEAS by tier (matching Mimo curriculum):

Level 1 (Intro to Python):
- Tier 1: Personal info collector, simple greeter, age calculator (current year - birth year)
- Tier 2: Calculator with multiple operations, temperature/unit converter, simple quiz with score
- Tier 3: Complete profile/bio card generator, interactive story with user choices, budget planner with multiple inputs

Level 6 (Modules & APIs):
- Tier 1 (Modules basics): Simple module usage - dice roller with random, temperature converter with math, simple data formatter with json
- Tier 2 (Modules + Errors): Apps with error handling - calculator that handles division by zero, file reader with try/except, data validator that catches bad input
- Tier 3 (Modules + Exceptions + API patterns): Simulated API workflows - weather data parser (JSON string → dict → process), movie database searcher (parse JSON data, handle missing fields), recipe finder (search JSON data with error handling)

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
13. CRITICAL: All code is executed with "import random; random.seed(42)" prepended automatically. When creating expected_output values for projects using the random module, you MUST calculate what random.seed(42) would produce. For example, with seed(42): random.randint(0, 2) returns 0, random.choice(['a','b','c']) returns 'a'. Simulate this seed to get accurate expected_output.

CRITICAL RULES:
- The "solution" field for each step MUST contain ONLY the new code the user writes in that step — NOT the full accumulated program. For example if step 1 solution is "print('Hello')" and step 2 adds a variable, step 2 solution should be "name = input('Name: ')" NOT "print('Hello')\\nname = input('Name: ')".
- The "expected_output" for each step MUST be the COMPLETE output of running ALL accumulated code up to and including that step (not just the new step's output). Include all newlines exactly as they would appear.
- The "full_solution" at the end should be the complete program (all step solutions concatenated with newlines).
- For modules & APIs projects: Don't just import and call one function. Use multiple functions from each module (e.g., if using random, use both randint AND choice; if using json, use both dumps/dump AND loads/load).
- Projects should feel like building something real, not just syntax exercises.

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
- If there's an output mismatch, update expected_output to match what the accumulated code actually produces. Remember: all code runs with "import random; random.seed(42)" prepended, so random module output is deterministic.
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
