"""Repository data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Repo:
    id: int
    name: str
    full_name: str
    private: bool
    fork: bool
    archived: bool
    html_url: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    default_branch: str
    visibility: str
