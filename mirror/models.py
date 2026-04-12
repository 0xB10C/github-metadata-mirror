"""Data models for the site index."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EntryMeta:
    """Lightweight metadata for a single issue or PR.

    Extracted during Pass 1 (index building) and kept in memory.
    The full JSON data is re-read from json_path during Pass 2 (rendering).
    """

    number: int
    title: str
    state: str  # open | closed | complete | merged | draft
    is_pr: bool
    contributor: str  # original case (display name)
    avatar_url: str
    labels: list[str]
    date: str  # ISO 8601
    json_path: Path  # path to source JSON for re-reading


@dataclass
class GraphData:
    """Nodes and links for the force-directed graph visualization."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, int]] = field(default_factory=list)


@dataclass
class SiteIndex:
    """In-memory index built during Pass 1. Used by all renderers."""

    entries: list[EntryMeta] = field(default_factory=list)  # sorted by date desc
    by_number: dict[int, EntryMeta] = field(default_factory=dict)  # number -> entry
    by_contributor: dict[str, list[EntryMeta]] = field(default_factory=dict)  # lowercase login -> entries
    by_label: dict[str, list[EntryMeta]] = field(default_factory=dict)  # label name -> entries
    contributor_avatars: dict[str, str] = field(default_factory=dict)  # lowercase login -> avatar URL
    graph: GraphData = field(default_factory=GraphData)
