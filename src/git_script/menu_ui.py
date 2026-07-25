"""Arrow-key terminal menus (stdlib only — not a full-screen TUI)."""

from __future__ import annotations

import os
import sys
from typing import Sequence

from git_script import ui

# ── keys ──────────────────────────────────────────────────────────────

KEY_UP = "up"
KEY_DOWN = "down"
KEY_ENTER = "enter"
KEY_ESC = "esc"
KEY_SPACE = "space"
KEY_QUIT = "quit"


def _read_key_windows() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return {"H": KEY_UP, "P": KEY_DOWN, "K": KEY_UP, "M": KEY_DOWN}.get(ch2, "")
    if ch in ("\r", "\n"):
        return KEY_ENTER
    if ch == "\x1b":
        return KEY_ESC
    if ch == " ":
        return KEY_SPACE
    if ch in ("q", "Q"):
        return KEY_QUIT
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def _read_key_unix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            rest = sys.stdin.read(2)
            if rest == "[A":
                return KEY_UP
            if rest == "[B":
                return KEY_DOWN
            return KEY_ESC
        if ch in ("\r", "\n"):
            return KEY_ENTER
        if ch == " ":
            return KEY_SPACE
        if ch in ("q", "Q"):
            return KEY_QUIT
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key() -> str:
    if os.name == "nt":
        return _read_key_windows()
    return _read_key_unix()


# ── cursor / paint ────────────────────────────────────────────────────

def _move_up(n: int) -> None:
    if n > 0:
        sys.stdout.write(f"\x1b[{n}A")
        sys.stdout.flush()


def _hide_cursor() -> None:
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def _show_cursor() -> None:
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def _paint(
    lines: list[str],
    *,
    first: bool,
    prev_count: int,
) -> int:
    if not first and prev_count:
        _move_up(prev_count)
    for line in lines:
        sys.stdout.write(f"\x1b[2K{line}")
        sys.stdout.write("\n")
    sys.stdout.flush()
    return len(lines)


# ── arrow menus ───────────────────────────────────────────────────────

def menu(
    title: str,
    options: Sequence[tuple[str, str]],
    subtitle: str = "",
    default: str | None = None,
    *,
    clear_on_select: bool = True,
) -> str | None:
    """
    Arrow-key menu. Returns selected option id, or None if cancelled.
    options: (id, label). Empty id = skipped (prefer omitting separators).
    """
    entries: list[tuple[str, str, bool]] = []
    for opt_id, label in options:
        if not opt_id:
            continue
        entries.append((opt_id, label, True))

    selectable_idx = list(range(len(entries)))
    if not selectable_idx:
        return None

    cursor = 0
    if default is not None:
        for ci, (opt_id, _, _) in enumerate(entries):
            if opt_id == default:
                cursor = ci
                break

    print()
    print(f"{ui.green('?')} {ui.bold(title)}")
    if subtitle:
        print(ui.dim(subtitle))
    print()
    print(ui.dim("up/down move · enter select · esc cancel"))
    print()

    _hide_cursor()
    first = True
    prev = 0
    try:
        while True:
            lines: list[str] = []
            for i, (_opt_id, label, _) in enumerate(entries):
                active = i == cursor
                if active:
                    lines.append(f" {ui.cyan_bold('>')} {ui.cyan_bold(label)}")
                else:
                    lines.append(f"   {label}")
            prev = _paint(lines, first=first, prev_count=prev)
            first = False

            key = read_key()
            if key == KEY_UP:
                cursor = (cursor - 1) % len(entries)
            elif key == KEY_DOWN:
                cursor = (cursor + 1) % len(entries)
            elif key == KEY_ENTER:
                chosen = entries[cursor][0]
                _show_cursor()
                if clear_on_select:
                    ui.clear_screen()
                else:
                    print()
                return chosen
            elif key in (KEY_ESC, KEY_QUIT):
                _show_cursor()
                if clear_on_select:
                    ui.clear_screen()
                else:
                    print()
                return None
    except KeyboardInterrupt:
        _show_cursor()
        print()
        raise SystemExit(0) from None
    finally:
        _show_cursor()


def confirm(prompt: str, default: bool = False) -> bool:
    if default:
        options = [("yes", "Yes"), ("no", "No")]
        default_id = "yes"
    else:
        options = [("no", "No"), ("yes", "Yes")]
        default_id = "no"
    choice = menu(prompt, options, default=default_id)
    if choice is None:
        return False
    return choice == "yes"


def pick_index(
    title: str,
    items: Sequence[str],
    multi: bool = False,
    subtitle: str = "",
    window: int = 16,
) -> list[int]:
    """Arrow-key picker. Returns 0-based indices."""
    if not items:
        ui.warn("nothing to show")
        return []

    cursor = 0
    selected: set[int] = set()
    total = len(items)

    print()
    print(f"{ui.green('?')} {ui.bold(title)}")
    if subtitle:
        print(ui.dim(subtitle))
    print()
    if multi:
        print(ui.dim("up/down move · space toggle · enter confirm · esc cancel"))
    else:
        print(ui.dim("up/down move · enter select · esc cancel"))
    print()

    _hide_cursor()
    first = True
    prev = 0
    try:
        while True:
            if total <= window:
                start, end = 0, total
            else:
                start = max(0, min(cursor - window // 2, total - window))
                end = start + window

            lines: list[str] = []
            if start > 0:
                lines.append(ui.dim(f"  … {start} more above"))
            for i in range(start, end):
                label = items[i]
                active = i == cursor
                mark = ui.cyan_bold(">") if active else " "
                if multi:
                    box = ui.cyan("[x]") if i in selected else "[ ]"
                    body = ui.cyan_bold(label) if active else label
                    lines.append(f" {mark} {box} {body}")
                else:
                    body = ui.cyan_bold(label) if active else label
                    lines.append(f" {mark} {body}")
            if end < total:
                lines.append(ui.dim(f"  … {total - end} more below"))

            prev = _paint(lines, first=first, prev_count=prev)
            first = False

            key = read_key()
            if key == KEY_UP:
                cursor = (cursor - 1) % total
            elif key == KEY_DOWN:
                cursor = (cursor + 1) % total
            elif key == KEY_SPACE and multi:
                if cursor in selected:
                    selected.discard(cursor)
                else:
                    selected.add(cursor)
            elif key == KEY_ENTER:
                _show_cursor()
                ui.clear_screen()
                if multi:
                    if selected:
                        return sorted(selected)
                    return [cursor]
                return [cursor]
            elif key in (KEY_ESC, KEY_QUIT):
                _show_cursor()
                ui.clear_screen()
                return []
    except KeyboardInterrupt:
        _show_cursor()
        print()
        raise SystemExit(0) from None
    finally:
        _show_cursor()
