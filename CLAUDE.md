# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mimo Clone is a browser-based Python learning companion with a terminal-like UI. It features guided step-by-step projects across 9 learning levels with 3 difficulty tiers each. The core experience is a guided step-by-step project in bite-sized chunks where users write 1-5 lines of code per step, submit/run to validate, and accumulate working code as they progress.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla HTML/CSS/JS (terminal aesthetic)
- **Database**: SQLite with SQLModel
- **Python Execution**: Docker sandbox (isolated, no network)
- **AI Generation**: Claude API for dynamic projects/hints

## Development Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Run with Docker
docker-compose up --build

# Test API endpoints
curl http://localhost:8000/api/v1/lessons
```

## Architecture

### Backend Structure
- `backend/main.py` - FastAPI entry point, mounts all routers
- `backend/api/` - Route handlers (lessons, projects, execution, generation)
- `backend/services/` - Business logic (execution_service, validation_service, claude_service, progress_service)
- `backend/sandbox/executor.py` - Docker-based isolated Python execution with timeout/memory limits
- `backend/storage/database.py` - SQLite/SQLModel setup and models

### Frontend Structure
- `frontend/index.html` - Single page app with terminal aesthetic
- `frontend/js/app.js` - Main orchestration, state management
- `frontend/js/api.js` - API client wrapper
- `frontend/css/terminal.css` - Dark theme, monospace, green text styling

### Data Flow
1. User selects level/tier → fetches project with steps
2. User writes code for current step → POST to `/api/v1/execute`
3. Sandbox runs code with mocked inputs → returns output
4. Validation service compares output → returns match result + feedback
5. On success, step marked complete, accumulated code updates
6. Code from completed steps becomes read-only accumulated code (grayed out in the UI)

### Code Execution Sandbox
The sandbox (`Dockerfile.sandbox`) runs user Python code in isolation:
- No network access
- Memory and CPU limits
- Timeout enforcement
- `input()` calls are mocked with predefined values from step config

### Validation System
Output matching supports:
- Exact string match (primary)
- Whitespace normalization
- Float precision tolerance
- Element containment check
- Helpful mismatch feedback with graduated messages based on similarity ratio:
  - Close match: "close but not quite"
  - Partial match: "right idea but needs adjustment"
  - No output: "Your code didn't produce any output. Make sure you're using print()."
  - Line count differences are flagged

---

## Project Tier Definitions

### Tier 1 — Basic
- **Scope**: 15-20 lines of code, 4-6 steps
- **Focus**: Most narrow focus on topics introduced by the lesson. Single concept exercises.
- **Purpose**: Basic checkpoint for the lesson/section concepts

### Tier 2 — Intermediate
- **Scope**: 20-30 lines of code, 6-8 steps
- **Focus**: Still narrowly focused on lesson topics but starts combining 2-3 concepts from the lesson together
- **Purpose**: Bridge between basic understanding and full integration

### Tier 3 — Capstone
- **Scope**: 30-70 lines of code, 8-15 steps
- **Focus**: Brings together ALL topics from the current lesson/section, PLUS topics from all previous lessons to reinforce how concepts integrate
- **Purpose**: Comprehensive integration project demonstrating mastery

### Tier Unlocking Rules
- Basic: unlocked if previous level is complete
- Intermediate: unlocked if basic is done
- Capstone: unlocked if intermediate is done

---

## 9 Learning Levels — Detailed Reference

### Level 1: Intro to Python
- **Description**: "Your first steps into Python programming"
- **Concepts**: `print`, `variables`, `input`, `strings`, `integers`, `basic math`
- **Examples**: `print('Hello!')`, `name = 'Alice'`, `name = input('Name: ')`, `age = 25`, `total = 5 + 3`
- **Prerequisite**: None

#### Level 1 Project Ideas
- **Tier 1 (Basic)**: "Personal Greeter" — Ask for name and age, display a personalized greeting. Focuses on print(), input(), and variables. ~8 lines, 5 steps.
- **Tier 2 (Intermediate)**: "Simple Calculator" — Take two numbers as input, perform basic math operations (+, -, *, /), display results. Combines input, variables, int conversion, and string concatenation. ~20-25 lines.
- **Tier 3 (Capstone)**: "Interactive Bio Card" — Build a complete profile card generator that collects name, age, favorite color, hobby, and formats a multi-line styled output. Integrates all Level 1 concepts. ~30-40 lines.

### Level 2: Flow Control
- **Description**: "Make decisions and repeat actions in your code"
- **Concepts**: `if statements`, `else/elif`, `comparison operators`, `logical operators`, `while loops`, `for loops`
- **Examples**: `if age >= 18:`, `==, !=, <, >, <=, >=`, `and, or, not`, `while count < 10:`, `for i in range(5):`
- **Prerequisite**: Level 1

#### Level 2 Project Ideas
- **Tier 1 (Basic)**: "Age Checker" — Ask user age and tell them if they're a child, teen, or adult using if/elif/else. ~15 lines.
- **Tier 2 (Intermediate)**: "Number Guessing Game" — Generate a target number, use a while loop for guesses with higher/lower hints. Combines loops with conditionals. ~25 lines.
- **Tier 3 (Capstone)**: "Quiz Game" — Multi-question quiz with scoring, loops for question iteration, conditionals for answer checking, running score display. Integrates Level 1 I/O with Level 2 control flow. ~40-50 lines.

### Level 3: Lists
- **Description**: "Work with collections of data"
- **Concepts**: `list creation`, `indexing`, `slicing`, `append/insert`, `remove/pop`, `list iteration`
- **Examples**: `fruits = ['apple', 'banana']`, `first = fruits[0]`, `some = fruits[1:3]`, `fruits.append('cherry')`, `for fruit in fruits:`
- **Prerequisite**: Level 2

#### Level 3 Project Ideas
- **Tier 1 (Basic)**: "Shopping List" — Create a list, add items, display the list. Focuses on list creation and append. ~15 lines.
- **Tier 2 (Intermediate)**: "Top Scores Tracker" — Maintain a list of scores, add new ones, sort, show top 3 using slicing. Combines list methods with iteration. ~25 lines.
- **Tier 3 (Capstone)**: "To-Do List Manager" — Full menu-driven app: add, remove, mark complete, view all, view by status. Uses lists, loops, conditionals, and all prior concepts. ~50-60 lines.

### Level 4: Functions
- **Description**: "Create reusable blocks of code"
- **Concepts**: `def keyword`, `parameters`, `return values`, `default arguments`, `scope`
- **Examples**: `def greet():`, `def greet(name):`, `return result`, `def greet(name='World'):`, local vs global
- **Prerequisite**: Level 3

#### Level 4 Project Ideas
- **Tier 1 (Basic)**: "Temperature Converter" — Write a function that converts Celsius to Fahrenheit and vice versa. Focuses on def, parameters, return. ~15 lines.
- **Tier 2 (Intermediate)**: "Tip Calculator" — Functions for calculating tip, splitting bill, formatting currency. Combines multiple functions with default parameters. ~25 lines.
- **Tier 3 (Capstone)**: "Student Grade Book" — Functions to add students, record grades, calculate averages, find highest/lowest, display report. Integrates functions with lists and control flow. ~50-60 lines.

### Level 5: Tuples, Dicts & Sets
- **Description**: "More ways to organize data"
- **Concepts**: `tuples`, `dictionaries`, `dict methods`, `sets`, `set operations`
- **Examples**: `point = (3, 4)`, `person = {'name': 'Alice'}`, `.keys(), .values(), .items()`, `unique = {1, 2, 3}`, `a | b, a & b`
- **Prerequisite**: Level 4

#### Level 5 Project Ideas
- **Tier 1 (Basic)**: "Contact Card" — Create a dictionary for a contact with name, phone, email. Access and display values. ~15 lines.
- **Tier 2 (Intermediate)**: "Word Frequency Counter" — Take a sentence, split into words, count occurrences using a dict, display sorted results. Combines dicts with loops. ~25 lines.
- **Tier 3 (Capstone)**: "Inventory System" — Dict-based inventory with add/remove/search/update operations, set operations to compare inventories, tuple-based transaction log. Integrates all data structures. ~50-65 lines.

### Level 6: Modules & APIs
- **Description**: "Use external code and connect to the world"
- **Concepts**: `import`, `from import`, `random module`, `json module`, `requests basics`
- **Examples**: `import math`, `from math import sqrt`, `random.randint(1, 10)`, `json.loads(data)`, `requests.get(url)`
- **Prerequisite**: Level 5
- **Note**: Since sandbox has no network, API projects should use mocked/simulated responses or focus on json/random modules

#### Level 6 Project Ideas
- **Tier 1 (Basic)**: "Dice Roller" — Use random module to simulate dice rolls, display results. ~15 lines.
- **Tier 2 (Intermediate)**: "JSON Data Parser" — Parse a JSON string containing records, extract specific fields, format output. Combines json module with dict/list operations. ~25 lines.
- **Tier 3 (Capstone)**: "Mock Weather App" — Simulate an API response as JSON, parse it, use random for variability, format a weather report with conditionals. Integrates modules with all prior concepts. ~45-60 lines.

### Level 7: Strings & List Operations
- **Description**: "Advanced text and list manipulation"
- **Concepts**: `string methods`, `f-strings`, `list comprehensions`, `join/split`, `sorting`
- **Examples**: `.upper(), .split(), .strip()`, `f'Hello, {name}!'`, `[x*2 for x in range(5)]`, `', '.join(items)`, `sorted(items, key=len)`
- **Prerequisite**: Level 6

#### Level 7 Project Ideas
- **Tier 1 (Basic)**: "Text Formatter" — Take user text, apply various string methods (upper, lower, title, strip), display results. ~15 lines.
- **Tier 2 (Intermediate)**: "CSV Line Parser" — Split CSV-style strings, clean whitespace, filter/sort entries using comprehensions. ~25 lines.
- **Tier 3 (Capstone)**: "Text Analysis Tool" — Word count, character frequency, sentence detection, longest/shortest words, formatted report using f-strings and comprehensions. Integrates all string/list operations with prior knowledge. ~50-65 lines.

### Level 8: Object-Oriented Programming (OOP)
- **Description**: "Create your own data types with classes"
- **Concepts**: `classes`, `__init__`, `self`, `methods`, `inheritance`
- **Examples**: `class Dog:`, `def __init__(self, name):`, `self.name = name`, `def bark(self):`, `class Puppy(Dog):`
- **Prerequisite**: Level 7

#### Level 8 Project Ideas
- **Tier 1 (Basic)**: "Pet Class" — Define a Pet class with name, species, sound attributes and a speak() method. ~15 lines.
- **Tier 2 (Intermediate)**: "Bank Account" — Account class with deposit/withdraw/balance methods, transaction validation. Combines classes with conditionals. ~25 lines.
- **Tier 3 (Capstone)**: "Library System" — Book class, Library class with add/remove/search/checkout, Member class with inheritance. Full OOP system integrating all concepts. ~55-70 lines.

### Level 9: Working with Private APIs
- **Description**: "Build real integrations with web services"
- **Concepts**: `API authentication`, `REST concepts`, `error handling`, `pagination`, `rate limiting`
- **Examples**: `headers = {'Authorization': key}`, `GET, POST, PUT, DELETE`, `try/except, status codes`, `while next_page:`, `time.sleep(1)`
- **Prerequisite**: Level 8
- **Note**: Uses simulated API responses since sandbox has no network

#### Level 9 Project Ideas
- **Tier 1 (Basic)**: "API Response Handler" — Parse a simulated API response, check status codes, extract data with try/except. ~15-20 lines.
- **Tier 2 (Intermediate)**: "Authenticated Data Fetcher" — Simulate auth headers, handle success/failure responses, parse JSON results with error handling. ~25-30 lines.
- **Tier 3 (Capstone)**: "REST Client Simulator" — Full simulated REST client class with GET/POST/PUT/DELETE methods, auth, error handling, pagination, formatted output. Integrates OOP with API concepts and all prior learning. ~55-70 lines.

---

## Project Step Format

Each step in a project contains:
- **step_num**: Sequential step number
- **instruction**: Clear, beginner-friendly instruction for what to write
- **hint**: Helpful hint if the user is stuck
- **expected_lines**: How many lines the user should write (1-5)
- **expected_output**: Exact expected stdout output (MUST exactly match what running the solution produces, including newlines)
- **mock_inputs**: Simulated input() responses for testing (list of strings in order they'll be consumed)
- **starter_code**: Optional starting code for the step
- **solution**: Reference solution for this step

### Project Design Rules
1. Each step should have the user write **1-5 lines of code** (free response, not fill-in-the-blank)
2. Steps **build on each other logically** — code accumulates across steps
3. Instructions must be **clear and beginner-friendly**
4. Include **mock_inputs** for any `input()` calls
5. **expected_output must exactly match** what running the solution code produces
6. Projects should be **practical and engaging**, not abstract exercises
7. Project descriptions should **explain what we're building, why, and how it uses the key concepts**

### Claude API Project Generation Prompt

When generating projects dynamically, the prompt follows this template:
```
Generate a Python learning project for a Mimo-like learning app.

LEVEL: {level_id} - Concepts: {concepts}
TIER: {tier} ({tier_description})
TARGET: {lines} lines of code, {steps} steps
THEME: {theme} (if provided)
AVOID: {avoid_topics} (if provided)

Requirements:
1. Each step should have the user write 1-5 lines of code
2. Steps should build on each other logically
3. Provide clear, beginner-friendly instructions
4. Include mock_inputs for any input() calls
5. expected_output must exactly match what the code produces
6. Make it practical and engaging, not just abstract exercises

CRITICAL: The expected_output MUST exactly match what running the solution produces, including newlines.
```

The generation endpoint also accepts an optional `theme` (e.g., "space exploration") and `avoid_concepts` list.

---

## Reference Project: "Personal Greeter" (Level 1, Tier 1)

This is the canonical example of a well-structured project:

```json
{
  "id": "level1_basic_hello",
  "level_id": 1,
  "tier": 1,
  "name": "Personal Greeter",
  "description": "Build a simple program that asks for a user's name and age, then creates a personalized greeting. This project teaches you the fundamentals of output, input, and variables.",
  "learning_goals": [
    "Use print() to display messages",
    "Use input() to get user information",
    "Store values in variables",
    "Combine strings and variables"
  ],
  "concepts_used": ["print", "input", "variables", "strings", "string concatenation"],
  "total_lines": 8,
  "difficulty_rating": 1,
  "estimated_minutes": 10,
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
      "instruction": "Now ask for the user's name. Use input() with the prompt 'What is your name? ' and store the result in a variable called 'name'.",
      "hint": "variable = input('prompt text')",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\nWhat is your name? ",
      "mock_inputs": ["Alice"],
      "solution": "name = input('What is your name? ')"
    },
    {
      "step_num": 3,
      "instruction": "Ask for the user's age. Use input() with the prompt 'How old are you? ' and store it in a variable called 'age'.",
      "hint": "Same pattern as name — age = input('prompt')",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\nWhat is your name? How old are you? ",
      "mock_inputs": ["Alice", "25"],
      "solution": "age = input('How old are you? ')"
    },
    {
      "step_num": 4,
      "instruction": "Create the greeting! Print a message that says 'Hello, Alice! You are 25 years old.' using the + operator to combine strings and variables.",
      "hint": "print('Hello, ' + name + '! You are ' + age + ' years old.')",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\nWhat is your name? How old are you? Hello, Alice! You are 25 years old.\n",
      "mock_inputs": ["Alice", "25"],
      "solution": "print('Hello, ' + name + '! You are ' + age + ' years old.')"
    },
    {
      "step_num": 5,
      "instruction": "End with a nice farewell. Print: 'Thanks for using Personal Greeter. Goodbye!'",
      "hint": "One more print() statement",
      "expected_lines": 1,
      "expected_output": "Welcome to the Personal Greeter!\nWhat is your name? How old are you? Hello, Alice! You are 25 years old.\nThanks for using Personal Greeter. Goodbye!\n",
      "mock_inputs": ["Alice", "25"],
      "solution": "print('Thanks for using Personal Greeter. Goodbye!')"
    }
  ],
  "full_solution": "print('Welcome to the Personal Greeter!')\nname = input('What is your name? ')\nage = input('How old are you? ')\nprint('Hello, ' + name + '! You are ' + age + ' years old.')\nprint('Thanks for using Personal Greeter. Goodbye!')"
}
```
