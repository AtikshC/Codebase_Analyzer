# Codebase Health Analyzer (Python)

A lightweight, public-facing CLI tool that scans **Python codebases** and produces a **Codebase Health Report** with:

- A **0–100 Health Score**
- A **score breakdown** across multiple categories
- **Actionable recommendations** that explain:
  - **What was found**
  - **Why it matters**
  - **How to improve**
- A Markdown report you can share (`report_<project>.md`)
- Optional history storage in SQLite (`health.db`)

This project is designed to look and feel like an early-stage developer tool (similar to how professional static analysis tools behave), while remaining simple to run and extend.

---

## What “Health Score” Means

The score is computed from **relative rates**, not raw counts, so large repositories are not punished just for being large.

Instead of “50 long functions = bad,” the analyzer uses **normalized rates** like:

- long functions per **KLOC** (1000 lines of code)
- large files per **100 files**
- empty except blocks per **KLOC**
- print statements per **KLOC**

This keeps scoring fair across small and huge repositories.

---

## Features

### 1) Static analysis on Python code
- Scans `.py` files in a directory recursively
- Parses code using Python’s built-in `ast` module
- Skips common noise directories:
  - `.git`, `__pycache__`, `venv`, `.venv`, `node_modules`, `dist`, `build`

### 2) Health Score (0–100)
The score is a weighted combination of 4 categories:

- **Readability**
  - long functions (rate-based)
  - deep nesting (rate-based)
  - too many parameters (rate-based)
- **Maintainability**
  - oversized files (per-file rate)
  - too many functions per file (per-file rate)
  - TODO/FIXME density (per-file rate)
  - duplicate function names across the repo (normalized)
- **Complexity**
  - too many branches in functions (rate-based)
  - too many loops in functions (rate-based)
  - “god function” heuristic (rate-based)
- **Safety / Style**
  - empty except blocks (rate-based)
  - wildcard imports (rate-based)
  - frequent `print()` usage (rate-based)

Each category uses capped penalties so your score remains meaningful and doesn’t explode on large repos.

### 3) Actionable recommendations (not just “LOW/MEDIUM”)
Every recommendation includes:

- **What was found** (counts + normalized rate)
- **Why it matters** (engineering reasoning)
- **Recommended improvement** (what to change)

### 4) Markdown report output
Generates a file in the project root:

- `report_<project_name>.md`

Example:
- `report_TrainVit.md`

This makes it easy to share results publicly or attach to a PR discussion.

### 5) Local scan history (SQLite)
The tool writes scan results to:

- `health.db`

This database is meant to be **local only** and should be ignored by Git.

---

## Requirements

- Python 3.10+ recommended (3.11+ ideal)
- Git (only if you want to clone external repos)

No external Python packages are required (standard library only).

---

## Installation (Step-by-step)

### 1) Download / clone this repo
If you already have it locally, skip this.

```bash
git clone <YOUR_REPO_URL>
cd CodebaseAnalyzer

###Install dependencies
pip install -r requirements.txt

###Run on THIS project itself (self-scan)

From the project root:

python analyze.py .

###Run on another local folder
python analyze.py path/to/another/project


###Run on a GitHub repository (recommended test)
1) Clone a repo somewhere (DO NOT commit it into this repo)

Create a folder in your analyzer project:

mkdir external_repos
cd external_repos


Clone a public repo:

git clone https://github.com/pallets/flask.git


Go back to analyzer root:

cd ..


Run the analyzer:

python analyze.py external_repos/flask
