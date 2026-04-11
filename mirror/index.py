"""Pass 1: Build a lightweight in-memory index from backup JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mirror.config import Config
from mirror.data import extract_issue_meta, extract_pull_meta
from mirror.models import EntryMeta, GraphData, SiteIndex

SUBSET_SIZE = 100


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def _extract_graph_links(
    data: dict[str, Any], source_number: int, owner_repo: str,
) -> list[dict[str, int]]:
    """Extract cross-reference links from events for the graph."""
    links: list[dict[str, int]] = []
    for event in data.get("events", []):
        if event.get("event") != "cross-referenced":
            continue
        source_issue = event.get("source", {}).get("issue", {})
        repo_url = source_issue.get("repository_url", "")
        if owner_repo in repo_url:
            links.append({
                "source": source_number,
                "target": source_issue["number"],
            })
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
        index.graph.links.extend(
            _extract_graph_links(data, meta.number, owner_repo)
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
        index.graph.links.extend(
            _extract_graph_links(data, meta.number, owner_repo)
        )

        _index_entry(index, meta)

    if total_pulls:
        print(f"Indexing pulls... {total_pulls}/{total_pulls} done")

    # Sort entries by date descending
    index.entries.sort(key=lambda e: e.date, reverse=True)

    return index


def _index_entry(index: SiteIndex, meta: EntryMeta) -> None:
    """Add an entry to the contributor and label indexes."""
    login_lower = meta.contributor.lower()
    index.by_contributor.setdefault(login_lower, []).append(meta)
    index.contributor_avatars[login_lower] = meta.avatar_url

    for label in meta.labels:
        index.by_label.setdefault(label, []).append(meta)
