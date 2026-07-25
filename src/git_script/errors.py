"""Domain errors with clean, user-facing messages."""

from __future__ import annotations

STATUS_HINTS = {
    401: "invalid or expired token",
    403: "permission denied - check token scopes (needs repo, delete_repo for deletes)",
    404: "not found - missing access or wrong name",
    422: "invalid request",
}


class GithubError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message

    def __str__(self) -> str:
        if self.status and self.status in STATUS_HINTS:
            return f"{self.message} ({STATUS_HINTS[self.status]})"
        return self.message
