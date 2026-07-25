"""GitHub REST API client (stdlib urllib)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from git_script.errors import GithubError
from git_script.models import Repo

# ── constants ─────────────────────────────────────────────────────────

API = "https://api.github.com"


class GithubClient:
    def __init__(self, username: str, token: str) -> None:
        self.username = username
        self.token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"git-script/{self.username}",
        }

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        url = f"{API}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = None
        headers = self._headers()
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                payload = json.loads(raw.decode("utf-8")) if raw else None
                return payload, dict(resp.headers)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(detail).get("message", detail)
            except json.JSONDecodeError:
                msg = detail or str(e)
            raise GithubError(str(msg).strip() or f"HTTP {e.code}", e.code) from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", None) or e
            raise GithubError(f"network error: {reason}") from e
        except TimeoutError as e:
            raise GithubError("request timed out") from e

    def verify(self) -> str:
        data, _ = self._request("GET", "/user")
        login = data.get("login", "")
        if login.lower() != self.username.lower():
            raise GithubError(f"token belongs to '{login}', not '{self.username}'")
        self.username = login
        return login

    def list_repos(self) -> list[Repo]:
        repos: list[Repo] = []
        page = 1
        while True:
            data, headers = self._request(
                "GET",
                "/user/repos",
                params={
                    "per_page": "100",
                    "page": str(page),
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if not isinstance(data, list) or not data:
                break
            for item in data:
                repos.append(self._to_repo(item))
            link = headers.get("Link") or headers.get("link") or ""
            if 'rel="next"' not in link:
                break
            page += 1
        return repos

    def update_repo(self, full_name: str, **fields: Any) -> Repo:
        data, _ = self._request("PATCH", f"/repos/{full_name}", body=fields)
        return self._to_repo(data)

    def delete_repo(self, full_name: str) -> None:
        self._request("DELETE", f"/repos/{full_name}")

    def _to_repo(self, item: dict[str, Any]) -> Repo:
        return Repo(
            id=item["id"],
            name=item["name"],
            full_name=item["full_name"],
            private=bool(item.get("private")),
            fork=bool(item.get("fork")),
            archived=bool(item.get("archived")),
            html_url=item.get("html_url", ""),
            description=item.get("description"),
            language=item.get("language"),
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            default_branch=item.get("default_branch") or "main",
            visibility=item.get("visibility")
            or ("private" if item.get("private") else "public"),
        )
