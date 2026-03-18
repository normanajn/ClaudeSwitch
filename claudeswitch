#!/usr/bin/env python3
"""
claudeswitch — manage Claude Code settings profiles.

Usage:
  claudeswitch                    Launch interactive TUI (curses)
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

CLAUDE_DIR    = Path.home() / ".claude"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
STATE_FILE    = CLAUDE_DIR / ".claudeswitch"


# ═══════════════════════════════════════════════════════════════════════════════
#  Data layer
# ═══════════════════════════════════════════════════════════════════════════════

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
        bd = CLAUDE_DIR / "backups"
        bd.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(SETTINGS_FILE, bd / ("settings_" + ts + ".json"))


def activate_profile(name):
    src = profile_path(name)
    if not src.exists():
        raise FileNotFoundError("Profile file not found: " + str(src))
    backup_settings()
    shutil.copy(src, SETTINGS_FILE)
    STATE_FILE.write_text(name)


def read_env(name):
    p = profile_path(name)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text()).get("env", {})
    except (json.JSONDecodeError, OSError):
        return {}


def write_env(name, env):
    p = profile_path(name)
    base = {}
    if p.exists():
        try:
            data = json.loads(p.read_text())
            base = {k: v for k, v in data.items() if k != "env"}
        except (json.JSONDecodeError, OSError):
            pass
    base["env"] = {k: v for k, v in env.items() if v}
    p.write_text(json.dumps(base, indent=2) + "\n")


def do_init():
    CLAUDE_DIR.mkdir(exist_ok=True)
    (CLAUDE_DIR / "backups").mkdir(exist_ok=True)
    p = profile_path("login")
    if not p.exists():
        p.write_text("{}\n")


def fields_for(name, env):
    """
    Return field-spec list for a profile type, or None for login.
    Each spec: {key, label, default, secret (bool), optional (bool)}
    """
    def f(key, label, default="", secret=False, optional=False):
        return dict(key=key, label=label,
                    default=env.get(key, default),
                    secret=secret, optional=optional)

    if name == "login":
        return None

    if name == "asksage":
        return [
            f("ANTHROPIC_API_KEY", "API Key", secret=True),
            f("ANTHROPIC_BASE_URL", "Base URL",
              "https://api.asksage.ai/server/user-anthropic-proxy"),
            f("ASKSAGE_TOKEN", "AskSage Token", secret=True, optional=True),
        ]

    if name == "litellm":
        return [
            f("ANTHROPIC_API_KEY", "API Key", secret=True),
            f("ANTHROPIC_BASE_URL", "LiteLLM Proxy URL", "http://localhost:4000"),
        ]

    if name == "azure":
        return [
            f("ANTHROPIC_API_KEY",     "Azure API Key", secret=True),
            f("ANTHROPIC_BASE_URL",    "Azure Endpoint URL",
              "https://<resource>.openai.azure.com"),
            f("AZURE_API_VERSION",     "API Version",     "2024-02-01"),
            f("AZURE_DEPLOYMENT_NAME", "Deployment Name", "claude-3-5-sonnet"),
        ]

    return [
        f("ANTHROPIC_API_KEY",  "API Key",  secret=True),
        f("ANTHROPIC_BASE_URL", "Base URL", "https://api.anthropic.com"),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
#  Curses TUI
# ═══════════════════════════════════════════════════════════════════════════════

def run_tui():
    curses.wrapper(_tui_main)


CP_HEADER   = 1
CP_SEL      = 2
CP_ACTIVE   = 3
CP_FOOTER   = 4
CP_FIELD_ON = 5
CP_FIELD_OFF= 6
CP_BORDER   = 7
CP_DIM      = 8


def _init_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_HEADER,    curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(CP_SEL,       curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(CP_ACTIVE,    curses.COLOR_GREEN, -1)
    curses.init_pair(CP_FOOTER,    curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_FIELD_ON,  curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(CP_FIELD_OFF, curses.COLOR_WHITE, -1)
    curses.init_pair(CP_BORDER,    curses.COLOR_CYAN,  -1)
    curses.init_pair(CP_DIM,       curses.COLOR_WHITE, -1)


def _inline_edit(win, y, x, width, initial="", secret=False):
    """Single-line text editor. Returns new string or None on Esc."""
    buf  = list(initial)
    cpos = len(buf)
    off  = 0
    vw   = width - 1
    curses.curs_set(1)

    def repaint():
        nonlocal off
        if cpos - off >= vw:
            off = cpos - vw + 1
        if cpos < off:
            off = cpos
        seg     = buf[off:off + vw]
        display = ("●" * len(seg)) if secret else "".join(seg)
        try:
            win.addstr(y, x, display.ljust(vw)[:vw],
                       curses.color_pair(CP_FIELD_ON))
            win.move(y, x + cpos - off)
        except curses.error:
            pass
        win.refresh()

    repaint()
    while True:
        ch = win.getch()
        if ch in (curses.KEY_ENTER, 10, 13):
            break
        elif ch == 27:
            curses.curs_set(0)
            return None
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if cpos > 0:
                del buf[cpos - 1]; cpos -= 1
        elif ch == curses.KEY_DC:
            if cpos < len(buf): del buf[cpos]
        elif ch == curses.KEY_LEFT:
            cpos = max(0, cpos - 1)
        elif ch == curses.KEY_RIGHT:
            cpos = min(len(buf), cpos + 1)
        elif ch == 1:   cpos = 0           # Ctrl-A
        elif ch == 5:   cpos = len(buf)    # Ctrl-E
        elif ch == 11:  del buf[cpos:]     # Ctrl-K
        elif 32 <= ch <= 126:
            buf.insert(cpos, chr(ch)); cpos += 1
        repaint()

    curses.curs_set(0)
    return "".join(buf)


def _make_popup(stdscr, title, lines, extra=0):
    h, w   = stdscr.getmaxyx()
    inner  = max(len(title), max((len(l) for l in lines), default=0)) + 4
    box_w  = min(max(inner, 36) + 4, w - 4)
    box_h  = min(len(lines) + 4 + extra, h - 4)
    pop    = curses.newwin(box_h, box_w,
                           (h - box_h) // 2, (w - box_w) // 2)
    pop.attron(curses.color_pair(CP_BORDER))
    pop.box()
    pop.attroff(curses.color_pair(CP_BORDER))
    pop.addstr(0, (box_w - len(title) - 2) // 2, " " + title + " ",
               curses.A_BOLD)
    for i, line in enumerate(lines[:box_h - 4]):
        try:
            pop.addstr(i + 2, 3, line[:box_w - 6])
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
        pop.addstr(box_h - 2, (box_w - len(hint)) // 2, hint,
                   curses.color_pair(CP_DIM) | curses.A_DIM)
    except curses.error:
        pass
    if success:
        try:
            pop.addstr(0, (box_w - len(title) - 2) // 2, " " + title + " ",
                       curses.color_pair(CP_ACTIVE) | curses.A_BOLD)
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
            _dismiss(pop, stdscr); return True
        if ch in (ord("n"), ord("N"), 27):
            _dismiss(pop, stdscr); return False


def _configure_form(stdscr, title, fields):
    """Multi-field form. Returns {key: value} or None."""
    h, w     = stdscr.getmaxyx()
    lbl_w    = max(len(f["label"]) for f in fields) + 10
    input_w  = min(45, w - lbl_w - 10)
    box_w    = min(lbl_w + input_w + 8, w - 4)
    input_w  = box_w - lbl_w - 8
    box_h    = min(len(fields) * 2 + 6, h - 4)
    by       = (h - box_h) // 2
    bx       = (w - box_w) // 2
    values   = {f["key"]: f.get("default", "") for f in fields}
    cur      = 0

    while True:
        pop = curses.newwin(box_h, box_w, by, bx)
        pop.attron(curses.color_pair(CP_BORDER))
        pop.box()
        pop.attroff(curses.color_pair(CP_BORDER))
        pop.addstr(0, (box_w - len(title) - 2) // 2,
                   " " + title + " ", curses.A_BOLD)

        vis = min(len(fields), (box_h - 6) // 2)
        for i in range(vis):
            field  = fields[i]
            row    = i * 2 + 2
            is_cur = (i == cur)
            tag    = " (opt)" if field.get("optional") else ""
            lbl    = field["label"] + tag + ":"
            attr   = curses.color_pair(CP_SEL) | curses.A_BOLD if is_cur else 0
            try:
                pop.addstr(row, 2, lbl.ljust(lbl_w), attr)
            except curses.error:
                pass
            val     = values[field["key"]]
            display = "●" * len(val) if field.get("secret") else val
            display = display[-input_w:] if len(display) > input_w else display
            iattr   = (curses.color_pair(CP_FIELD_ON) if is_cur
                       else curses.color_pair(CP_FIELD_OFF) | curses.A_DIM)
            try:
                pop.addstr(row, lbl_w + 2,
                           display.ljust(input_w)[:input_w], iattr)
            except curses.error:
                pass

        hint = "↑↓/Tab move  Enter edit  s save  Esc cancel"
        try:
            pop.addstr(box_h - 2,
                       max(0, (box_w - len(hint)) // 2),
                       hint[:box_w - 2],
                       curses.color_pair(CP_DIM) | curses.A_DIM)
        except curses.error:
            pass
        pop.refresh()

        ch = pop.getch()

        if ch == 27:
            _dismiss(pop, stdscr); return None

        elif ch in (ord("s"), ord("S")):
            missing = [f["label"] for f in fields
                       if not f.get("optional") and not values[f["key"]]]
            _dismiss(pop, stdscr)
            if missing:
                _popup_message(stdscr, "Required",
                               ["These fields are required:"] +
                               ["  \u2022 " + m for m in missing])
                continue
            return values

        elif ch == curses.KEY_UP:
            cur = (cur - 1) % len(fields)
            _dismiss(pop, stdscr)

        elif ch in (curses.KEY_DOWN, 9):
            cur = (cur + 1) % len(fields)
            _dismiss(pop, stdscr)

        elif ch in (curses.KEY_ENTER, 10, 13):
            field = fields[cur]
            row   = cur * 2 + 2
            if row < box_h - 2:
                result = _inline_edit(pop, row, lbl_w + 2, input_w,
                                      values[field["key"]],
                                      field.get("secret", False))
                if result is not None:
                    values[field["key"]] = result
            _dismiss(pop, stdscr)

        else:
            _dismiss(pop, stdscr)


def _tui_do_configure(stdscr, name):
    env    = read_env(name)
    spec   = fields_for(name, env)
    if spec is None:
        p = profile_path(name)
        if not p.exists():
            p.write_text("{}\n")
        _popup_message(stdscr, "Login Profile",
                       ["Login mode uses your Anthropic subscription.",
                        "No API key is needed.",
                        "", "Profile is ready to use."],
                       success=True)
        return
    result = _configure_form(stdscr, "Configure: " + name, spec)
    if result is None:
        return
    write_env(name, result)
    _popup_message(stdscr, "Saved",
                   ["Profile '" + name + "' saved.", "",
                    "File: " + str(profile_path(name))],
                   success=True)


def _tui_new_profile(stdscr):
    h, w  = stdscr.getmaxyx()
    box_h = 7
    box_w = min(52, w - 4)
    pop   = curses.newwin(box_h, box_w,
                          (h - box_h) // 2, (w - box_w) // 2)
    pop.attron(curses.color_pair(CP_BORDER))
    pop.box()
    pop.attroff(curses.color_pair(CP_BORDER))
    pop.addstr(0, (box_w - 15) // 2, " New Profile ", curses.A_BOLD)
    pop.addstr(2, 3, "Name: ")
    pop.addstr(5, 3, "Enter confirm   Esc cancel",
               curses.color_pair(CP_DIM) | curses.A_DIM)
    pop.refresh()
    raw = _inline_edit(pop, 2, 9, box_w - 12)
    _dismiss(pop, stdscr)
    if not raw:
        return None
    name = raw.strip().lower().replace(" ", "-")
    if not name:
        return None
    p = profile_path(name)
    if p.exists():
        _popup_message(stdscr, "Error",
                       ["Profile '" + name + "' already exists."])
        return None
    p.write_text("{}\n")
    return name


_FOOTER = ("  \u2191\u2193 Navigate"
           "   [Enter] Switch"
           "   q Quit"
           "   m More  ")

_FOOTER_MORE = ("  c Configure"
                "   n New"
                "   d Delete"
                "   i Init"
                "   < Back  ")


def _draw_main(stdscr, profiles, sel, active, msg, footer=_FOOTER):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header  = "  ClaudeSwitch \u2014 Profile Manager"
    cur_tag = "  current: " + active + "  "
    stdscr.attron(curses.color_pair(CP_HEADER) | curses.A_BOLD)
    stdscr.addstr(0, 0, (header + cur_tag.rjust(w - len(header)))[:w])
    stdscr.attroff(curses.color_pair(CP_HEADER) | curses.A_BOLD)

    col_s = 22
    col_f = col_s + 10
    try:
        stdscr.addstr(2, 2,
                      "PROFILE".ljust(col_s - 2) + "STATUS    FILE",
                      curses.A_BOLD | curses.A_UNDERLINE)
    except curses.error:
        pass

    has_login = "login" in profiles
    for i, name in enumerate(profiles):
        sep_offset = 1 if (has_login and i > 0) else 0
        row = i + 3 + sep_offset
        if row >= h - 3:
            break

        if has_login and i == 1:
            try:
                stdscr.addstr(row - 1, 2, "\u2500" * (w - 4),
                              curses.color_pair(CP_DIM) | curses.A_DIM)
            except curses.error:
                pass

        is_sel    = (i == sel)
        is_active = (name == active)
        fp        = str(profile_path(name)).replace(str(Path.home()), "~")
        avail     = max(1, w - col_f - 2)
        if len(fp) > avail:
            fp = "\u2026" + fp[-(avail - 1):]

        if is_sel:
            line = (" \u25b6 " + name.ljust(col_s - 2) +
                    ("ACTIVE" if is_active else "ready").ljust(10) + fp)
            stdscr.attron(curses.color_pair(CP_SEL) | curses.A_BOLD)
            try:
                stdscr.addstr(row, 0, line.ljust(w)[:w])
            except curses.error:
                pass
            stdscr.attroff(curses.color_pair(CP_SEL) | curses.A_BOLD)
        else:
            try:
                stdscr.addstr(row, 2, "  " + name.ljust(col_s - 2))
            except curses.error:
                pass
            stat_attr = (curses.color_pair(CP_ACTIVE) | curses.A_BOLD
                         if is_active else curses.A_DIM)
            try:
                stdscr.addstr(row, col_s,
                              ("ACTIVE    " if is_active else "ready     "),
                              stat_attr)
                stdscr.addstr(row, col_f, fp[:avail])
            except curses.error:
                pass

    if not profiles:
        try:
            stdscr.addstr(4, 4,
                          "No profiles found in " + str(CLAUDE_DIR),
                          curses.A_DIM)
            stdscr.addstr(5, 4,
                          "Press i to initialise defaults, or n to create one.",
                          curses.A_DIM)
        except curses.error:
            pass

    if msg:
        try:
            stdscr.addstr(h - 3, 2, msg[:w - 4],
                          curses.color_pair(CP_ACTIVE) | curses.A_BOLD)
        except curses.error:
            pass

    stdscr.attron(curses.color_pair(CP_FOOTER))
    try:
        stdscr.addstr(h - 2, 0, footer.ljust(w)[:w])
    except curses.error:
        pass
    stdscr.attroff(curses.color_pair(CP_FOOTER))
    stdscr.refresh()


def _tui_main(stdscr):
    _init_colors()
    curses.curs_set(0)
    CLAUDE_DIR.mkdir(exist_ok=True)

    profiles = discover_profiles()
    sel      = 0
    active   = current_profile()
    msg      = ""
    mode     = "main"

    while True:
        if profiles and sel >= len(profiles):
            sel = len(profiles) - 1
        if sel < 0:
            sel = 0

        footer = _FOOTER_MORE if mode == "more" else _FOOTER
        _draw_main(stdscr, profiles, sel, active, msg, footer)
        msg = ""
        ch  = stdscr.getch()

        if ch in (ord("q"), ord("Q")):
            break
        elif ch in (ord("<"), ord(",")):
            mode = "main"
        elif ch in (ord("m"), ord("M")):
            mode = "more"
        elif ch == curses.KEY_UP:
            if profiles: sel = (sel - 1) % len(profiles)
        elif ch == curses.KEY_DOWN:
            if profiles: sel = (sel + 1) % len(profiles)
        elif ch == curses.KEY_HOME:
            sel = 0
        elif ch == curses.KEY_END:
            sel = max(0, len(profiles) - 1)
        elif ch in (curses.KEY_ENTER, 10, 13):
            if profiles:
                name = profiles[sel]
                if name == active:
                    msg = "'" + name + "' is already the active profile."
                else:
                    try:
                        activate_profile(name)
                        active = name
                        msg    = "Switched to: " + name
                    except Exception as e:
                        _popup_message(stdscr, "Error", [str(e)])
        elif ch in (ord("c"), ord("C")):
            if mode == "more" and profiles:
                _tui_do_configure(stdscr, profiles[sel])
                profiles = discover_profiles()
        elif ch in (ord("n"), ord("N")):
            if mode == "more":
                new_name = _tui_new_profile(stdscr)
                if new_name:
                    profiles = discover_profiles()
                    try:
                        sel = profiles.index(new_name)
                    except ValueError:
                        pass
                    msg = "Created '" + new_name + "'. Press c to configure."
        elif ch in (ord("d"), ord("D")):
            if mode == "more" and profiles:
                name = profiles[sel]
                if name == active:
                    _popup_message(stdscr, "Cannot Delete",
                                   ["Cannot delete the active profile.",
                                    "Switch to another profile first."])
                elif _popup_confirm(stdscr, "Confirm Delete",
                                    "Delete profile '" + name + "'?\n" +
                                    str(profile_path(name))):
                    try:
                        profile_path(name).unlink()
                    except OSError:
                        pass
                    profiles = discover_profiles()
                    sel = min(sel, max(0, len(profiles) - 1))
                    msg = "Deleted profile '" + name + "'."
        elif ch in (ord("i"), ord("I")):
            if mode == "more":
                do_init()
                profiles = discover_profiles()
                active   = current_profile()
                msg      = "Initialised default profiles."
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()


# ═══════════════════════════════════════════════════════════════════════════════
#  Qt GUI
# ═══════════════════════════════════════════════════════════════════════════════

def _import_qt():
    """Try PySide6 then PyQt5. Returns the QtWidgets module or raises."""
    try:
        import PySide6.QtWidgets as _w
        return "pyside6"
    except ImportError:
        pass
    try:
        import PyQt5.QtWidgets as _w  # noqa: F401
        return "pyqt5"
    except ImportError:
        pass
    return None


def run_gui():
    binding = _import_qt()
    if binding is None:
        print("claudeswitch --gui requires PySide6 or PyQt5.", file=sys.stderr)
        print("Install one:  pip install PySide6   or   pip install PyQt5",
              file=sys.stderr)
        sys.exit(1)

    if binding == "pyside6":
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QSplitter,
            QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
            QPushButton, QListWidget, QListWidgetItem, QTextEdit,
            QLineEdit, QScrollArea, QGroupBox, QMessageBox,
            QFileDialog, QInputDialog,
        )
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QAction, QFont, QKeySequence, QColor
    else:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QSplitter,
            QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
            QPushButton, QListWidget, QListWidgetItem, QTextEdit,
            QLineEdit, QScrollArea, QGroupBox, QMessageBox,
            QFileDialog, QInputDialog, QAction,
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QKeySequence, QColor

    # ── Main window ───────────────────────────────────────────────────────────

    class ClaudeSwitchWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("ClaudeSwitch")
            self.resize(1000, 650)
            self._selected = None     # currently selected profile name
            self._form_fields  = []   # list of field specs
            self._form_widgets = {}   # key -> QLineEdit
            self._setup_ui()
            self._setup_menu()
            self._refresh()

        # ── UI construction ───────────────────────────────────────────────────

        def _setup_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            root = QHBoxLayout(central)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            main_split = QSplitter(Qt.Horizontal)
            root.addWidget(main_split)

            # ── Left panel: profile list ──────────────────────────────────────
            left = QWidget()
            left.setMinimumWidth(180)
            ll = QVBoxLayout(left)
            ll.setContentsMargins(10, 10, 6, 10)

            hdr = QLabel("Profiles")
            hdr.setStyleSheet(
                "font-weight: bold; font-size: 15px; padding-bottom: 4px;")
            ll.addWidget(hdr)

            self.profile_list = QListWidget()
            self.profile_list.setAlternatingRowColors(True)
            self.profile_list.currentRowChanged.connect(
                self._on_selection_changed)
            self.profile_list.itemDoubleClicked.connect(self._cmd_switch)
            ll.addWidget(self.profile_list)

            btn_switch = QPushButton("▶  Switch to Selected")
            btn_switch.clicked.connect(self._cmd_switch)
            ll.addWidget(btn_switch)

            main_split.addWidget(left)
            main_split.setStretchFactor(0, 1)

            # ── Right panel: JSON viewer + form editor ────────────────────────
            right_split = QSplitter(Qt.Vertical)

            # JSON viewer
            json_box = QGroupBox("Settings JSON  (live preview)")
            jl = QVBoxLayout(json_box)
            self.json_view = QTextEdit()
            self.json_view.setReadOnly(True)
            mono = QFont("Courier New", 10)
            mono.setStyleHint(QFont.Monospace)
            self.json_view.setFont(mono)
            self.json_view.setStyleSheet(
                "background:#1e1e1e; color:#d4d4d4; border:none;")
            jl.addWidget(self.json_view)
            right_split.addWidget(json_box)

            # Form editor
            form_box = QGroupBox("Configuration")
            form_outer = QVBoxLayout(form_box)

            self.form_scroll = QScrollArea()
            self.form_scroll.setWidgetResizable(True)
            self.form_container = QWidget()
            self.form_layout = QFormLayout(self.form_container)
            self.form_layout.setFieldGrowthPolicy(
                QFormLayout.AllNonFixedFieldsGrow)
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
            mb = self.menuBar()

            # File
            fm = mb.addMenu("&File")
            a = QAction("&Save Profile", self)
            a.setShortcut(QKeySequence.Save)
            a.triggered.connect(self._cmd_save)
            fm.addAction(a)

            a = QAction("&Load Config from File…", self)
            a.triggered.connect(self._cmd_load_from_file)
            fm.addAction(a)

            a = QAction("&Export Profile to File…", self)
            a.triggered.connect(self._cmd_export_to_file)
            fm.addAction(a)

            fm.addSeparator()

            a = QAction("E&xit", self)
            a.setShortcut(QKeySequence.Quit)
            a.triggered.connect(self.close)
            fm.addAction(a)

            # Profile
            pm = mb.addMenu("&Profile")
            a = QAction("&Switch to Selected", self)
            a.triggered.connect(self._cmd_switch)
            pm.addAction(a)

            a = QAction("&New Profile…", self)
            a.triggered.connect(self._cmd_new)
            pm.addAction(a)

            a = QAction("&Delete Profile", self)
            a.triggered.connect(self._cmd_delete)
            pm.addAction(a)

            pm.addSeparator()

            a = QAction("&Initialize Defaults", self)
            a.triggered.connect(self._cmd_init)
            pm.addAction(a)

            # Help
            hm = mb.addMenu("&Help")
            a = QAction("&About", self)
            a.triggered.connect(self._cmd_about)
            hm.addAction(a)

        # ── Refresh / populate ────────────────────────────────────────────────

        def _refresh(self):
            profiles = discover_profiles()
            active   = current_profile()
            prev_sel = self._selected

            self.profile_list.blockSignals(True)
            self.profile_list.clear()
            for name in profiles:
                is_active = (name == active)
                item = QListWidgetItem(
                    ("▶  " + name + "  [ACTIVE]") if is_active
                    else ("    " + name))
                item.setData(Qt.UserRole, name)
                if is_active:
                    item.setForeground(QColor("#00bb44"))
                    fnt = item.font()
                    fnt.setBold(True)
                    item.setFont(fnt)
                self.profile_list.addItem(item)
            self.profile_list.blockSignals(False)

            # Restore selection
            if prev_sel:
                for i in range(self.profile_list.count()):
                    if self.profile_list.item(i).data(Qt.UserRole) == prev_sel:
                        self.profile_list.setCurrentRow(i)
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
            p = profile_path(name)
            if p.exists():
                try:
                    self.json_view.setPlainText(p.read_text())
                except OSError as e:
                    self.json_view.setPlainText("# Error reading file:\n# " + str(e))
            else:
                self.json_view.setPlainText("# Profile file not yet created.\n{}")

        def _clear_form(self):
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
            self._form_widgets = {}
            self._form_fields  = []

        def _rebuild_form(self, name):
            self._clear_form()
            env    = read_env(name)
            fields = fields_for(name, env)

            if fields is None:
                lbl = QLabel(
                    "Login profile — no API configuration needed.\n"
                    "Uses your Anthropic subscription directly.\n\n"
                    "The profile file is ready to activate.")
                lbl.setWordWrap(True)
                self.form_layout.addRow(lbl)
                return

            self._form_fields = fields
            for field in fields:
                key      = field["key"]
                label    = field["label"]
                default  = field.get("default", "")
                secret   = field.get("secret", False)
                optional = field.get("optional", False)
                row_lbl  = label + (" (optional)" if optional else "") + ":"

                le = QLineEdit(default)
                le.setMinimumWidth(300)
                if secret:
                    le.setEchoMode(QLineEdit.Password)
                    le.setPlaceholderText("(unchanged)" if default else "")

                    container = QWidget()
                    hl = QHBoxLayout(container)
                    hl.setContentsMargins(0, 0, 0, 0)
                    hl.addWidget(le)

                    toggle = QPushButton("Show")
                    toggle.setFixedWidth(52)
                    toggle.setCheckable(True)
                    toggle.toggled.connect(
                        self._make_toggle(le, toggle))
                    hl.addWidget(toggle)
                    self.form_layout.addRow(row_lbl, container)
                else:
                    self.form_layout.addRow(row_lbl, le)

                le.textChanged.connect(self._on_field_changed)
                self._form_widgets[key] = le

        @staticmethod
        def _make_toggle(line_edit, button):
            def _toggle(checked):
                line_edit.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password)
                button.setText("Hide" if checked else "Show")
            return _toggle

        def _on_field_changed(self):
            """Live-update the JSON preview as the user edits fields."""
            if not self._selected or not self._form_fields:
                return
            env = {f["key"]: self._form_widgets[f["key"]].text()
                   for f in self._form_fields}
            p    = profile_path(self._selected)
            base = {}
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                    base = {k: v for k, v in data.items() if k != "env"}
                except (json.JSONDecodeError, OSError):
                    pass
            base["env"] = {k: v for k, v in env.items() if v}
            self.json_view.setPlainText(json.dumps(base, indent=2))

        # ── Commands ──────────────────────────────────────────────────────────

        def _cmd_switch(self, *_):
            if not self._selected:
                QMessageBox.information(self, "No Selection",
                                        "Select a profile to switch to.")
                return
            name = self._selected
            if name == current_profile():
                QMessageBox.information(self, "Already Active",
                                        "'" + name + "' is already active.")
                return
            try:
                activate_profile(name)
                self._refresh()
                self.statusBar().showMessage("Switched to: " + name)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

        def _cmd_save(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection",
                                        "Select a profile first.")
                return
            name = self._selected
            if not self._form_fields:
                # Login profile — just ensure file exists
                p = profile_path(name)
                if not p.exists():
                    p.write_text("{}\n")
                self.statusBar().showMessage("Profile '" + name + "' is ready.")
                return
            env = {f["key"]: self._form_widgets[f["key"]].text()
                   for f in self._form_fields}
            missing = [f["label"] for f in self._form_fields
                       if not f.get("optional") and not env[f["key"]]]
            if missing:
                QMessageBox.warning(
                    self, "Required Fields",
                    "These fields are required:\n" +
                    "\n".join("  \u2022 " + m for m in missing))
                return
            write_env(name, env)
            self._refresh_json_view(name)
            self.statusBar().showMessage("Saved profile '" + name + "'.")

        def _cmd_load_from_file(self):
            path, _ = QFileDialog.getOpenFileName(
                self, "Load Config File", str(Path.home()),
                "JSON Files (*.json);;All Files (*)")
            if not path:
                return
            # Suggest a name from the filename
            stem = Path(path).stem
            if stem.startswith("settings-"):
                stem = stem[len("settings-"):]
            name, ok = QInputDialog.getText(
                self, "Profile Name",
                "Save as profile name:", text=stem)
            if not ok or not name:
                return
            name = name.strip().lower().replace(" ", "-")
            if not name:
                return
            dest = profile_path(name)
            if dest.exists():
                r = QMessageBox.question(
                    self, "Overwrite?",
                    "Profile '" + name + "' already exists. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No)
                if r != QMessageBox.Yes:
                    return
            try:
                shutil.copy(path, dest)
            except OSError as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self._refresh()
            # Select the loaded profile
            for i in range(self.profile_list.count()):
                if self.profile_list.item(i).data(Qt.UserRole) == name:
                    self.profile_list.setCurrentRow(i)
                    break
            self.statusBar().showMessage(
                "Loaded '" + name + "' from " + path)

        def _cmd_export_to_file(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection",
                                        "Select a profile to export.")
                return
            name    = self._selected
            default = str(Path.home() / ("settings-" + name + ".json"))
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Profile", default,
                "JSON Files (*.json);;All Files (*)")
            if not path:
                return
            try:
                shutil.copy(profile_path(name), path)
            except OSError as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.statusBar().showMessage(
                "Exported '" + name + "' to " + path)

        def _cmd_new(self):
            name, ok = QInputDialog.getText(
                self, "New Profile", "Profile name:")
            if not ok or not name:
                return
            name = name.strip().lower().replace(" ", "-")
            if not name:
                return
            p = profile_path(name)
            if p.exists():
                QMessageBox.warning(self, "Exists",
                                    "Profile '" + name + "' already exists.")
                return
            p.write_text("{}\n")
            self._refresh()
            for i in range(self.profile_list.count()):
                if self.profile_list.item(i).data(Qt.UserRole) == name:
                    self.profile_list.setCurrentRow(i)
                    break

        def _cmd_delete(self):
            if not self._selected:
                QMessageBox.information(self, "No Selection",
                                        "Select a profile to delete.")
                return
            name = self._selected
            if name == current_profile():
                QMessageBox.warning(
                    self, "Cannot Delete",
                    "Cannot delete the active profile.\n"
                    "Switch to another profile first.")
                return
            r = QMessageBox.question(
                self, "Confirm Delete",
                "Delete profile '" + name + "'?\n" + str(profile_path(name)),
                QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
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
                self, "About ClaudeSwitch",
                "<b>ClaudeSwitch</b><br>"
                "Manage Claude Code settings profiles.<br><br>"
                "Profiles are stored in:<br>"
                "<tt>~/.claude/settings-&lt;name&gt;.json</tt><br><br>"
                "The active profile is copied to:<br>"
                "<tt>~/.claude/settings.json</tt>")

    # ── Launch ────────────────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("ClaudeSwitch")
    win = ClaudeSwitchWindow()
    win.show()
    sys.exit(app.exec() if binding == "pyside6" else app.exec_())


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__.strip())
        sys.exit(0)

    if "--list" in args or "-l" in args:
        profiles = discover_profiles()
        active = current_profile()
        if not profiles:
            print("No profiles found. Run: claudeswitch init")
            sys.exit(0)
        for name in profiles:
            marker = "* " if name == active else "  "
            print(marker + name)
        sys.exit(0)

    switch_name = None
    for flag in ("--switch", "-s"):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 >= len(args):
                print("claudeswitch: " + flag + " requires a profile name", file=sys.stderr)
                sys.exit(1)
            switch_name = args[idx + 1]
            break

    if switch_name is not None:
        profiles = discover_profiles()
        if switch_name not in profiles:
            print("claudeswitch: unknown profile '" + switch_name + "'", file=sys.stderr)
            print("Available profiles: " + (", ".join(profiles) if profiles else "(none)"), file=sys.stderr)
            sys.exit(1)
        try:
            activate_profile(switch_name)
            print("Switched to profile: " + switch_name)
        except Exception as e:
            print("claudeswitch: " + str(e), file=sys.stderr)
            sys.exit(1)
        return

    if "--gui" in args:
        run_gui()
        return

    try:
        import curses
        run_tui()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("claudeswitch: " + str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
