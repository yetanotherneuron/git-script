"""Terminal colors and output helpers (less-size style, ANSI / VT)."""

from __future__ import annotations

import getpass
import os
import sys

# ── ANSI ──────────────────────────────────────────────────────────────

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"
_ENABLED = False


def _enable_ansi() -> None:
    global _ENABLED
    if _ENABLED:
        return
    _ENABLED = True
    if os.name != "nt":
        return
    try:
        import ctypes

        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _c(*codes: str, text: str) -> str:
    _enable_ansi()
    if not sys.stdout.isatty():
        return text
    return f"{''.join(codes)}{text}{_RESET}"


def bold(text: str) -> str:
    return _c(_BOLD, text=text)


def dim(text: str) -> str:
    return _c(_DIM, text=text)


def cyan(text: str) -> str:
    return _c(_CYAN, text=text)


def green(text: str) -> str:
    return _c(_GREEN, text=text)


def red(text: str) -> str:
    return _c(_RED, text=text)


def yellow(text: str) -> str:
    return _c(_YELLOW, text=text)


def cyan_bold(text: str) -> str:
    return _c(_CYAN, _BOLD, text=text)


def green_bold(text: str) -> str:
    return _c(_GREEN, _BOLD, text=text)


# ── screen ────────────────────────────────────────────────────────────

def clear_screen() -> None:
    _enable_ansi()
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def blank() -> None:
    print()


# ── output helpers ────────────────────────────────────────────────────

def banner(name: str, tagline: str = "") -> None:
    print(bold(name))
    if tagline:
        print(dim(tagline))
    print()


def ok(msg: str) -> None:
    print(f"  {green_bold('ok')}   {msg}")


def info(msg: str) -> None:
    print(f"       {dim(msg)}" if msg else "")


def warn(msg: str) -> None:
    print(f"  {_c(_YELLOW, _BOLD, text='!')}    {msg}")


def err(msg: str) -> None:
    print(f"  {_c(_RED, _BOLD, text='err')}  {msg}", file=sys.stderr)


def bye() -> None:
    print(dim("bye"))


def cancelled() -> None:
    print(dim("cancelled"))


def title(message: str) -> None:
    print()
    print(f"  {cyan_bold(message)}")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    label = f"{green('?')} {bold(prompt)}{dim(suffix)}"
    try:
        value = input(f"{label}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0) from None
    if not value and default is not None:
        return default
    return value


def ask_secret(prompt: str, *, hidden: bool = False) -> str:
    """Visible by default so paste works on Windows."""
    label = f"{green('?')} {bold(prompt)}"
    try:
        if hidden:
            return getpass.getpass(f"{label}: ").strip()
        return input(f"{label} {dim('(paste ok, visible)')}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0) from None


def pause(msg: str = "press enter...") -> None:
    ask(msg, "")


# Back-compat alias used by older call sites
def clear() -> None:
    clear_screen()
