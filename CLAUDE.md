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
uvicorn backend.main:app --reload --port 8003

# Reset database (re-seeds from JSON files)
rm -f data/db/mimo.db

# Generate seed projects (requires MIMO_CLAUDE_API_KEY in .env)
python -m scripts.generate_seeds                    # Generate all missing
python -m scripts.generate_seeds --level 1 --tier 2 # Specific level/tier
python -m scripts.generate_seeds --force             # Regenerate existing

# Run with Docker (foreground mode - stops when terminal closes)
docker-compose up --build

# Run in background (persistent)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## Important Gotchas

- `.env` is read at startup only — must kill and restart uvicorn after changes (--reload won't pick it up)
- Old uvicorn processes linger on ports. Always `lsof -ti:PORT | xargs kill` before restarting
- `rm -f data/db/mimo.db` before restart to re-seed from JSON files. Seed functions skip if data already exists.
- The `docker.containers.run()` API does NOT have a `timeout` parameter
- Use `docker.from_env()` + `client.images.get()` to check if sandbox image exists, fall back to local subprocess
- Docker deployment port is configured in `docker-compose.yml` (line 7), not via command-line flags. Current deployment uses port 8003 (host) mapped to 8000 (container).
- `docker-compose up` runs in **foreground mode** — stops when terminal closes. Use `docker-compose up -d` for **persistent/background** operation.
- Database persists across container restarts via volume mount (`./data:/app/data`). Use `docker-compose down -v` to delete volumes and reset database.
- The sandbox container (`sandbox-build`) runs once to build `mimo-sandbox:latest` image, then exits. This is normal behavior — only the `app` container should stay running.
- **Temp files for sandbox execution**: Must be created in `/app/data/tmp` (mounted volume) so Docker daemon can access them. Files in container's `/tmp` are not accessible to Docker for volume mounts.
- **Host path mapping**: Sandbox execution requires `MIMO_HOST_PROJECT_ROOT` env var to convert container paths to host paths for Docker volume mounts.

## Docker Deployment

The application runs via Docker Compose with a two-container architecture:

### Container Architecture
- **app container**: Runs FastAPI backend + serves frontend static files (Python 3.12-slim)
- **sandbox-build container**: Builds `mimo-sandbox:latest` image for isolated Python code execution, then exits

### Port Configuration
- **Deployed configuration**: `8003:8000` (host port 8003 → container port 8000)
- Port mapping is in `docker-compose.yml` line 7
- To change port: edit docker-compose.yml, then rebuild with `docker-compose up --build`

### Deployment Modes

**Foreground mode (development, non-persistent):**
```bash
docker-compose up --build
```
- Runs in current terminal
- Stops when terminal closes or Ctrl+C pressed
- Useful for development with live log output

**Background mode (persistent):**
```bash
docker-compose up -d --build
```
- Runs detached in background
- Survives terminal closure
- View logs with `docker-compose logs -f`

### Container Management
```bash
# View running containers
docker ps

# View logs (follow mode)
docker-compose logs -f

# Stop containers (keeps data)
docker-compose down

# Stop and remove volumes (deletes database)
docker-compose down -v

# Restart containers
docker-compose restart

# Rebuild containers
docker-compose up --build
```

### Persistence
- **Database**: Persists via volume mount (`./data:/app/data`)
- **Docker images**: `mimo-clone-app` and `mimo-sandbox:latest` remain after containers stop
- **For production**: Consider systemd service to auto-start on system boot

## Architecture

### Backend Structure
- `backend/main.py` - FastAPI entry point with lifespan (init_db, seed), static file serving
- `backend/config.py` - Pydantic settings from env vars (prefix: `MIMO_`)
- `backend/quality.py` - Shared quality-checking utilities (VAGUE_PATTERNS, normalize, fix_cumulative_solutions, validate_project_quality)
- `backend/api/` - Route handlers (lessons, projects, execution, generation)
- `backend/services/claude_service.py` - Claude API calls (generate_project, repair_project, generate_hint) with tier-based model routing
- `backend/services/repair_service.py` - Two-phase repair: programmatic auto-fix + Claude-based repair for generated projects
- `backend/services/validation_service.py` - Runtime output validation (exact, normalized, float-tolerant matching)
- `backend/services/execution_service.py` - Code execution orchestration
- `backend/services/progress_service.py` - User progress tracking
- `backend/sandbox/executor.py` - Docker sandbox with local subprocess fallback, input() mocking, random.seed(42) for deterministic output
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
The sandbox (`Dockerfile.sandbox`) runs user Python code in isolation (no network, memory/CPU limits). For development without Docker, execution falls back to local `subprocess`. The `input()` function is mocked by wrapping user code with a shim that reads from a predefined list of values. All code is executed with `random.seed(42)` prepended for deterministic output — this ensures projects using the `random` module produce consistent results during generation, validation, and user execution.

**Critical Implementation Details:**
- Temp files are created in `/app/data/tmp` (mounted volume) so Docker daemon can access them for volume mounts
- Container paths are converted to host paths using `MIMO_HOST_PROJECT_ROOT` environment variable
- Temp files get `chmod 0o644` to ensure sandbox user can read them
- No ENTRYPOINT in `Dockerfile.sandbox` - full command specified in executor

### Project Generation Streaming
The `POST /generate/project` endpoint returns a `StreamingResponse` with `text/event-stream` (SSE). The frontend reads the stream with `fetch()` + `ReadableStream` (not `EventSource`, since it's a POST). Status events are sent at each stage: generating → validating → quality_check → repairing → claude_repair → saving → done/error.

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

**NOTE**: Concepts listed are from validated Mimo curriculum screenshots. Each lesson also includes a detailed `generation_context` field in `data/lessons.json` for project generation guidance.

| Level | Name | Concepts | Prerequisite |
|-------|------|----------|-------------|
| 1 | Intro to Python | print, variables, input, strings, integers, floats, booleans, comparisons, f-strings, type conversion | None |
| 2 | Flow Control | if/elif/else, comparison/logical operators, while/for loops | Level 1 |
| 3 | Lists | creation, indexing, slicing, append/insert, remove/pop, iteration | Level 2 |
| 4 | Functions | def, parameters, return, default arguments, scope | Level 3 |
| 5 | Tuples, Dicts & Sets | tuples, dictionaries, dict methods, sets, set operations | Level 4 |
| 6 | Modules & APIs | import, from import, try/except, random module, json module (no actual network in sandbox) | Level 5 |
| 7 | Strings & List Operations | string methods, f-strings, list comprehensions, join/split, sorting | Level 6 |
| 8 | OOP | classes, __init__, self, methods, inheritance | Level 7 |
| 9 | Working with APIs | API auth, REST concepts, try/except, pagination (simulated) | Level 8 |

**Level 6 Curriculum Detail** (from Mimo):
- Lessons 1-2: Modules (import basics)
- Lessons 3-5: Errors & Exceptions (try/except/raise)
- Lessons 6-7: Communicating with APIs, Introduction to Requests
- Lessons 8-9: Star Wars API project (guided)

---

## Claude API Generation — Known Issues & Mitigations

When generating projects dynamically via Claude API, these issues are handled in the codebase:

1. **Cumulative solutions**: Claude returns the full program in each step's `solution` instead of just the new code. Fixed by `fix_cumulative_solutions()` in `backend/quality.py`.
2. **Broken full_solution**: Claude smashes all code onto one line. Fixed by rebuilding `full_solution` from `"\n".join(step solutions)`.
3. **Apostrophe in single quotes**: `print('Let's go!')` → SyntaxError. Prompt instructs Claude to use double quotes. Auto-repair swaps single→double quotes programmatically.
4. **Vague instructions**: "print a welcome message" without exact text. Prompt now requires exact text for every print/input and exact variable names. Claude repair rewrites vague instructions when detected.
5. **Malformed JSON on long projects**: Capstone projects (8-15 steps) frequently cause unterminated strings. Reducing step count and using `max_tokens=3000` helps. The generate script retries on failure.
6. **Random seed mismatch**: Claude cannot accurately predict `random.seed(42)` output, causing validation failures on projects using random module. Fixed by ALWAYS running `auto_fix_project()` before first quality check to re-execute all code with seed(42) and update `expected_output` values to match actual seeded output.
7. **Validation & repair pipeline**: All generated projects go through quality checks (step execution, output matching, instruction specificity, mock_inputs coverage). Auto-fix runs FIRST (expected_output regeneration, apostrophe fixes, mock_inputs backfill), then validation. On remaining errors, up to 2 Claude repair attempts run for issues needing language understanding (vague instructions, code errors). Only if all repair passes fail does the user see a 422.
8. **Curriculum alignment**: Each lesson now has a `generation_context` field providing detailed guidance on appropriate project types, concept progression, and tier-specific requirements. This ensures generated projects match the actual Mimo curriculum and use concepts students have learned.

### Model Routing

- **Tier 1-2 (basic/intermediate)**: Uses Sonnet (`MIMO_CLAUDE_MODEL`) — faster, cheaper, sufficient for simpler projects
- **Tier 3 (capstone)**: Uses Opus (`MIMO_CLAUDE_MODEL_HEAVY`) — better at complex multi-step projects with 8-15 steps
- **Hints**: Always uses Sonnet — short responses where latency matters
- Both models are configurable via `.env`

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
