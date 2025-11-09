import sys
import json
import sqlite3

from PySide6.QtCore import QObject, Slot, QUrl, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QDockWidget, QListWidget,
    QWidget, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QTextEdit,
    QPushButton, QVBoxLayout, QDialog, QDialogButtonBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel


# -------------------------------------------------
# DB / MODEL (runtime DB)
# -------------------------------------------------

DB_PATH = ":memory:"  # change to "stack.db" for persistence

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stack (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    start_card_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    script TEXT
);

CREATE TABLE IF NOT EXISTS background (
    id INTEGER PRIMARY KEY,
    stack_id INTEGER NOT NULL,
    name TEXT,
    script TEXT,
    layout_json TEXT,
    FOREIGN KEY (stack_id) REFERENCES stack(id)
);

CREATE TABLE IF NOT EXISTS card (
    id INTEGER PRIMARY KEY,
    stack_id INTEGER NOT NULL,
    background_id INTEGER,
    name TEXT,
    order_index INTEGER,
    script TEXT,
    FOREIGN KEY (stack_id) REFERENCES stack(id),
    FOREIGN KEY (background_id) REFERENCES background(id)
);

CREATE TABLE IF NOT EXISTS part (
    id INTEGER PRIMARY KEY,
    card_id INTEGER,
    background_id INTEGER,
    type TEXT NOT NULL,
    name TEXT,
    props_json TEXT,
    script TEXT,
    FOREIGN KEY (card_id) REFERENCES card(id),
    FOREIGN KEY (background_id) REFERENCES background(id)
);
"""


def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)
    cur = conn.execute("SELECT COUNT(*) FROM stack")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO stack (id, name, start_card_id, script) VALUES (1, 'Untitled', 1, '')")
        conn.execute("INSERT INTO background (id, stack_id, name, script, layout_json) VALUES (1, 1, 'Default BG', '', '{}')")
        conn.execute("INSERT INTO card (id, stack_id, background_id, name, order_index, script) VALUES (1, 1, 1, 'Card 1', 1, '')")
        conn.execute("INSERT INTO card (id, stack_id, background_id, name, order_index, script) VALUES (2, 1, 1, 'Card 2', 2, '')")
        # button
        btn_props = {"x": 20, "y": 20, "width": 100, "height": 30, "text": "Next"}
        btn_script = """on click
go next card
end click"""
        conn.execute(
            "INSERT INTO part (card_id, type, name, props_json, script) VALUES (1, 'button', 'NextButton', ?, ?)",
            (json.dumps(btn_props), btn_script)
        )
        # field
        field_props = {"x": 20, "y": 70, "width": 250, "height": 120, "text": "Hello from card 1", "lockText": False}
        conn.execute(
            "INSERT INTO part (card_id, type, name, props_json, script) VALUES (1, 'field', 'Notes', ?, '')",
            (json.dumps(field_props),)
        )
        conn.commit()


def get_cards(conn):
    return conn.execute("SELECT id, name FROM card ORDER BY order_index ASC").fetchall()


def get_card(conn, card_id: int):
    return conn.execute("SELECT id, stack_id, background_id, name, script FROM card WHERE id = ?", (card_id,)).fetchone()


def get_background(conn, bg_id: int):
    return conn.execute("SELECT id, stack_id, name, script FROM background WHERE id = ?", (bg_id,)).fetchone()


def get_parts_for_card(conn, card_id: int, bg_id: int):
    parts = []
    parts.extend(conn.execute("SELECT id, type, name, props_json, script FROM part WHERE background_id = ?", (bg_id,)).fetchall())
    parts.extend(conn.execute("SELECT id, type, name, props_json, script FROM part WHERE card_id = ?", (card_id,)).fetchall())
    return parts


def get_next_card_id(conn, current_id: int):
    row = conn.execute("SELECT order_index FROM card WHERE id = ?", (current_id,)).fetchone()
    if not row:
        return current_id
    idx = row[0]
    nxt = conn.execute("SELECT id FROM card WHERE order_index > ? ORDER BY order_index ASC LIMIT 1", (idx,)).fetchone()
    return nxt[0] if nxt else current_id


# -------------------------------------------------
# SCRIPT ENGINE (now with get field + sql)
# -------------------------------------------------

class Statement:
    def __init__(self, kind, args):
        self.kind = kind
        self.args = args


class Handler:
    def __init__(self, event, statements):
        self.event = event
        self.statements = statements


class Script:
    def __init__(self, handlers):
        self.handlers = handlers


def parse_script(text: str) -> Script:
    if not text:
        return Script({})
    lines = [l.strip() for l in text.splitlines()]
    handlers = {}
    current_event = None
    current_statements = []

    import re

    def flush():
        nonlocal current_event, current_statements
        if current_event:
            handlers[current_event.lower()] = Handler(current_event.lower(), current_statements)
            current_event = None
            current_statements = []

    def parse_statement(line: str) -> Statement:
        ll = line.lower()
        # navigation
        if ll == "go next card":
            return Statement("go", {"target": "next"})
        if ll == "go prev card":
            return Statement("go", {"target": "prev"})
        if ll.startswith("go card "):
            rest = line[8:].strip()
            if rest.startswith('"') and rest.endswith('"'):
                return Statement("go", {"target": "name", "value": rest[1:-1]})
            else:
                return Statement("go", {"target": "number", "value": int(rest)})
        # answer
        if ll.startswith("answer "):
            m = re.match(r'answer\s+"(.*)"\s*$', line, re.IGNORECASE)
            if m:
                return Statement("answer", {"text": m.group(1)})
        # set field
        if ll.startswith("set field "):
            m = re.match(r'set field\s+"(.*)"\s+to\s+"(.*)"\s*$', line, re.IGNORECASE)
            if m:
                return Statement("set_field", {"field": m.group(1), "value": m.group(2)})
        # get field
        if ll.startswith("get field "):
            m = re.match(r'get field\s+"(.*)"\s+into\s+"(.*)"\s*$', line, re.IGNORECASE)
            if m:
                return Statement("get_field", {"field": m.group(1), "var": m.group(2)})
        # sql
        if ll.startswith("sql "):
            m = re.match(r'sql\s+"(.*)"(?:\s+into\s+"(.*)")?$', line, re.IGNORECASE)
            if m:
                query = m.group(1)
                into = m.group(2)
                return Statement("sql", {"query": query, "into": into})
        return Statement("noop", {})

    for line in lines:
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("on "):
            flush()
            current_event = line.split(None, 1)[1].strip()
            current_statements = []
        elif lower.startswith("end "):
            flush()
        else:
            current_statements.append(parse_statement(line))

    flush()
    return Script(handlers)


class ScriptRuntime:
    def __init__(self, app_api):
        self.api = app_api
        self.vars = {}  # per-run vars

    def run_event_chain(self, event_name: str, scripts: list[str]):
        # reset vars for this run
        self.vars = {}
        for text in scripts:
            script = parse_script(text)
            handler = script.handlers.get(event_name.lower())
            if handler:
                for stmt in handler.statements:
                    self.exec_stmt(stmt)
                break

    def exec_stmt(self, stmt: Statement):
        if stmt.kind == "go":
            tgt = stmt.args["target"]
            if tgt == "next":
                self.api.go_next_card()
            elif tgt == "prev":
                self.api.go_prev_card()
            elif tgt == "name":
                self.api.go_card_by_name(stmt.args["value"])
            elif tgt == "number":
                self.api.go_card_by_number(stmt.args["value"])
        elif stmt.kind == "answer":
            self.api.answer(stmt.args["text"])
        elif stmt.kind == "set_field":
            self.api.set_field(stmt.args["field"], stmt.args["value"])
        elif stmt.kind == "get_field":
            self.api.get_field(stmt.args["field"], stmt.args["var"])
        elif stmt.kind == "sql":
            self.api.run_user_sql(stmt.args["query"], stmt.args.get("into"))


# -------------------------------------------------
# QT BRIDGE
# -------------------------------------------------

class Bridge(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @Slot(int)
    def partClicked(self, part_id: int):
        self.main_window.handle_part_clicked(part_id)

    @Slot(int, str)
    def fieldChanged(self, part_id: int, new_text: str):
        self.main_window.handle_field_changed(part_id, new_text)

    @Slot(int, int, int)
    def partMoved(self, part_id: int, new_x: int, new_y: int):
        self.main_window.handle_part_moved(part_id, new_x, new_y)


# -------------------------------------------------
# PROPERTY PANEL
# -------------------------------------------------

class PartPropertyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.part_id = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name", self.name_edit)

        self.x_edit = QSpinBox(); self.x_edit.setRange(0, 2000)
        form.addRow("X", self.x_edit)

        self.y_edit = QSpinBox(); self.y_edit.setRange(0, 2000)
        form.addRow("Y", self.y_edit)

        self.w_edit = QSpinBox(); self.w_edit.setRange(10, 2000)
        form.addRow("Width", self.w_edit)

        self.h_edit = QSpinBox(); self.h_edit.setRange(10, 2000)
        form.addRow("Height", self.h_edit)

        self.text_edit = QLineEdit()
        form.addRow("Text", self.text_edit)

        self.lock_chk = QCheckBox("Lock text")
        form.addRow(self.lock_chk)

        self.script_edit = QTextEdit()
        form.addRow("Script", self.script_edit)

        layout.addLayout(form)

        self.apply_btn = QPushButton("Apply")
        layout.addWidget(self.apply_btn)
        layout.addStretch(1)

    def set_part_data(self, part_id, ptype, name, props: dict, script: str):
        self.part_id = part_id
        self.name_edit.setText(name or "")
        self.x_edit.setValue(int(props.get("x", 0)))
        self.y_edit.setValue(int(props.get("y", 0)))
        self.w_edit.setValue(int(props.get("width", 100)))
        self.h_edit.setValue(int(props.get("height", 30)))
        self.text_edit.setText(props.get("text", ""))
        self.lock_chk.setChecked(bool(props.get("lockText", False)))
        self.script_edit.setPlainText(script or "")

    def collect_data(self):
        return {
            "part_id": self.part_id,
            "name": self.name_edit.text(),
            "x": self.x_edit.value(),
            "y": self.y_edit.value(),
            "width": self.w_edit.value(),
            "height": self.h_edit.value(),
            "text": self.text_edit.text(),
            "lockText": self.lock_chk.isChecked(),
            "script": self.script_edit.toPlainText(),
        }


# -------------------------------------------------
# MAIN WINDOW
# -------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setWindowTitle("HyperCard Lite")
        self.mode = "browse"
        self.current_card_id = 1
        self.selected_part_id = None

        # userland DB
        self.user_conn = sqlite3.connect("user_data.db")

        self.runtime = ScriptRuntime(self)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("pybridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.cardDock = QDockWidget("Cards", self)
        self.cardList = QListWidget()
        self.cardDock.setWidget(self.cardList)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.cardDock)
        self.cardList.itemClicked.connect(self._card_clicked)

        self.propDock = QDockWidget("Properties", self)
        self.propPanel = PartPropertyPanel()
        self.propDock.setWidget(self.propPanel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.propDock)
        self.propPanel.apply_btn.clicked.connect(self.apply_part_changes)

        self.dataDock = QDockWidget("Data Output", self)
        self.dataText = QTextEdit()
        self.dataText.setReadOnly(True)
        self.dataDock.setWidget(self.dataText)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dataDock)

        self._build_menus()

        self.load_cards()
        self.render_current_card()

    # ---------------- menus ----------------
    def _build_menus(self):
        mode_menu = self.menuBar().addMenu("Mode")
        browse_act = QAction("Browse", self)
        browse_act.triggered.connect(lambda: self.set_mode("browse"))
        mode_menu.addAction(browse_act)

        edit_act = QAction("Edit", self)
        edit_act.triggered.connect(lambda: self.set_mode("edit"))
        mode_menu.addAction(edit_act)

        card_menu = self.menuBar().addMenu("Card")

        new_card_act = QAction("New card", self)
        new_card_act.triggered.connect(self.create_new_card)
        card_menu.addAction(new_card_act)

        del_card_act = QAction("Delete current card", self)
        del_card_act.triggered.connect(self.delete_current_card)
        card_menu.addAction(del_card_act)

        edit_card_act = QAction("Edit card script...", self)
        edit_card_act.triggered.connect(self.edit_card_script)
        card_menu.addAction(edit_card_act)

        insert_menu = self.menuBar().addMenu("Insert")

        add_btn_act = QAction("Button", self)
        add_btn_act.triggered.connect(self.add_button_to_current_card)
        insert_menu.addAction(add_btn_act)

        add_field_act = QAction("Field", self)
        add_field_act.triggered.connect(self.add_field_to_current_card)
        insert_menu.addAction(add_field_act)

    # ---------------- mode ----------------
    def set_mode(self, mode: str):
        self.mode = mode
        self.statusBar().showMessage(f"Mode: {mode}", 2000)
        self.render_current_card()

    # ---------------- script API ----------------
    def go_next_card(self):
        nxt = get_next_card_id(self.conn, self.current_card_id)
        self.current_card_id = nxt
        self.render_current_card()
        self.run_open_card_scripts()

    def go_prev_card(self):
        row = self.conn.execute("SELECT order_index FROM card WHERE id = ?", (self.current_card_id,)).fetchone()
        if row:
            idx = row[0]
            prev = self.conn.execute(
                "SELECT id FROM card WHERE order_index < ? ORDER BY order_index DESC LIMIT 1",
                (idx,)
            ).fetchone()
            if prev:
                self.current_card_id = prev[0]
                self.render_current_card()
                self.run_open_card_scripts()

    def go_card_by_name(self, name: str):
        row = self.conn.execute("SELECT id FROM card WHERE name = ?", (name,)).fetchone()
        if row:
            self.current_card_id = row[0]
            self.render_current_card()
            self.run_open_card_scripts()

    def go_card_by_number(self, number: int):
        row = self.conn.execute("SELECT id FROM card WHERE order_index = ?", (number,)).fetchone()
        if row:
            self.current_card_id = row[0]
            self.render_current_card()
            self.run_open_card_scripts()

    def answer(self, text: str):
        # expand {var}
        out = text
        for k, v in self.runtime.vars.items():
            out = out.replace("{" + k + "}", str(v))
        QMessageBox.information(self, "Message", out)

    def set_field(self, field_name: str, value: str):
        card = get_card(self.conn, self.current_card_id)
        parts = get_parts_for_card(self.conn, self.current_card_id, card[2])
        for p in parts:
            pid, ptype, pname, props_json, _ = p
            if pname == field_name and ptype == "field":
                props = json.loads(props_json)
                props["text"] = value
                self.conn.execute("UPDATE part SET props_json = ? WHERE id = ?", (json.dumps(props), pid))
                self.conn.commit()
                self.render_current_card()
                break

    def get_field(self, field_name: str, var_name: str):
        """read current card's field text and store to runtime var"""
        card = get_card(self.conn, self.current_card_id)
        parts = get_parts_for_card(self.conn, self.current_card_id, card[2])
        value = ""
        for p in parts:
            pid, ptype, pname, props_json, _ = p
            if pname == field_name and ptype == "field":
                props = json.loads(props_json)
                value = props.get("text", "")
                break
        self.runtime.vars[var_name] = value

    def run_user_sql(self, query: str, into: str | None):
        # expand {var} like we do in answer
        for k, v in self.runtime.vars.items():
            query = query.replace("{" + k + "}", str(v))
        try:
            cur = self.user_conn.cursor()
            cur.execute(query)
            qlower = query.strip().lower()
            if qlower.startswith("select"):
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
                if into:
                    if rows:
                        self.runtime.vars[into] = str(rows[0][0])
                    else:
                        self.runtime.vars[into] = ""
                else:
                    lines = []
                    if cols:
                        lines.append(" | ".join(cols))
                        lines.append("-" * (len(lines[0]) if lines else 10))
                    for r in rows:
                        lines.append(" | ".join(str(x) for x in r))
                    self.show_data_output("\n".join(lines) if lines else "(no rows)")
            else:
                self.user_conn.commit()
                if into:
                    self.runtime.vars[into] = "ok"
        except Exception as e:
            self.show_data_output(f"SQL error: {e}")

    def show_data_output(self, text: str):
        self.dataText.setPlainText(text)
        self.dataDock.raise_()

    # ---------------- bridge handlers ----------------
    def handle_part_clicked(self, part_id: int):
        if self.mode == "edit":
            self.selected_part_id = part_id
            self.load_part_into_panel(part_id)
            return

        card = get_card(self.conn, self.current_card_id)
        bg = get_background(self.conn, card[2])
        part_row = self.conn.execute("SELECT script FROM part WHERE id = ?", (part_id,)).fetchone()
        part_script = part_row[0] if part_row else ""
        card_script = card[4] or ""
        bg_script = bg[3] or ""
        self.runtime.run_event_chain("click", [part_script, card_script, bg_script, ""])

    def handle_field_changed(self, part_id: int, new_text: str):
        row = self.conn.execute("SELECT props_json FROM part WHERE id = ?", (part_id,)).fetchone()
        if row:
            props = json.loads(row[0])
            props["text"] = new_text
            self.conn.execute("UPDATE part SET props_json = ? WHERE id = ?", (json.dumps(props), part_id))
            self.conn.commit()

    def handle_part_moved(self, part_id: int, new_x: int, new_y: int):
        row = self.conn.execute("SELECT props_json FROM part WHERE id = ?", (part_id,)).fetchone()
        if not row:
            return
        props = json.loads(row[0]) if row[0] else {}
        props["x"] = new_x
        props["y"] = new_y
        self.conn.execute("UPDATE part SET props_json = ? WHERE id = ?", (json.dumps(props), part_id))
        self.conn.commit()
        if self.selected_part_id == part_id:
            part_row = self.conn.execute("SELECT type, name, props_json, script FROM part WHERE id = ?", (part_id,)).fetchone()
            if part_row:
                ptype, name, props_json, script = part_row
                self.propPanel.set_part_data(part_id, ptype, name, json.loads(props_json), script)

    # ---------------- properties ----------------
    def load_part_into_panel(self, part_id: int):
        row = self.conn.execute("SELECT type, name, props_json, script FROM part WHERE id = ?", (part_id,)).fetchone()
        if not row:
            return
        ptype, name, props_json, script = row
        props = json.loads(props_json) if props_json else {}
        self.propPanel.set_part_data(part_id, ptype, name, props, script)

    def apply_part_changes(self):
        data = self.propPanel.collect_data()
        if not data["part_id"]:
            return
        props = {
            "x": data["x"],
            "y": data["y"],
            "width": data["width"],
            "height": data["height"],
            "text": data["text"],
            "lockText": data["lockText"],
        }
        self.conn.execute(
            "UPDATE part SET name = ?, props_json = ?, script = ? WHERE id = ?",
            (data["name"], json.dumps(props), data["script"], data["part_id"])
        )
        self.conn.commit()
        self.render_current_card()

    # ---------------- card list ----------------
    def load_cards(self):
        self.cardList.clear()
        for cid, name in get_cards(self.conn):
            self.cardList.addItem(f"{cid}: {name}")

    def _card_clicked(self, item):
        cid = int(item.text().split(":", 1)[0])
        self.current_card_id = cid
        self.render_current_card()
        self.run_open_card_scripts()

    # ---------------- openCard chain ----------------
    def run_open_card_scripts(self):
        card = get_card(self.conn, self.current_card_id)
        bg = get_background(self.conn, card[2])
        self.runtime.run_event_chain("openCard", [card[4] or "", bg[3] or "", ""])

    # ---------------- rendering ----------------
    def render_current_card(self):
        card = get_card(self.conn, self.current_card_id)
        card_id, _, bg_id, card_name, _ = card
        parts = get_parts_for_card(self.conn, card_id, bg_id)

        html_parts = []
        for p in parts:
            pid, ptype, pname, props_json, _ = p
            props = json.loads(props_json)
            style = (
                f"position:absolute; left:{props.get('x',0)}px; top:{props.get('y',0)}px; "
                f"width:{props.get('width',100)}px; height:{props.get('height',30)}px;"
            )
            if ptype == "button":
                label = props.get("text", pname or "Button")
                html_parts.append(f'<button class="part button" data-part-id="{pid}" style="{style}">{label}</button>')
            elif ptype == "field":
                text = props.get("text", "")
                readonly = "readonly" if props.get("lockText") else ""
                html_parts.append(
                    f'<textarea class="part field" data-part-id="{pid}" style="{style}" {readonly}>{text}</textarea>'
                )

        edit_css = ".part { outline: 1px dashed #55a; cursor: move; }" if self.mode == "edit" else ""

        drag_js = ""
        if self.mode == "edit":
            drag_js = """
let dragging = null;
let offsetX = 0;
let offsetY = 0;

document.addEventListener('mousedown', function(e) {
  const t = e.target;
  if (t && t.dataset && t.dataset.partId) {
    dragging = t;
    const rect = t.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    e.preventDefault();
  }
});

document.addEventListener('mousemove', function(e) {
  if (dragging) {
    const card = document.getElementById('card');
    const cardRect = card.getBoundingClientRect();
    const newLeft = e.clientX - cardRect.left - offsetX;
    const newTop = e.clientY - cardRect.top - offsetY;
    dragging.style.left = newLeft + 'px';
    dragging.style.top = newTop + 'px';
  }
});

document.addEventListener('mouseup', function(e) {
  if (dragging) {
    const card = document.getElementById('card');
    const cardRect = card.getBoundingClientRect();
    const rect = dragging.getBoundingClientRect();
    const newLeft = rect.left - cardRect.left;
    const newTop = rect.top - cardRect.top;
    const partId = parseInt(dragging.dataset.partId);
    if (bridge && bridge.partMoved) {
      bridge.partMoved(partId, Math.round(newLeft), Math.round(newTop));
    }
    dragging = null;
  }
});
"""

        html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
body {{ margin:0; padding:0; background:#fff; }}
#card {{ position:relative; width:800px; height:600px; }}
{edit_css}
</style>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
var bridge = null;
new QWebChannel(qt.webChannelTransport, function(channel) {{
    bridge = channel.objects.pybridge;
    document.addEventListener('click', function(e) {{
        var t = e.target;
        if (t && t.dataset && t.dataset.partId) {{
            bridge.partClicked(parseInt(t.dataset.partId));
        }}
    }});
    document.addEventListener('input', function(e) {{
        var t = e.target;
        if (t && t.dataset && t.dataset.partId && t.tagName.toLowerCase() === 'textarea') {{
            bridge.fieldChanged(parseInt(t.dataset.partId), t.value);
        }}
    }});
    {drag_js}
}});
</script>
</head>
<body>
<div id="card" data-card-id="{card_id}">
{''.join(html_parts)}
</div>
</body>
</html>
"""
        self.view.setHtml(html, QUrl("qrc:///"))
        self.setWindowTitle(f"HyperCard Lite - {card_name}")

        for i in range(self.cardList.count()):
            if self.cardList.item(i).text().startswith(f"{card_id}:"):
                self.cardList.setCurrentRow(i)
                break

    # ---------------- add/remove cards & parts ----------------
    def create_new_card(self):
        card = get_card(self.conn, self.current_card_id)
        if not card:
            return
        _, stack_id, bg_id, _, _ = card
        row = self.conn.execute("SELECT COALESCE(MAX(order_index), 0) FROM card WHERE stack_id = ?", (stack_id,)).fetchone()
        next_idx = (row[0] or 0) + 1
        self.conn.execute(
            "INSERT INTO card (stack_id, background_id, name, order_index, script) VALUES (?, ?, ?, ?, ?)",
            (stack_id, bg_id, f"Card {next_idx}", next_idx, "")
        )
        self.conn.commit()
        new_id = self.conn.execute(
            "SELECT id FROM card WHERE stack_id = ? AND order_index = ?",
            (stack_id, next_idx)
        ).fetchone()[0]
        self.current_card_id = new_id
        self.load_cards()
        self.render_current_card()
        self.run_open_card_scripts()

    def delete_current_card(self):
        count = self.conn.execute("SELECT COUNT(*) FROM card").fetchone()[0]
        if count <= 1:
            QMessageBox.warning(self, "Delete card", "You can't delete the last card.")
            return
        cid = self.current_card_id
        self.conn.execute("DELETE FROM part WHERE card_id = ?", (cid,))
        self.conn.execute("DELETE FROM card WHERE id = ?", (cid,))
        self.conn.commit()
        row = self.conn.execute("SELECT id FROM card ORDER BY order_index ASC LIMIT 1").fetchone()
        self.current_card_id = row[0]
        self.load_cards()
        self.render_current_card()

    def add_button_to_current_card(self):
        card = get_card(self.conn, self.current_card_id)
        if not card:
            return
        card_id = card[0]
        props = {"x": 40, "y": 40, "width": 120, "height": 30, "text": "New Button"}
        script = """on click
answer "Button clicked"
end click"""
        self.conn.execute(
            "INSERT INTO part (card_id, type, name, props_json, script) VALUES (?, 'button', ?, ?, ?)",
            (card_id, "NewButton", json.dumps(props), script)
        )
        self.conn.commit()
        self.render_current_card()

    def add_field_to_current_card(self):
        card = get_card(self.conn, self.current_card_id)
        if not card:
            return
        card_id = card[0]
        props = {"x": 40, "y": 90, "width": 200, "height": 80, "text": "New field", "lockText": False}
        self.conn.execute(
            "INSERT INTO part (card_id, type, name, props_json, script) VALUES (?, 'field', ?, ?, '')",
            (card_id, "NewField", json.dumps(props))
        )
        self.conn.commit()
        self.render_current_card()

    def edit_card_script(self):
        card = get_card(self.conn, self.current_card_id)
        if not card:
            return
        card_id, _, _, card_name, card_script = card

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit script for {card_name}")
        layout = QVBoxLayout(dlg)
        edit = QTextEdit()
        edit.setPlainText(card_script or "")
        layout.addWidget(edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            new_script = edit.toPlainText()
            self.conn.execute("UPDATE card SET script = ? WHERE id = ?", (new_script, card_id))
            self.conn.commit()
            QMessageBox.information(self, "Card script", "Card script saved.")


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    app = QApplication(sys.argv)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    win = MainWindow(conn)
    win.resize(1200, 700)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
