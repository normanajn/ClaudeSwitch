#!/usr/bin/env python3
"""
claudeswitch — manage Claude Code settings profiles.

Usage:
  claudeswitch                    Launch interactive TUI (curses)
  claudeswitch init               Create default profile storage
  claudeswitch --gui              Launch graphical UI (Qt)
  claudeswitch --list             List available profiles
  claudeswitch --switch <name>    Switch to the named profile
  claudeswitch --help             Show this message

Short forms:
  -l   --list
  -s   --switch
"""

import curses
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("ESCDELAY", "25")   # fast ESC in ncurses

CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
STATE_FILE = CLAUDE_DIR / ".claudeswitch"


def current_profile():
    return STATE_FILE.read_text().strip() if STATE_FILE.exists() else "none"


def profile_path(name):
    return CLAUDE_DIR / ("settings-" + name + ".json")


def discover_profiles():
    profiles = sorted(
        p.stem[len("settings-"):]
        for p in CLAUDE_DIR.glob("settings-*.json")
        if p.is_file()
    )
    if "login" in profiles:
        profiles.insert(0, profiles.pop(profiles.index("login")))
    return profiles


def backup_settings():
    if SETTINGS_FILE.exists():
        backup_dir = CLAUDE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(SETTINGS_FILE, backup_dir / ("settings_" + ts + ".json"))


def activate_profile(name):
    src = profile_path(name)
    if not src.exists():
        raise FileNotFoundError("Profile file not found: " + str(src))
    backup_settings()
    shutil.copy(src, SETTINGS_FILE)
    STATE_FILE.write_text(name)


def read_env(name):
    profile = profile_path(name)
    if not profile.exists():
        return {}
    try:
        return json.loads(profile.read_text()).get("env", {})
    except (json.JSONDecodeError, OSError):
        return {}


def write_env(name, env):
    profile = profile_path(name)
    base = {}
    if profile.exists():
        try:
            data = json.loads(profile.read_text())
            base = {key: value for key, value in data.items() if key != "env"}
        except (json.JSONDecodeError, OSError):
            pass
    base["env"] = {key: value for key, value in env.items() if value}
    profile.write_text(json.dumps(base, indent=2) + "\n")


def do_init():
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    (CLAUDE_DIR / "backups").mkdir(exist_ok=True)
    login_profile = profile_path("login")
    if not login_profile.exists():
        login_profile.write_text("{}\n")


def fields_for(name, env):
    """
    Return field-spec list for a profile type, or None for login.
    Each spec: {key, label, default, secret (bool), optional (bool)}
    """

    def field(key, label, default="", secret=False, optional=False):
        return dict(
            key=key,
            label=label,
            default=env.get(key, default),
            secret=secret,
            optional=optional,
        )

    if name == "login":
        return None

    if name == "asksage":
        return [
            field("ANTHROPIC_API_KEY", "API Key", secret=True),
            field(
                "ANTHROPIC_BASE_URL",
                "Base URL",
                "https://api.asksage.ai/server/user-anthropic-proxy",
            ),
            field("ASKSAGE_TOKEN", "AskSage Token", secret=True, optional=True),
        ]

    if name == "litellm":
        return [
            field("ANTHROPIC_API_KEY", "API Key", secret=True),
            field("ANTHROPIC_BASE_URL", "LiteLLM Proxy URL", "http://localhost:4000"),
        ]

    if name == "azure":
        return [
            field("ANTHROPIC_API_KEY", "Azure API Key", secret=True),
            field(
                "ANTHROPIC_BASE_URL",
                "Azure Endpoint URL",
                "https://<resource>.openai.azure.com",
            ),
            field("AZURE_API_VERSION", "API Version", "2024-02-01"),
            field("AZURE_DEPLOYMENT_NAME", "Deployment Name", "claude-3-5-sonnet"),
        ]

    return [
        field("ANTHROPIC_API_KEY", "API Key", secret=True),
        field("ANTHROPIC_BASE_URL", "Base URL", "https://api.anthropic.com"),
    ]


def run_tui():
    curses.wrapper(_tui_main)


CP_HEADER = 1
CP_SEL = 2
CP_ACTIVE = 3
CP_FOOTER = 4
CP_FIELD_ON = 5
CP_FIELD_OFF = 6
CP_BORDER = 7
CP_DIM = 8


def _init_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_HEADER, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(CP_SEL, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(CP_ACTIVE, curses.COLOR_GREEN, -1)
    curses.init_pair(CP_FOOTER, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_FIELD_ON, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_FIELD_OFF, curses.COLOR_WHITE, -1)
    curses.init_pair(CP_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(CP_DIM, curses.COLOR_WHITE, -1)


def _inline_edit(win, y, x, width, initial="", secret=False):
    """Single-line text editor. Returns new string or None on Esc."""
    buf = list(initial)
    cpos = len(buf)
    off = 0
    view_width = width - 1
    curses.curs_set(1)

    def repaint():
        nonlocal off
        if cpos - off >= view_width:
            off = cpos - view_width + 1
        if cpos < off:
            off = cpos
        seg = buf[off:off + view_width]
        display = ("●" * len(seg)) if secret else "".join(seg)
        try:
            win.addstr(
                y,
                x,
                display.ljust(view_width)[:view_width],
                curses.color_pair(CP_FIELD_ON),
            )
            win.move(y, x + cpos - off)
        except curses.error:
            pass
        win.refresh()

    repaint()
    while True:
        ch = win.getch()
        if ch in (curses.KEY_ENTER, 10, 13):
            break
        if ch == 27:
            curses.curs_set(0)
            return None
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if cpos > 0:
                del buf[cpos - 1]
                cpos -= 1
        elif ch == curses.KEY_DC:
            if cpos < len(buf):
                del buf[cpos]
        elif ch == curses.KEY_LEFT:
            cpos = max(0, cpos - 1)
        elif ch == curses.KEY_RIGHT:
            cpos = min(len(buf), cpos + 1)
        elif ch == 1:
            cpos = 0
        elif ch == 5:
            cpos = len(buf)
        elif ch == 11:
            del buf[cpos:]
        elif 32 <= ch <= 126:
            buf.insert(cpos, chr(ch))
            cpos += 1
        repaint()

    curses.curs_set(0)
    return "".join(buf)


def _make_popup(stdscr, title, lines, extra=0):
    height, width = stdscr.getmaxyx()
    inner = max(len(title), max((len(line) for line in lines), default=0)) + 4
    box_w = min(max(inner, 36) + 4, width - 4)
    box_h = min(len(lines) + 4 + extra, height - 4)
    pop = curses.newwin(box_h, box_w, (height - box_h) // 2, (width - box_w) // 2)
    pop.attron(curses.color_pair(CP_BORDER))
    pop.box()
    pop.attroff(curses.color_pair(CP_BORDER))
    pop.addstr(0, (box_w - len(title) - 2) // 2, " " + title + " ", curses.A_BOLD)
    for index, line in enumerate(lines[:box_h - 4]):
        try:
            pop.addstr(index + 2, 3, line[:box_w - 6])
        except curses.error:
            pass
    return pop, box_w, box_h


def _dismiss(pop, stdscr):
    del pop
    stdscr.touchwin()
    stdscr.refresh()


def _popup_message(stdscr, title, lines, success=False):
    pop, box_w, box_h = _make_popup(stdscr, title, lines, extra=2)
    hint = "─ press any key ─"
    try:
        pop.addstr(
            box_h - 2,
            (box_w - len(hint)) // 2,
            hint,
            curses.color_pair(CP_DIM) | curses.A_DIM,
        )
    except curses.error:
        pass
    if success:
        try:
            pop.addstr(
                0,
                (box_w - len(title) - 2) // 2,
                " " + title + " ",
                curses.color_pair(CP_ACTIVE) | curses.A_BOLD,
            )
        except curses.error:
            pass
    pop.refresh()
    pop.getch()
    _dismiss(pop, stdscr)


def _popup_confirm(stdscr, title, question):
    lines = question.split("\n")
    pop, box_w, box_h = _make_popup(stdscr, title, lines, extra=2)
    hint = "[ y ] Yes    [ n ] No"
    try:
        pop.addstr(box_h - 2, (box_w - len(hint)) // 2, hint, curses.A_BOLD)
    except curses.error:
        pass
    pop.refresh()
    while True:
        ch = pop.getch()
        if ch in (ord("y"), ord("Y")):
            _dismiss(pop, stdscr)
            return True
        if ch in (ord("n"), ord("N"), 27):
            _dismiss(pop, stdscr)
            return False


def _configure_form(stdscr, title, fields):
    """Multi-field form. Returns {key: value} or None."""
    height, width = stdscr.getmaxyx()
    label_width = max(len(field["label"]) for field in fields) + 10
    input_width = min(45, width - label_width - 10)
    box_w = min(label_width + input_width + 8, width - 4)
    input_width = box_w - label_width - 8
    box_h = min(len(fields) * 2 + 6, height - 4)
    by = (height - box_h) // 2
    bx = (width - box_w) // 2
    values = {field["key"]: field.get("default", "") for field in fields}
    cur = 0

    while True:
        pop = curses.newwin(box_h, box_w, by, bx)
        pop.attron(curses.color_pair(CP_BORDER))
        pop.box()
        pop.attroff(curses.color_pair(CP_BORDER))
        pop.addstr(0, (box_w - len(title) - 2) // 2, " " + title + " ", curses.A_BOLD)

        visible_count = min(len(fields), (box_h - 6) // 2)
        for index in range(visible_count):
            field = fields[index]
            row = index * 2 + 2
            is_current = index == cur
            tag = " (opt)" if field.get("optional") else ""
            label = field["label"] + tag + ":"
            attr = curses.color_pair(CP_SEL) | curses.A_BOLD if is_current else 0
            try:
                pop.addstr(row, 2, label.ljust(label_width), attr)
            except curses.error:
                pass
            value = values[field["key"]]
            display = "●" * len(value) if field.get("secret") else value
            display = display[-input_width:] if len(display) > input_width else display
            input_attr = (
                curses.color_pair(CP_FIELD_ON)
                if is_current
                else curses.color_pair(CP_FIELD_OFF) | curses.A_DIM
            )
            try:
                pop.addstr(row, label_width + 2, display.ljust(input_width)[:input_width], input_attr)
            except curses.error:
                pass

        hint = "↑↓/Tab move  Enter edit  s save  Esc cancel"
        try:
            pop.addstr(
                box_h - 2,
                max(0, (box_w - len(hint)) // 2),
                hint[:box_w - 2],
                curses.color_pair(CP_DIM) | curses.A_DIM,
            )
        except curses.error:
            pass
        pop.refresh()

        ch = pop.getch()

        if ch == 27:
            _dismiss(pop, stdscr)
            return None
        if ch in (ord("s"), ord("S")):
            missing = [
                field["label"]
                for field in fields
                if not field.get("optional") and not values[field["key"]]
            ]
            _dismiss(pop, stdscr)
            if missing:
                _popup_message(
                    stdscr,
                    "Required",
                    ["These fields are required:"] + ["  • " + label for label in missing],
                )
                continue
            return values
        if ch == curses.KEY_UP:
            cur = (cur - 1) % len(fields)
            _dismiss(pop, stdscr)
        elif ch in (curses.KEY_DOWN, 9):
            cur = (cur + 1) % len(fields)
            _dismiss(pop, stdscr)
        elif ch in (curses.KEY_ENTER, 10, 13):
            field = fields[cur]
            row = cur * 2 + 2
            if row < box_h - 2:
                result = _inline_edit(
                    pop,
                    row,
                    label_width + 2,
                    input_width,
                    values[field["key"]],
                    field.get("secret", False),
                )
                if result is not None:
                    values[field["key"]] = result
            _dismiss(pop, stdscr)
        else:
            _dismiss(pop, stdscr)


def _tui_do_configure(stdscr, name):
    env = read_env(name)
    spec = fields_for(name, env)
    if spec is None:
        profile = profile_path(name)
        if not profile.exists():
            profile.write_text("{}\n")
        _popup_message(
            stdscr,
            "Login Profile",
            [
                "Login mode uses your Anthropic subscription.",
                "No API key is needed.",
                "",
                "Profile is ready to use.",
            ],
            success=True,
        )
        return
    result = _configure_form(stdscr, "Configure: " + name, spec)
    if result is None:
        return
    write_env(name, result)
    _popup_message(
        stdscr,
        "Saved",
        ["Profile '" + name + "' saved.", "", "File: " + str(profile_path(name))],
        success=True,
    )


def _tui_new_profile(stdscr):
    height, width = stdscr.getmaxyx()
    box_h = 7
    box_w = min(52, width - 4)
    pop = curses.newwin(box_h, box_w, (height - box_h) // 2, (width - box_w) // 2)
    pop.attron(curses.color_pair(CP_BORDER))
    pop.box()
    pop.attroff(curses.color_pair(CP_BORDER))
    pop.addstr(0, (box_w - 15) // 2, " New Profile ", curses.A_BOLD)
    pop.addstr(2, 3, "Name: ")
    pop.addstr(5, 3, "Enter confirm   Esc cancel", curses.color_pair(CP_DIM) | curses.A_DIM)
    pop.refresh()
    raw = _inline_edit(pop, 2, 9, box_w - 12)
    _dismiss(pop, stdscr)
    if not raw:
        return None
    name = raw.strip().lower().replace(" ", "-")
    if not name:
        return None
    profile = profile_path(name)
    if profile.exists():
        _popup_message(stdscr, "Error", ["Profile '" + name + "' already exists."])
        return None
    profile.write_text("{}\n")
    return name


_FOOTER = "  ↑↓ Navigate   [Enter] Switch   q Quit   m More  "
_FOOTER_MORE = "  c Configure   n New   d Delete   i Init   < Back  "


def _draw_main(stdscr, profiles, selected_index, active, msg, footer=_FOOTER):
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    header = "  ClaudeSwitch — Profile Manager"
    cur_tag = "  current: " + active + "  "
    stdscr.attron(curses.color_pair(CP_HEADER) | curses.A_BOLD)
    stdscr.addstr(0, 0, (header + cur_tag.rjust(width - len(header)))[:width])
    stdscr.attroff(curses.color_pair(CP_HEADER) | curses.A_BOLD)

    col_status = 22
    col_file = col_status + 10
    try:
        stdscr.addstr(
            2,
            2,
            "PROFILE".ljust(col_status - 2) + "STATUS    FILE",
            curses.A_BOLD | curses.A_UNDERLINE,
        )
    except curses.error:
        pass

    has_login = "login" in profiles
    for index, name in enumerate(profiles):
        sep_offset = 1 if (has_login and index > 0) else 0
        row = index + 3 + sep_offset
        if row >= height - 3:
            break

        if has_login and index == 1:
            try:
                stdscr.addstr(row - 1, 2, "─" * (width - 4), curses.color_pair(CP_DIM) | curses.A_DIM)
            except curses.error:
                pass

        is_selected = index == selected_index
        is_active = name == active
        file_path = str(profile_path(name)).replace(str(Path.home()), "~")
        available_width = max(1, width - col_file - 2)
        if len(file_path) > available_width:
            file_path = "…" + file_path[-(available_width - 1):]

        if is_selected:
            line = (" ▶ " + name.ljust(col_status - 2) + ("ACTIVE" if is_active else "ready").ljust(10) + file_path)
            stdscr.attron(curses.color_pair(CP_SEL) | curses.A_BOLD)
            try:
                stdscr.addstr(row, 0, line.ljust(width)[:width])
            except curses.error:
                pass
            stdscr.attroff(curses.color_pair(CP_SEL) | curses.A_BOLD)
        else:
            try:
                stdscr.addstr(row, 2, "  " + name.ljust(col_status - 2))
            except curses.error:
                pass
            status_attr = curses.color_pair(CP_ACTIVE) | curses.A_BOLD if is_active else curses.A_DIM
            try:
                stdscr.addstr(row, col_status, ("ACTIVE    " if is_active else "ready     "), status_attr)
                stdscr.addstr(row, col_file, file_path[:available_width])
            except curses.error:
                pass

    if not profiles:
        try:
            stdscr.addstr(4, 4, "No profiles found in " + str(CLAUDE_DIR), curses.A_DIM)
            stdscr.addstr(5, 4, "Press i to initialise defaults, or n to create one.", curses.A_DIM)
        except curses.error:
            pass

    if msg:
        try:
            stdscr.addstr(height - 3, 2, msg[:width - 4], curses.color_pair(CP_ACTIVE) | curses.A_BOLD)
        except curses.error:
            pass

    stdscr.attron(curses.color_pair(CP_FOOTER))
    try:
        stdscr.addstr(height - 2, 0, footer.ljust(width)[:width])
    except curses.error:
        pass
    stdscr.attroff(curses.color_pair(CP_FOOTER))
    stdscr.refresh()


def _tui_main(stdscr):
    _init_colors()
    curses.curs_set(0)
    CLAUDE_DIR.mkdir(exist_ok=True)

    profiles = discover_profiles()
    selected_index = 0
    active = current_profile()
    msg = ""
    mode = "main"

    while True:
        if profiles and selected_index >= len(profiles):
            selected_index = len(profiles) - 1
        if selected_index < 0:
            selected_index = 0

        footer = _FOOTER_MORE if mode == "more" else _FOOTER
        _draw_main(stdscr, profiles, selected_index, active, msg, footer)
        msg = ""
        ch = stdscr.getch()

        if ch in (ord("q"), ord("Q")):
            break
        if ch in (ord("<"), ord(",")):
            mode = "main"
        elif ch in (ord("m"), ord("M")):
            mode = "more"
        elif ch == curses.KEY_UP:
            if profiles:
                selected_index = (selected_index - 1) % len(profiles)
        elif ch == curses.KEY_DOWN:
            if profiles:
                selected_index = (selected_index + 1) % len(profiles)
        elif ch == curses.KEY_HOME:
            selected_index = 0
        elif ch == curses.KEY_END:
            selected_index = max(0, len(profiles) - 1)
        elif ch in (curses.KEY_ENTER, 10, 13):
            if profiles:
                name = profiles[selected_index]
                if name == active:
                    msg = "'" + name + "' is already the active profile."
                else:
                    try:
                        activate_profile(name)
                        active = name
                        msg = "Switched to: " + name
                    except Exception as exc:
                        _popup_message(stdscr, "Error", [str(exc)])
        elif ch in (ord("c"), ord("C")):
            if mode == "more" and profiles:
                _tui_do_configure(stdscr, profiles[selected_index])
                profiles = discover_profiles()
        elif ch in (ord("n"), ord("N")):
            if mode == "more":
                new_name = _tui_new_profile(stdscr)
                if new_name:
                    profiles = discover_profiles()
                    try:
                        selected_index = profiles.index(new_name)
                    except ValueError:
                        pass
                    msg = "Created '" + new_name + "'. Press c to configure."
        elif ch in (ord("d"), ord("D")):
            if mode == "more" and profiles:
                name = profiles[selected_index]
                if name == active:
                    _popup_message(
                        stdscr,
                        "Cannot Delete",
                        ["Cannot delete the active profile.", "Switch to another profile first."],
                    )
                elif _popup_confirm(
                    stdscr,
                    "Confirm Delete",
                    "Delete profile '" + name + "'?\n" + str(profile_path(name)),
                ):
                    try:
                        profile_path(name).unlink()
                    except OSError:
                        pass
                    profiles = discover_profiles()
                    selected_index = min(selected_index, max(0, len(profiles) - 1))
                    msg = "Deleted profile '" + name + "'."
        elif ch in (ord("i"), ord("I")):
            if mode == "more":
                do_init()
                profiles = discover_profiles()
                active = current_profile()
                msg = "Initialised default profiles."
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()


def _import_qt():
    """Try PySide6 then PyQt5. Returns the binding name or None."""
    try:
        import PySide6.QtWidgets as _unused

        return "pyside6"
    except ImportError:
        pass
    try:
        import PyQt5.QtWidgets as _unused

        return "pyqt5"
    except ImportError:
        pass
    return None


def run_gui():
    binding = _import_qt()
    if binding is None:
        print("claudeswitch --gui requires PySide6 or PyQt5.", file=sys.stderr)
        print("Install one:  pip install 'claudeswitch[gui]'   or   pip install PyQt5", file=sys.stderr)
        return 1

    if binding == "pyside6":
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
        from PySide6.QtWidgets import (
            QApplication,
            QFileDialog,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QScrollArea,
            QSplitter,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    else:
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor, QFont, QKeySequence
        from PyQt5.QtWidgets import (
            QAction,
            QApplication,
            QFileDialog,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QScrollArea,
            QSplitter,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

    class ClaudeSwitchWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("ClaudeSwitch")
            self.resize(1000, 650)
            self._selected = None
            self._form_fields = []
            self._form_widgets = {}
            self._setup_ui()
            self._setup_menu()
            self._refresh()

        def _setup_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            root = QHBoxLayout(central)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            main_split = QSplitter(Qt.Horizontal)
            root.addWidget(main_split)

            left = QWidget()
            left.setMinimumWidth(180)
            left_layout = QVBoxLayout(left)
            left_layout.setContentsMargins(10, 10, 6, 10)

            hdr = QLabel("Profiles")
            hdr.setStyleSheet("font-weight: bold; font-size: 15px; padding-bottom: 4px;")
            left_layout.addWidget(hdr)

            self.profile_list = QListWidget()
            self.profile_list.setAlternatingRowColors(True)
            self.profile_list.currentRowChanged.connect(self._on_selection_changed)
            self.profile_list.itemDoubleClicked.connect(self._cmd_switch)
            left_layout.addWidget(self.profile_list)

            btn_switch = QPushButton("▶  Switch to Selected")
            btn_switch.clicked.connect(self._cmd_switch)
            left_layout.addWidget(btn_switch)

            main_split.addWidget(left)
            main_split.setStretchFactor(0, 1)

            right_split = QSplitter(Qt.Vertical)

            json_box = QGroupBox("Settings JSON  (live preview)")
            json_layout = QVBoxLayout(json_box)
            self.json_view = QTextEdit()
            self.json_view.setReadOnly(True)
            mono = QFont("Courier New", 10)
            mono.setStyleHint(QFont.Monospace)
            self.json_view.setFont(mono)
            self.json_view.setStyleSheet("background:#1e1e1e; color:#d4d4d4; border:none;")
            json_layout.addWidget(self.json_view)
            right_split.addWidget(json_box)

            form_box = QGroupBox("Configuration")
            form_outer = QVBoxLayout(form_box)

            self.form_scroll = QScrollArea()
            self.form_scroll.setWidgetResizable(True)
            self.form_container = QWidget()
            self.form_layout = QFormLayout(self.form_container)
            self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            self.form_scroll.setWidget(self.form_container)
            form_outer.addWidget(self.form_scroll)

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            self.btn_save = QPushButton("  Save  ")
            self.btn_save.setEnabled(False)
            self.btn_save.clicked.connect(self._cmd_save)
            btn_row.addWidget(self.btn_save)
            form_outer.addLayout(btn_row)

            right_split.addWidget(form_box)
            right_split.setSizes([220, 400])

            main_split.addWidget(right_split)
            main_split.setStretchFactor(1, 3)
            main_split.setSizes([200, 800])

            self.statusBar().showMessage("Active profile: " + current_profile())

        def _setup_menu(self):
            menu_bar = self.menuBar()

            file_menu = menu_bar.addMenu("&File")
            action = QAction("&Save Profile", self)
            action.setShortcut(QKeySequence.Save)
            action.triggered.connect(self._cmd_save)
            file_menu.addAction(action)

            action = QAction("&Load Config from File…", self)
            action.triggered.connect(self._cmd_load_from_file)
            file_menu.addAction(action)

            action = QAction("&Export Profile to File…", self)
            action.triggered.connect(self._cmd_export_to_file)
            file_menu.addAction(action)

            file_menu.addSeparator()

            action = QAction("E&xit", self)
            action.setShortcut(QKeySequence.Quit)
            action.triggered.connect(self.close)
            file_menu.addAction(action)

            profile_menu = menu_bar.addMenu("&Profile")
            action = QAction("&Switch to Selected", self)
            action.triggered.connect(self._cmd_switch)
            profile_menu.addAction(action)

            action = QAction("&New Profile…", self)
            action.triggered.connect(self._cmd_new)
            profile_menu.addAction(action)

            action = QAction("&Delete Profile", self)
            action.triggered.connect(self._cmd_delete)
            profile_menu.addAction(action)

            profile_menu.addSeparator()

            action = QAction("&Initialize Defaults", self)
            action.triggered.connect(self._cmd_init)
            profile_menu.addAction(action)

            help_menu = menu_bar.addMenu("&Help")
            action = QAction("&About", self)
            action.triggered.connect(self._cmd_about)
            help_menu.addAction(action)

        def _refresh(self):
            profiles = discover_profiles()
            active = current_profile()
            previous_selection = self._selected

            self.profile_list.blockSignals(True)
            self.profile_list.clear()
            for name in profiles:
                is_active = name == active
                item = QListWidgetItem(("▶  " + name + "  [ACTIVE]") if is_active else ("    " + name))
                item.setData(Qt.UserRole, name)
                if is_active:
                    item.setForeground(QColor("#00bb44"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.profile_list.addItem(item)
            self.profile_list.blockSignals(False)

            if previous_selection:
                for index in range(self.profile_list.count()):
                    if self.profile_list.item(index).data(Qt.UserRole) == previous_selection:
                        self.profile_list.setCurrentRow(index)
                        break

            self.statusBar().showMessage("Active profile: " + active)

        def _on_selection_changed(self, row):
            if row < 0:
                self._selected = None
                self.json_view.clear()
                self._clear_form()
                self.btn_save.setEnabled(False)
                return
            name = self.profile_list.item(row).data(Qt.UserRole)
            self._selected = name
            self._refresh_json_view(name)
            self._rebuild_form(name)
            self.btn_save.setEnabled(True)

        def _refresh_json_view(self, name):
            profile = profile_path(name)
            if profile.exists():
                try:
                    self.json_view.setPlainText(profile.read_text())
                except OSError as exc:
                    self.json_view.setPlainText("# Error reading file:\n# " + str(exc))
            else:
                self.json_view.setPlainText("# Profile file not yet created.\n{}")

        def _clear_form(self):
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
            self._form_widgets = {}
            self._form_fields = []

        def _rebuild_form(self, name):
            self._clear_form()
            env = read_env(name)
            fields = fields_for(name, env)

            if fields is None:
                label = QLabel(
                    "Login profile — no API configuration needed.\n"
                    "Uses your Anthropic subscription directly.\n\n"
                    "The profile file is ready to activate."
                )
                label.setWordWrap(True)
                self.form_layout.addRow(label)
                return

            self._form_fields = fields
            for field in fields:
                key = field["key"]
                label = field["label"]
                default = field.get("default", "")
                secret = field.get("secret", False)
                optional = field.get("optional", False)
                row_label = label + (" (optional)" if optional else "") + ":"

                line_edit = QLineEdit(default)
                line_edit.setMinimumWidth(300)
                if secret:
                    line_edit.setEchoMode(QLineEdit.Password)
                    line_edit.setPlaceholderText("(unchanged)" if default else "")

                    container = QWidget()
                    row_layout = QHBoxLayout(container)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.addWidget(line_edit)

                    toggle = QPushButton("Show")
                    toggle.setFixedWidth(52)
                    toggle.setCheckable(True)
                    toggle.toggled.connect(self._make_toggle(line_edit, toggle))
                    row_layout.addWidget(toggle)
                    self.form_layout.addRow(row_label, container)
                else:
                    self.form_layout.addRow(row_label, line_edit)

                line_edit.textChanged.connect(self._on_field_changed)
                self._form_widgets[key] = line_edit

        @staticmethod
        def _make_toggle(line_edit, button):
            def toggle_echo(checked):
                line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
                button.setText("Hide" if checked else "Show")

            return toggle_echo

        def _on_field_changed(self):
            if not self._selected or not self._form_fields:
                return
            env = {field["key"]: self._form_widgets[field["key"]].text() for field in self._form_fields}
            profile = profile_path(self._selected)
            base = {}
            if profile.exists():
                try:
                    data = json.loads(profile.read_text())
                    base = {key: value for key, value in data.items() if key != "env"}
                except (json.JSONDecodeError, OSError):
                    pass
            base["env"] = {key: value for key, value in env.items() if value}
            self.json_view.setPlainText(json.dumps(base, indent=2))

        def _cmd_switch(self, *_):
            if not self._selected:
                QMessageBox.information(self, "No Selection", "Select a profile to switch to.")
                return
            name = self._selected
            if name == current_profile():
                QMessageBox.information(self, "Already Active", "'" + name + "' is already active.")
                return
            try:
                activate_profile(name)
                self._refresh()
                self.statusBar().showMessage("Switched to: " + name)
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

        def _cmd_save(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection", "Select a profile first.")
                return
            name = self._selected
            if not self._form_fields:
                profile = profile_path(name)
                if not profile.exists():
                    profile.write_text("{}\n")
                self.statusBar().showMessage("Profile '" + name + "' is ready.")
                return
            env = {field["key"]: self._form_widgets[field["key"]].text() for field in self._form_fields}
            missing = [
                field["label"]
                for field in self._form_fields
                if not field.get("optional") and not env[field["key"]]
            ]
            if missing:
                QMessageBox.warning(
                    self,
                    "Required Fields",
                    "These fields are required:\n" + "\n".join("  • " + label for label in missing),
                )
                return
            write_env(name, env)
            self._refresh_json_view(name)
            self.statusBar().showMessage("Saved profile '" + name + "'.")

        def _cmd_load_from_file(self):
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Config File",
                str(Path.home()),
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return
            stem = Path(path).stem
            if stem.startswith("settings-"):
                stem = stem[len("settings-"):]
            name, ok = QInputDialog.getText(self, "Profile Name", "Save as profile name:", text=stem)
            if not ok or not name:
                return
            name = name.strip().lower().replace(" ", "-")
            if not name:
                return
            dest = profile_path(name)
            if dest.exists():
                response = QMessageBox.question(
                    self,
                    "Overwrite?",
                    "Profile '" + name + "' already exists. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if response != QMessageBox.Yes:
                    return
            try:
                shutil.copy(path, dest)
            except OSError as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self._refresh()
            for index in range(self.profile_list.count()):
                if self.profile_list.item(index).data(Qt.UserRole) == name:
                    self.profile_list.setCurrentRow(index)
                    break
            self.statusBar().showMessage("Loaded '" + name + "' from " + path)

        def _cmd_export_to_file(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection", "Select a profile to export.")
                return
            name = self._selected
            default = str(Path.home() / ("settings-" + name + ".json"))
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Profile",
                default,
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return
            try:
                shutil.copy(profile_path(name), path)
            except OSError as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.statusBar().showMessage("Exported '" + name + "' to " + path)

        def _cmd_new(self):
            name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
            if not ok or not name:
                return
            name = name.strip().lower().replace(" ", "-")
            if not name:
                return
            profile = profile_path(name)
            if profile.exists():
                QMessageBox.warning(self, "Exists", "Profile '" + name + "' already exists.")
                return
            profile.write_text("{}\n")
            self._refresh()
            for index in range(self.profile_list.count()):
                if self.profile_list.item(index).data(Qt.UserRole) == name:
                    self.profile_list.setCurrentRow(index)
                    break

        def _cmd_delete(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection", "Select a profile to delete.")
                return
            name = self._selected
            if name == current_profile():
                QMessageBox.warning(
                    self,
                    "Cannot Delete",
                    "Cannot delete the active profile.\nSwitch to another profile first.",
                )
                return
            response = QMessageBox.question(
                self,
                "Confirm Delete",
                "Delete profile '" + name + "'?\n" + str(profile_path(name)),
                QMessageBox.Yes | QMessageBox.No,
            )
            if response == QMessageBox.Yes:
                try:
                    profile_path(name).unlink()
                except OSError:
                    pass
                self._selected = None
                self._refresh()

        def _cmd_init(self):
            do_init()
            self._refresh()
            self.statusBar().showMessage("Initialised default profiles.")

        def _cmd_about(self):
            QMessageBox.about(
                self,
                "About ClaudeSwitch",
                "<b>ClaudeSwitch</b><br>"
                "Manage Claude Code settings profiles.<br><br>"
                "Profiles are stored in:<br>"
                "<tt>~/.claude/settings-&lt;name&gt;.json</tt><br><br>"
                "The active profile is copied to:<br>"
                "<tt>~/.claude/settings.json</tt>",
            )

    app = QApplication(sys.argv)
    app.setApplicationName("ClaudeSwitch")
    window = ClaudeSwitchWindow()
    window.show()
    return app.exec() if binding == "pyside6" else app.exec_()


def _print_help():
    print(__doc__.strip())


def _print_unknown_args(args):
    print("claudeswitch: unknown arguments: " + " ".join(args), file=sys.stderr)
    print("Try 'claudeswitch --help' for usage.", file=sys.stderr)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)

    if "--help" in args or "-h" in args:
        _print_help()
        return 0

    if not args:
        try:
            run_tui()
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print("claudeswitch: " + str(exc), file=sys.stderr)
            return 1

    if args == ["init"]:
        do_init()
        print("Initialised default profiles in " + str(CLAUDE_DIR))
        return 0

    if args in (["--list"], ["-l"]):
        profiles = discover_profiles()
        active = current_profile()
        if not profiles:
            print("No profiles found. Run: claudeswitch init")
            return 0
        for name in profiles:
            marker = "* " if name == active else "  "
            print(marker + name)
        return 0

    if args == ["--gui"]:
        return run_gui()

    if len(args) == 2 and args[0] in ("--switch", "-s"):
        switch_name = args[1]
        profiles = discover_profiles()
        if switch_name not in profiles:
            print("claudeswitch: unknown profile '" + switch_name + "'", file=sys.stderr)
            print(
                "Available profiles: " + (", ".join(profiles) if profiles else "(none)"),
                file=sys.stderr,
            )
            return 1
        try:
            activate_profile(switch_name)
            print("Switched to profile: " + switch_name)
            return 0
        except Exception as exc:
            print("claudeswitch: " + str(exc), file=sys.stderr)
            return 1

    _print_unknown_args(args)
    return 1


def run():
    raise SystemExit(main())
