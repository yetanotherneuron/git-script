"""git-script CLI — interactive stdlib arrow menu by default."""

from __future__ import annotations

from git_script.menu import run_menu


def main() -> None:
    """Open the interactive menu."""
    run_menu()


if __name__ == "__main__":
    main()
