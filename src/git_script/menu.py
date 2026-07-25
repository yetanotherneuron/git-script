"""Interactive arrow-key terminal menu for git-script."""

from __future__ import annotations

import os
import webbrowser

from git_script import menu_ui, ui
from git_script.errors import GithubError
from git_script.github_api import GithubClient
from git_script.models import Repo

# ── filters ───────────────────────────────────────────────────────────

FILTERS = ("all", "public", "private", "forks", "sources", "archived")
FILTER_LABELS = {
    "all": "all",
    "public": "public",
    "private": "private",
    "forks": "forks",
    "sources": "sources",
    "archived": "archived",
}


class App:
    def __init__(self) -> None:
        self.client: GithubClient | None = None
        self.repos: list[Repo] = []
        self.filter_mode = "all"
        self.search = ""

    def login(self) -> bool:
        ui.clear_screen()
        ui.banner("git-script", "manage your GitHub repositories")
        username = ui.ask("username")
        token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
        if token:
            ui.info("using token from environment")
        else:
            token = ui.ask_secret("token (repo scope)")
        if not username:
            ui.err("username required")
            return False
        if not token:
            ui.err("token required - paste with Ctrl+V, or set GITHUB_TOKEN")
            return False
        client = GithubClient(username, token)
        try:
            login = client.verify()
        except GithubError as e:
            ui.err(str(e))
            return False
        self.client = client
        ui.ok(f"signed in as {login}")
        return self.refresh()

    def refresh(self) -> bool:
        assert self.client is not None
        ui.info("loading repos...")
        try:
            self.repos = self.client.list_repos()
        except GithubError as e:
            ui.err(str(e))
            return False
        ui.ok(f"loaded {len(self.repos)} repos")
        return True

    def visible(self) -> list[Repo]:
        out: list[Repo] = []
        for repo in self.repos:
            if self.filter_mode == "public" and repo.private:
                continue
            if self.filter_mode == "private" and not repo.private:
                continue
            if self.filter_mode == "forks" and not repo.fork:
                continue
            if self.filter_mode == "sources" and repo.fork:
                continue
            if self.filter_mode == "archived" and not repo.archived:
                continue
            text = self.search.strip().lower()
            if text:
                hay = (
                    f"{repo.name} {repo.full_name} "
                    f"{repo.description or ''} {repo.language or ''}"
                ).lower()
                if text not in hay:
                    continue
            out.append(repo)
        return out

    def _flags(self, repo: Repo) -> str:
        bits = ["private" if repo.private else "public"]
        if repo.fork:
            bits.append("fork")
        if repo.archived:
            bits.append("archived")
        return " | ".join(bits)

    def _line(self, repo: Repo) -> str:
        lang = repo.language or "-"
        return f"{repo.full_name:<40}  {self._flags(repo)} | *{repo.stars} | {lang}"

    def _summary(self) -> str:
        shown = len(self.visible())
        total = len(self.repos)
        parts = [f"{shown}/{total} shown", f"filter: {FILTER_LABELS[self.filter_mode]}"]
        if self.search:
            parts.append(f'search: "{self.search}"')
        return " | ".join(parts)

    def _replace(self, updated: Repo) -> None:
        for i, repo in enumerate(self.repos):
            if repo.id == updated.id:
                self.repos[i] = updated
                return

    def _remove(self, full_names: set[str]) -> None:
        self.repos = [r for r in self.repos if r.full_name not in full_names]

    def _names(self, repos: list[Repo], limit: int = 5) -> str:
        names = [r.full_name for r in repos]
        if len(names) <= limit:
            return ", ".join(names)
        return ", ".join(names[:limit]) + f" (+{len(names) - limit} more)"

    def _report(self, verb: str, ok_count: int, total: int, errors: list[str]) -> None:
        if not errors:
            word = "repo" if ok_count == 1 else "repos"
            ui.ok(f"{verb} {ok_count} {word}")
            return
        ui.err(f"{verb} {ok_count}/{total} | {len(errors)} failed | {errors[0]}")
        for line in errors[1:]:
            ui.err(f"  {line}")

    def run(self) -> None:
        if not self.login():
            return
        while True:
            ui.clear_screen()
            ui.banner("git-script", self._summary())
            choice = menu_ui.menu(
                "What do you want to do?",
                [
                    ("list", "List repos"),
                    ("select", "Select repos → actions"),
                    ("filter", f"Filter  (now: {FILTER_LABELS[self.filter_mode]})"),
                    ("search", f'Search  (now: "{self.search or "-"}")'),
                    ("bulk", "Bulk actions"),
                    ("refresh", "Refresh"),
                    ("quit", "Quit"),
                ],
            )
            if choice in (None, "quit"):
                ui.bye()
                return
            if choice == "list":
                self.cmd_list()
            elif choice == "select":
                self.cmd_select()
            elif choice == "filter":
                self.cmd_filter()
            elif choice == "search":
                self.cmd_search()
            elif choice == "bulk":
                self.cmd_bulk()
            elif choice == "refresh":
                self.refresh()

    def cmd_list(self) -> None:
        repos = self.visible()
        ui.banner("Repositories", self._summary())
        if not repos:
            ui.warn("no repos match")
        else:
            for i, repo in enumerate(repos, 1):
                print(f"  {ui.cyan(f'{i:>3}')}  {ui.bold(repo.full_name)}")
                print(f"       {ui.dim(self._flags(repo))} · *{repo.stars} · {repo.language or '-'}")
                desc = (repo.description or "").strip()
                if desc:
                    if len(desc) > 72:
                        desc = desc[:69] + "..."
                    print(f"       {ui.dim(desc)}")
        print()
        ui.pause()

    def cmd_filter(self) -> None:
        options = [
            (key, f"{'› ' if key == self.filter_mode else '  '}{FILTER_LABELS[key]}")
            for key in FILTERS
        ]
        options.append(("back", "Back"))
        choice = menu_ui.menu(
            "Filter",
            options,
            subtitle=f"current: {FILTER_LABELS[self.filter_mode]}",
        )
        if choice and choice in FILTERS:
            self.filter_mode = choice
            ui.ok(f"filter → {FILTER_LABELS[choice]}")

    def cmd_search(self) -> None:
        value = ui.ask("search text (empty clears)", self.search)
        self.search = value
        if value:
            ui.ok(f'search -> "{value}"')
        else:
            ui.ok("search cleared")

    def cmd_select(self) -> None:
        repos = self.visible()
        if not repos:
            ui.warn("no repos match")
            ui.pause()
            return
        indices = menu_ui.pick_index(
            "Select repos",
            [self._line(r) for r in repos],
            multi=True,
            subtitle=self._summary(),
        )
        if not indices:
            return
        self.action_menu([repos[i] for i in indices])

    def action_menu(self, selected: list[Repo]) -> None:
        n = len(selected)
        subtitle = selected[0].full_name if n == 1 else f"{n} repos"
        all_archived = all(r.archived for r in selected)
        archive_label = "Unarchive" if all_archived else "Archive"
        can_private = any(not r.private for r in selected)
        can_public = any(r.private for r in selected)

        choice = menu_ui.menu(
            "Actions",
            [
                ("archive", archive_label),
                ("private", "Make private"),
                ("public", "Make public"),
                ("rename", "Rename"),
                ("delete", "Delete"),
                ("open", "Open in browser"),
                ("back", "Back"),
            ],
            subtitle=subtitle,
        )
        if choice in (None, "back"):
            return
        if choice == "archive":
            self.do_archive(selected, archive=not all_archived)
        elif choice == "private":
            if not can_private:
                ui.warn("already private")
                return
            self.do_visibility([r for r in selected if not r.private], private=True)
        elif choice == "public":
            if not can_public:
                ui.warn("already public")
                return
            self.do_visibility([r for r in selected if r.private], private=False)
        elif choice == "rename":
            if n != 1:
                ui.warn("rename works on one repo only")
                return
            self.do_rename(selected[0])
        elif choice == "delete":
            self.do_delete(selected)
        elif choice == "open":
            self.do_open(selected)

    def cmd_bulk(self) -> None:
        public_ones = [r for r in self.repos if not r.private]
        private_ones = [r for r in self.repos if r.private]
        forks = [r for r in self.repos if r.fork]
        choice = menu_ui.menu(
            "Bulk actions",
            [
                ("all_private", f"All public → private  ({len(public_ones)})"),
                ("all_public", f"All private → public  ({len(private_ones)})"),
                ("remove_forks", f"Delete all forks     ({len(forks)})"),
                ("back", "Back"),
            ],
        )
        if choice == "all_private":
            if not public_ones:
                ui.warn("no public repos")
                return
            self.do_visibility(public_ones, private=True)
        elif choice == "all_public":
            if not private_ones:
                ui.warn("no private repos")
                return
            self.do_visibility(private_ones, private=False)
        elif choice == "remove_forks":
            if not forks:
                ui.warn("no forks")
                return
            self.do_delete(forks)

    def do_open(self, repos: list[Repo]) -> None:
        opened = 0
        for repo in repos:
            if repo.html_url:
                webbrowser.open(repo.html_url)
                opened += 1
        if opened:
            ui.ok(f"opened {opened}")
        else:
            ui.warn("nothing to open")

    def do_archive(self, repos: list[Repo], archive: bool) -> None:
        assert self.client is not None
        if archive:
            targets = [r for r in repos if not r.archived]
        else:
            targets = [r for r in repos if r.archived]
        if not targets:
            ui.warn("nothing to do")
            return
        verb = "archive" if archive else "unarchive"
        if not menu_ui.confirm(f"{verb} {len(targets)} repo(s)? {self._names(targets)}"):
            return
        ok_count, errors = 0, []
        for repo in targets:
            try:
                updated = self.client.update_repo(repo.full_name, archived=archive)
                self._replace(updated)
                ok_count += 1
            except GithubError as e:
                errors.append(f"{repo.full_name}: {e}")
        self._report("archived" if archive else "unarchived", ok_count, len(targets), errors)

    def do_visibility(self, repos: list[Repo], private: bool) -> None:
        assert self.client is not None
        if not repos:
            ui.warn("nothing to do")
            return
        label = "private" if private else "public"
        if not menu_ui.confirm(f"make {len(repos)} repo(s) {label}? {self._names(repos)}"):
            return
        ok_count, errors = 0, []
        for repo in repos:
            try:
                updated = self.client.update_repo(repo.full_name, private=private)
                self._replace(updated)
                ok_count += 1
            except GithubError as e:
                errors.append(f"{repo.full_name}: {e}")
        self._report(f"made {label}", ok_count, len(repos), errors)

    def do_rename(self, repo: Repo) -> None:
        assert self.client is not None
        name = ui.ask(f"new name for {repo.full_name}", repo.name)
        if not name or name == repo.name:
            ui.info("unchanged")
            return
        try:
            updated = self.client.update_repo(repo.full_name, name=name)
        except GithubError as e:
            ui.err(str(e))
            return
        self._replace(updated)
        ui.ok(f"renamed -> {updated.full_name}")

    def do_delete(self, repos: list[Repo]) -> None:
        assert self.client is not None
        if not menu_ui.confirm(f"DELETE {len(repos)} repo(s) forever? {self._names(repos)}"):
            return
        if not menu_ui.confirm("really sure?"):
            return
        ok_names: list[str] = []
        errors: list[str] = []
        for repo in repos:
            try:
                self.client.delete_repo(repo.full_name)
                ok_names.append(repo.full_name)
            except GithubError as e:
                errors.append(f"{repo.full_name}: {e}")
        self._remove(set(ok_names))
        self._report("deleted", len(ok_names), len(ok_names) + len(errors), errors)


def run_menu() -> None:
    """Arrow-key menu loop. Quit via menu item, Esc, or Ctrl+C."""
    App().run()
