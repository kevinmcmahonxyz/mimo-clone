# Mimo Clone — Python Learning Companion

A browser-based companion app for learning Python, inspired by the Mimo mobile app. Features a terminal-aesthetic UI with guided step-by-step projects across 9 learning levels and 3 difficulty tiers.

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
uvicorn backend.main:app --reload --port 8000
# Open http://localhost:8000
```

## Features

- **27 seed projects** across 9 learning levels (Intro to Python → Working with APIs)
- **3 difficulty tiers** per level: Basic, Intermediate, Capstone
- **Step-by-step guided coding** — write 1-5 lines per step, code accumulates
- **Code execution sandbox** — Docker-based isolation with local fallback for development
- **Output validation** — exact match with whitespace normalization and float tolerance
- **Progress tracking** — localStorage + server-side persistence
- **AI project generation** — dynamically create new projects via Claude API (optional)
- **AI hints** — get help when stuck (optional)
- **Terminal aesthetic UI** — dark theme, monospace, green text

## Configuration

Copy `.env.example` to `.env` and optionally add your Claude API key:

```bash
cp .env.example .env
# Edit .env to add MIMO_CLAUDE_API_KEY for AI features
```

AI features (project generation, hints) are optional — the app works fully without them.

## Docker

```bash
# Build and run everything
docker-compose up --build

# Just build the sandbox image
docker build -t mimo-sandbox:latest -f Dockerfile.sandbox .
```

Without Docker, code execution falls back to local `subprocess` (suitable for development).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/lessons` | List all 9 learning levels |
| GET | `/api/v1/lessons/{id}` | Get level details & concepts |
| GET | `/api/v1/projects?level=X&tier=Y` | List projects (filtered) |
| GET | `/api/v1/projects/{id}` | Get project with all steps |
| POST | `/api/v1/execute` | Run code & validate output |
| POST | `/api/v1/generate/project` | Generate project via Claude |
| POST | `/api/v1/generate/hint` | Get AI hint for stuck user |
| GET | `/api/v1/progress` | Get user progress |
| POST | `/api/v1/progress/complete` | Mark step/project done |

## Learning Levels

1. **Intro to Python** — print, variables, input, strings, integers
2. **Flow Control** — if/else, loops, comparisons
3. **Lists** — creation, indexing, slicing, methods
4. **Functions** — def, parameters, return, scope
5. **Tuples, Dicts & Sets** — data structures
6. **Modules & APIs** — import, random, json
7. **Strings & List Operations** — f-strings, comprehensions
8. **OOP** — classes, init, methods, inheritance
9. **Working with APIs** — auth, REST, error handling

## Generating Seed Projects

Seed projects are generated via Claude API. You must have `MIMO_CLAUDE_API_KEY` set in your `.env` file.

```bash
# Generate all missing projects (9 levels × 3 tiers = 27 projects)
python -m scripts.generate_seeds

# Generate only specific level(s)
python -m scripts.generate_seeds --level 1
python -m scripts.generate_seeds --level 2 3

# Generate only specific tier(s): 1=basic, 2=intermediate, 3=capstone
python -m scripts.generate_seeds --tier 1
python -m scripts.generate_seeds --level 1 --tier 2

# Regenerate even if project files already exist
python -m scripts.generate_seeds --force

# Delete all existing and regenerate from scratch
rm data/projects/level*
python -m scripts.generate_seeds
```

The generator validates each project by executing the full solution and running quality checks (output matching, instruction specificity, mock input coverage). Failed projects are automatically repaired before falling back to full regeneration.
