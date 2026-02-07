# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mimo Clone is a browser-based Python learning companion with a terminal-like UI. It features guided step-by-step projects across 9 learning levels with 3 difficulty tiers each. The core experience is a guided step-by-step project in bite-sized chunks where users write 1-5 lines of code per step, submit/run to validate, and accumulate working code as they progress.

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: Vanilla HTML/CSS/JS (terminal aesthetic)
- **Database**: SQLite with SQLModel
- **Python Execution**: Docker sandbox (isolated, no network), local subprocess fallback
- **AI Generation**: Claude API for dynamic projects/hints (optional)

## Development Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run (from project root)
uvicorn backend.main:app --reload --port 8000

# Reset database (re-seeds from JSON files)
rm -f data/db/mimo.db

# Regenerate seed projects (requires MIMO_CLAUDE_API_KEY in .env)
rm data/projects/level*
python -m scripts.generate_seeds

# Run with Docker
docker-compose up --build
```

## Important Gotchas

- `.env` is read at startup only — must kill and restart uvicorn after changes (--reload won't pick it up)
- Old uvicorn processes linger on ports. Always `lsof -ti:PORT | xargs kill` before restarting
- `rm -f data/db/mimo.db` before restart to re-seed from JSON files. Seed functions skip if data already exists.
- The `docker.containers.run()` API does NOT have a `timeout` parameter
- Use `docker.from_env()` + `client.images.get()` to check if sandbox image exists, fall back to local subprocess

## Architecture

### Backend Structure
- `backend/main.py` - FastAPI entry point with lifespan (init_db, seed), static file serving
- `backend/config.py` - Pydantic settings from env vars (prefix: `MIMO_`)
- `backend/api/` - Route handlers (lessons, projects, execution, generation)
- `backend/services/` - Business logic (execution_service, validation_service, claude_service, progress_service)
- `backend/sandbox/executor.py` - Docker sandbox with local subprocess fallback, input() mocking
- `backend/storage/database.py` - SQLModel models (Lesson, Project, Progress), SQLite setup, seed functions

### Frontend Structure
- `frontend/index.html` - Single page app shell
- `frontend/js/app.js` - Main state management, rendering, code execution flow
- `frontend/js/api.js` - API client wrapper
- `frontend/css/terminal.css` - Dark theme, monospace, green text styling

### Data Flow
1. User selects level → all projects for that level shown grouped by tier
2. User selects project → steps loaded, first incomplete step shown
3. User writes code for current step → POST to `/api/v1/execute`
4. Sandbox runs accumulated code + new code with mocked inputs → returns output
5. Validation service compares output → returns match result + feedback
6. On success, step marked complete, code moves to read-only accumulated section
7. After all steps complete, project marked done

### Code Execution
The sandbox (`Dockerfile.sandbox`) runs user Python code in isolation (no network, memory/CPU limits). For development without Docker, execution falls back to local `subprocess`. The `input()` function is mocked by wrapping user code with a shim that reads from a predefined list of values.

### Validation System
Output matching: exact → whitespace-normalized → float-tolerant. Graduated feedback based on similarity ratio. No output gets a specific "use print()" message.

---

## Project Tier Definitions

### Tier 1 — Basic
- **Scope**: 15-20 lines of code, 4-6 steps
- **Focus**: Single concept exercises, narrow focus on lesson topics

### Tier 2 — Intermediate
- **Scope**: 20-30 lines of code, 6-8 steps
- **Focus**: Combines 2-3 concepts from the lesson

### Tier 3 — Capstone
- **Scope**: 30-70 lines of code, 8-15 steps
- **Focus**: Integrates all lesson topics plus concepts from previous levels

### Tier Unlocking Rules
- Basic: unlocked if previous level is complete
- Intermediate: unlocked if basic is done
- Capstone: unlocked if intermediate is done

---

## 9 Learning Levels

| Level | Name | Concepts | Prerequisite |
|-------|------|----------|-------------|
| 1 | Intro to Python | print, variables, input, strings, integers, basic math | None |
| 2 | Flow Control | if/elif/else, comparison/logical operators, while/for loops | Level 1 |
| 3 | Lists | creation, indexing, slicing, append/insert, remove/pop, iteration | Level 2 |
| 4 | Functions | def, parameters, return, default arguments, scope | Level 3 |
| 5 | Tuples, Dicts & Sets | tuples, dictionaries, dict methods, sets, set operations | Level 4 |
| 6 | Modules & APIs | import, from import, random, json (no network in sandbox) | Level 5 |
| 7 | Strings & List Operations | string methods, f-strings, list comprehensions, join/split, sorting | Level 6 |
| 8 | OOP | classes, __init__, self, methods, inheritance | Level 7 |
| 9 | Working with APIs | API auth, REST concepts, try/except, pagination (simulated) | Level 8 |

---

## Claude API Generation — Known Issues & Mitigations

When generating projects dynamically via Claude API, these issues are handled in the codebase:

1. **Cumulative solutions**: Claude returns the full program in each step's `solution` instead of just the new code. Fixed by `_fix_cumulative_solutions()` in `generation.py`.
2. **Broken full_solution**: Claude smashes all code onto one line. Fixed by rebuilding `full_solution` from `"\n".join(step solutions)`.
3. **Apostrophe in single quotes**: `print('Let's go!')` → SyntaxError. Prompt instructs Claude to use double quotes. Validation catches failures.
4. **Vague instructions**: "print a welcome message" without exact text. Prompt now requires exact text for every print/input and exact variable names.
5. **Malformed JSON on long projects**: Capstone projects (8-15 steps) frequently cause unterminated strings. Reducing step count and using `max_tokens=3000` helps. The generate script retries on failure.
6. **Validation gate**: All generated projects are executed before saving. If the full_solution doesn't run cleanly, the project is rejected and the user is prompted to retry.

---

## Project Step Format

Each step in a project contains:
- **step_num**: Sequential step number
- **instruction**: Must specify EXACT text for print/input and EXACT variable names
- **hint**: Helpful hint if stuck
- **expected_lines**: How many lines the user should write (1-5)
- **expected_output**: COMPLETE output of running ALL accumulated code up to this step
- **mock_inputs**: Simulated input() responses (list of strings in consumption order)
- **starter_code**: Optional starting code
- **solution**: ONLY the new code for this step (NOT cumulative)

### Project Design Rules
1. Each step: **1-5 lines of code** (free response, not fill-in-the-blank)
2. Steps **build on each other logically** — code accumulates across steps
3. Instructions must specify **exact text** for every print/input and **exact variable names**
4. Include **mock_inputs** for any `input()` calls
5. **expected_output must exactly match** what running the accumulated solution code produces
6. Use **double quotes** for strings containing apostrophes
7. Projects should be **practical and engaging**, not abstract exercises

---

## Reference Project: "Personal Greeter" (Level 1, Tier 1)

This is the canonical example of a well-structured project:

```json
{
  "id": "level1_basic_hello",
  "level_id": 1,
  "tier": 1,
  "name": "Personal Greeter",
  "description": "Build a simple program that asks for a user's name and age, then creates a personalized greeting.",
  "learning_goals": ["Use print() to display messages", "Use input() to get user information", "Store values in variables", "Combine strings and variables with +"],
  "concepts_used": ["print", "input", "variables", "strings", "string concatenation"],
  "total_lines": 5,
  "steps": [
    {
      "step_num": 1,
      "instruction": "Let's start by welcoming the user! Use print() to display the message: Welcome to the Personal Greeter!",
      "hint": "Use print('text') to display text to the screen",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\n",
      "mock_inputs": [],
      "solution": "print('Welcome to the Personal Greeter!')"
    },
    {
      "step_num": 2,
      "instruction": "Now ask for the user's name. Use input() with the prompt 'What is your name? ' and store the result in a variable called name.",
      "hint": "variable = input('prompt text')",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\nWhat is your name? ",
      "mock_inputs": ["Alice"],
      "solution": "name = input('What is your name? ')"
    }
  ],
  "full_solution": "print('Welcome to the Personal Greeter!')\nname = input('What is your name? ')\n..."
}
```
