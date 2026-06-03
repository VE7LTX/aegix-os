#!/usr/bin/env python3
"""Aegix first-entry operator TUI."""

from __future__ import annotations

import curses
import os
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path


MAX_OUTPUT_LINES = 200
USE_COLOR = False


@dataclass(frozen=True)
class MenuItem:
    title: str
    description: str
    command: list[str] | None = None
    help_text: str | None = None


HELP_TEXT = """\
Aegix is terminal-first in this preview.

Use this screen as the operator home base. It gives you the main system entry
points without needing to remember commands on first login.

Important paths:
  /aegix                       System root for agent-facing state
  /aegix/notes/obsidian        File-backed AI memory vault
  /aegix/projects              Project workspaces
  /aegix/receipts              Action receipts

Important commands:
  agentctl status --json       Aegix operator status
  codexcli --version           Codex CLI entrypoint
  obsidianctl path --json      Obsidian memory vault path
  systemctl status ollama      Local model service status

Keys:
  Up/Down or j/k               Move
  Enter                        Open selected action
  r                            Refresh selected command
  s                            Exit to shell
  q                            Exit to shell
"""


MENU = [
    MenuItem(
        "Help / Getting Started",
        "Show the first-run map, paths, commands, and keys.",
        help_text=HELP_TEXT,
    ),
    MenuItem(
        "Aegix Status",
        "Inspect the scaffold command registry and operator status.",
        ["agentctl", "status", "--json"],
    ),
    MenuItem(
        "What Can I Do?",
        "List the current Aegix command groups.",
        ["agentctl", "commands", "--json"],
    ),
    MenuItem(
        "Codex CLI",
        "Check the Aegix-managed Codex CLI entrypoint.",
        ["codexcli", "--version"],
    ),
    MenuItem(
        "Obsidian AI Memory",
        "Show the file-backed Obsidian vault used for agent memory.",
        ["obsidianctl", "path", "--json"],
    ),
    MenuItem(
        "Search Memory For Aegix",
        "Search the preview Obsidian vault for the Aegix note.",
        ["obsidianctl", "search", "Aegix", "--json"],
    ),
    MenuItem(
        "Ollama Models Service",
        "Check the local model service used by the preview.",
        ["systemctl", "status", "ollama", "--no-pager", "--plain"],
    ),
    MenuItem(
        "Failed Services",
        "Show failed systemd units. A clean preview should list none.",
        ["systemctl", "--failed", "--no-pager", "--plain"],
    ),
    MenuItem(
        "Aegix Filesystem",
        "List the top-level agent-facing filesystem layout.",
        ["ls", "-la", "/aegix"],
    ),
    MenuItem(
        "Exit To Shell",
        "Leave the TUI and use the normal console.",
        None,
        "Exiting returns you to the operator shell. Run aegixtui to reopen this menu.",
    ),
]


def run_command(command: list[str]) -> str:
    missing = [part for part in command[:1] if shutil.which(part) is None]
    if missing:
        return f"Command not found: {missing[0]}"

    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("SYSTEMD_COLORS", "0")
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."

    output = result.stdout
    if result.stderr.strip():
        output = output + ("\n" if output else "") + result.stderr
    output = output.strip() or f"Command exited with status {result.returncode}."
    lines = output.splitlines()
    if len(lines) > MAX_OUTPUT_LINES:
        lines = lines[:MAX_OUTPUT_LINES] + ["...", "Output truncated."]
    return "\n".join(lines)


def wrap_lines(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines() or [""]:
        if not raw_line:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(raw_line, width=max(10, width), replace_whitespace=False))
    return lines


def draw_box(stdscr: curses.window, y: int, x: int, h: int, w: int, title: str) -> None:
    stdscr.attron(curses.color_pair(2))
    stdscr.border()
    stdscr.attroff(curses.color_pair(2))
    if title and w > 4:
        stdscr.addstr(y, x + 2, f" {title[: max(0, w - 6)]} ", curses.color_pair(3))


def color(pair: int) -> int:
    if not USE_COLOR:
        return curses.A_NORMAL
    return curses.color_pair(pair)


def render(stdscr: curses.window, selected: int, output: str) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    if height < 18 or width < 72:
        stdscr.addstr(0, 0, "Aegix TUI needs at least 72x18. Resize or press q.")
        stdscr.refresh()
        return

    title = " Aegix OS Preview | Operator Home "
    stdscr.addstr(0, 2, title, color(1) | curses.A_BOLD | curses.A_REVERSE)
    stdscr.addstr(1, 2, "Agent-first console + TUI. Choose an action or press q for shell.")

    left_w = min(34, max(28, width // 3))
    right_x = left_w + 2
    right_w = width - right_x - 1
    body_h = height - 5

    for i, item in enumerate(MENU):
        y = 3 + i
        if y >= height - 2:
            break
        marker = ">" if i == selected else " "
        text = f"{marker} {item.title}"
        attr = color(1) | curses.A_BOLD | curses.A_REVERSE if i == selected else color(3)
        stdscr.addstr(y, 2, text[: left_w - 3].ljust(left_w - 3), attr)

    item = MENU[selected]
    stdscr.addstr(3, right_x, item.title[:right_w], color(4) | curses.A_BOLD)
    for idx, line in enumerate(wrap_lines(item.description, right_w)):
        if 5 + idx >= height - 2:
            break
        stdscr.addstr(5 + idx, right_x, line[:right_w])

    if item.command:
        command_text = " ".join(item.command)
    elif item.title == "Exit To Shell":
        command_text = "exit to shell"
    else:
        command_text = "help screen"
    command_label = "Command: " + command_text
    stdscr.addstr(7, right_x, command_label[:right_w], color(2))

    output_y = 9
    output_h = body_h - 6
    output_title = "Output"
    stdscr.addstr(output_y - 1, right_x, output_title, color(3) | curses.A_BOLD)
    visible_lines = wrap_lines(output, right_w)
    for idx, line in enumerate(visible_lines[:output_h]):
        stdscr.addstr(output_y + idx, right_x, line[:right_w])

    footer = "Enter: run/open | r: refresh | s/q: shell | Up/Down/j/k: move"
    stdscr.addstr(height - 1, 2, footer[: width - 4], color(2))
    stdscr.refresh()


def initial_output(item: MenuItem) -> str:
    if item.help_text:
        return item.help_text
    if item.command:
        return "Press Enter to run this check."
    return item.help_text or "Press Enter to exit to shell."


def main(stdscr: curses.window) -> int:
    global USE_COLOR
    curses.curs_set(0)
    USE_COLOR = False
    if curses.has_colors() and getattr(curses, "COLORS", 0) >= 8:
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        try:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            USE_COLOR = True
        except curses.error:
            USE_COLOR = False
    stdscr.keypad(True)
    selected = 0
    output = initial_output(MENU[selected])

    while True:
        render(stdscr, selected, output)
        key = stdscr.getch()
        if key in (ord("q"), ord("s"), 27):
            return 0
        if key in (curses.KEY_UP, ord("k")):
            selected = (selected - 1) % len(MENU)
            output = initial_output(MENU[selected])
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = (selected + 1) % len(MENU)
            output = initial_output(MENU[selected])
        elif key in (ord("\n"), curses.KEY_ENTER, 10, 13, ord("r")):
            item = MENU[selected]
            if item.command is None and item.title == "Exit To Shell":
                return 0
            if item.help_text and item.command is None:
                output = item.help_text
            elif item.command:
                output = run_command(item.command)


def entrypoint() -> int:
    if os.environ.get("TERM", "") == "dumb":
        print("Aegix TUI requires an interactive terminal. Run agentctl status --json instead.")
        return 1
    return curses.wrapper(main)


if __name__ == "__main__":
    raise SystemExit(entrypoint())
