"""Pass 1: Build a lightweight in-memory index from backup JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mirror.config import Config
from mirror.data import extract_issue_meta, extract_pull_meta
from mirror.models import EntryMeta, GraphData, SiteIndex

SUBSET_SIZE = 100


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


# Bots whose cross-references are noise and should be excluded from the graph.
_GRAPH_EXCLUDED_ACTORS = frozenset({"drahtbot"})

# Matches any GitHub issue/PR URL: captures (owner, repo, number).
_RE_GITHUB_URL = re.compile(
    r"https?://github\.com/([^/\s]+)/([^/\s#]+)/(?:issues|pull)/(\d+)"
)
# Matches standalone #NNN references (same-repo convention on GitHub).
# Applied only after GitHub URLs have been stripped from the body.
_RE_BODY_REF = re.compile(r"(?<!\w)#(\d+)(?!\d)")


def _extract_graph_links(
    data: dict[str, Any], source_number: int, owner_repo: str,
    body: str | None = None,
) -> list[dict[str, int]]:
    """Extract cross-reference links for the graph.

    Sources:
    - cross-referenced events (GitHub records these on the *target* when
      something references it, so they capture incoming links)
    - same-repo GitHub URLs in the body (cross-referenced events are sometimes
      absent from backups; URL parsing fills the gap for outgoing links)
    - plain #NNN references in the body (same-repo convention on GitHub)
    """
    seen: set[int] = set()
    links: list[dict[str, int]] = []

    for event in data.get("events", []):
        if event.get("event") != "cross-referenced":
            continue
        actor = (event.get("actor") or {}).get("login", "")
        if actor.lower() in _GRAPH_EXCLUDED_ACTORS:
            continue
        source_issue = event.get("source", {}).get("issue", {})
        repo_url = source_issue.get("repository_url", "")
        target = source_issue.get("number")
        if target and owner_repo in repo_url and target not in seen:
            seen.add(target)
            links.append({"source": source_number, "target": target})

    if body:
        owner_lower, repo_lower = (s.lower() for s in owner_repo.split("/", 1))

        def _on_github_url(m: re.Match) -> str:
            # Strip every GitHub URL regardless of repo; only record same-repo ones.
            if m.group(1).lower() == owner_lower and m.group(2).lower() == repo_lower:
                target = int(m.group(3))
                if target != source_number and target not in seen:
                    seen.add(target)
                    links.append({"source": source_number, "target": target})
            return ""

        # Pass 1: full GitHub URLs. Strip them all so their numbers are not
        # picked up by the plain #NNN scan below.
        cleaned = _RE_GITHUB_URL.sub(_on_github_url, body)

        # Pass 2: plain #NNN references in the URL-stripped body.
        for m in _RE_BODY_REF.finditer(cleaned):
            target = int(m.group(1))
            if target != source_number and target not in seen:
                seen.add(target)
                links.append({"source": source_number, "target": target})

    return links


def build_index(config: Config) -> SiteIndex:
    """Read all issue/pull JSON files and build the site index.

    Only extracts lightweight metadata — full JSON is discarded after
    extracting EntryMeta and graph links.
    """
    owner_repo = f"{config.owner}/{config.repository}"

    issue_files = sorted(config.input_dir.glob("issues/*.json"))
    pull_files = sorted(config.input_dir.glob("pulls/*.json"))

    if config.subset:
        print(f"Subset mode: limiting to {SUBSET_SIZE} issues and {SUBSET_SIZE} pulls")
        issue_files = issue_files[:SUBSET_SIZE]
        pull_files = pull_files[:SUBSET_SIZE]

    index = SiteIndex()

    total_issues = len(issue_files)
    for i, issue_file in enumerate(issue_files):
        if (i + 1) % 100 == 0 or i == 0 or i == total_issues - 1:
            print(f"Indexing issues... {i + 1}/{total_issues}", end="\r", flush=True)

        data = _read_json(issue_file)
        meta = extract_issue_meta(data, issue_file)
        index.entries.append(meta)

        index.graph.nodes.append({
            "number": meta.number,
            "state": meta.state,
            "title": meta.title,
            "avatar_url": meta.avatar_url,
            "is_pr": False,
            "url": f"{config.base_url}{meta.number}/",
        })
        body = (data.get("issue") or {}).get("body") or ""
        index.graph.links.extend(
            _extract_graph_links(data, meta.number, owner_repo, body)
        )

        _index_entry(index, meta)

    if total_issues:
        print(f"Indexing issues... {total_issues}/{total_issues} done")

    total_pulls = len(pull_files)
    for i, pull_file in enumerate(pull_files):
        if (i + 1) % 100 == 0 or i == 0 or i == total_pulls - 1:
            print(f"Indexing pulls... {i + 1}/{total_pulls}", end="\r", flush=True)

        data = _read_json(pull_file)
        meta = extract_pull_meta(data, pull_file)
        index.entries.append(meta)

        index.graph.nodes.append({
            "number": meta.number,
            "state": meta.state,
            "title": meta.title,
            "avatar_url": meta.avatar_url,
            "is_pr": True,
            "url": f"{config.base_url}{meta.number}/",
        })
        body = (data.get("pull") or {}).get("body") or ""
        index.graph.links.extend(
            _extract_graph_links(data, meta.number, owner_repo, body)
        )

        _index_entry(index, meta)

    if total_pulls:
        print(f"Indexing pulls... {total_pulls}/{total_pulls} done")

    # Sort entries by date descending
    index.entries.sort(key=lambda e: e.date, reverse=True)

    return index


def _index_entry(index: SiteIndex, meta: EntryMeta) -> None:
    """Add an entry to the contributor, label, and number indexes."""
    index.by_number[meta.number] = meta

    login_lower = meta.contributor.lower()
    index.by_contributor.setdefault(login_lower, []).append(meta)
    index.contributor_avatars[login_lower] = meta.avatar_url

    for label in meta.labels:
        index.by_label.setdefault(label, []).append(meta)
