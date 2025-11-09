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

- Python 3.10+ (3.12 also works; 3.13 if PySide6 wheel is available)
- `PySide6`
- `PySide6-Qt6-WebEngine` (depending on your platform/package)
- SQLite (built in)

Install:

```bash
pip install PySide6 PySide6-Qt6-WebEngine
