# HyperCard Lite (PySide6 + Qt WebEngine)

A small, local, HyperCard-inspired prototype built in Python. It lets you create “stacks” of cards, put buttons and fields on them, script the buttons with a tiny language, and even run SQL against a separate user database — all in one window.

This repo is meant as a teaching / tinkering project, not a finished product.

> **License / Public Domain**  
> All files in this repo (unless stated otherwise) are released into the public domain (CC0 / Unlicense-style). Do whatever you want with them.

---

## Features

- **Cards**: multiple screens in one stack
- **Parts**: add **buttons** and **text fields**
- **Edit / Browse mode**:
  - *Edit*: select parts, drag them, change properties
  - *Browse*: run scripts like a user
- **Draggable layout** in Edit mode (HTML side sends new coords back to Python)
- **Per-part scripts** with a tiny language:
  - `on click ... end click`
  - `go next card`, `go card "Name"`, `answer "Text"`
  - `set field "Name" to "Text"`
  - `get field "Name" into "var"`
  - `sql "SELECT ..."` (user DB only)
- **Separate user database** (`user_data.db`) so scripts can’t break the runtime tables
- **Data Output dock** to show SQL results or errors
- **SQLite-backed** stack (cards, parts, scripts)

---

## Requirements

- Python 3.10+
- `PySide6`
- `PySide6-Qt6-WebEngine` (or equivalent per platform)
- SQLite (built in)

Install:

```bash
pip install PySide6 PySide6-Qt6-WebEngine
```

(Names can differ slightly per platform / packaging.)

---

## Running

```bash
python hypercard.py
```

- The app creates an in-memory stack by default (you can change the DB path in the code).
- A second SQLite file, `user_data.db`, is created for user-land data.

---

## How it works (short)

- The central area is a `QWebEngineView` that renders an HTML “card.”
- Each visual element (button, field) is a row in the `part` table with a JSON blob for position/size/text.
- When you click a part:
  - in **Browse** → the script runs
  - in **Edit** → the part is selected in the Properties panel
- Scripts are parsed by a tiny Python interpreter which calls back into the main window.
- `sql "..."` is **only** executed on the user DB, not on the runtime DB.

---

## Repo Structure (suggested)

- `hypercard.py` – main app
- `README.md` – this file
- `USER_MANUAL.md` – detailed UI walkthrough
- `USE_CASES.md` – small projects / recipes

---

## Status

This is a prototype. Things that are intentionally simple right now:

- script grammar is tiny
- fields are matched by **Name**, not label
- SQL is string-interpolated for convenience

---

## Public Domain

To the extent possible under law, the author(s) dedicate this work to the public domain. You can copy, modify, distribute, and perform the work, even for commercial purposes, all without asking permission.
