"""Site renderer orchestrator: Pass 2 — renders all pages and writes to disk."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from mirror.config import Config
from mirror.data import build_pull_timeline, remove_nested_keys
from mirror.markdown import MarkdownRenderer
from mirror.models import SiteIndex
from mirror.util import format_date_long, urlize
from mirror.html.pages import (
    render_contributor_page,
    render_contributors_page,
    render_entry_page,
    render_graph_page,
    render_home_page,
    render_label_page,
    render_labels_page,
)


class SiteRenderer:
    """Orchestrates rendering of all site pages."""

    def __init__(self, config: Config, index: SiteIndex, md: MarkdownRenderer) -> None:
        self.config = config
        self.index = index
        self.md = md

    def render_all(self) -> None:
        """Render all pages and write to output directory."""
        self._copy_static()
        self._render_home()
        self._render_entries()
        self._render_contributor_pages()
        self._render_label_pages()
        self._render_graph()
        self._render_search_index()
        self._write_graph_json()

    def _write(self, path: Path, content: str) -> None:
        """Write content to a file, creating parent directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _copy_static(self) -> None:
        """Copy static assets to output directory."""
        # The static/ dir is relative to the project root (where build.py lives)
        static_src = Path(__file__).parent.parent.parent / "static"
        out = self.config.output_dir

        if not static_src.is_dir():
            print(f"Warning: static directory not found at {static_src}")
            return

        for subdir in ("css", "js", "img"):
            src = static_src / subdir
            dst = out / subdir
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        # Copy root-level static files
        for name in ("site.webmanifest", "browserconfig.xml"):
            src = static_src / name
            if src.is_file():
                shutil.copy2(src, out / name)

    def _render_home(self) -> None:
        print("Rendering home page...")
        html = render_home_page(self.index, self.config)
        self._write(self.config.output_dir / "index.html", html)

    def _render_entries(self) -> None:
        """Render each issue/PR page. Re-reads full JSON one at a time."""
        # Build undirected adjacency: number -> set of linked numbers.
        linked: dict[int, set[int]] = {}
        for link in self.index.graph.links:
            src, tgt = link["source"], link["target"]
            linked.setdefault(src, set()).add(tgt)
            linked.setdefault(tgt, set()).add(src)

        total = len(self.index.entries)
        for i, meta in enumerate(self.index.entries):
            if (i + 1) % 100 == 0 or i == 0 or i == total - 1:
                print(f"Rendering entries... {i + 1}/{total}", end="\r", flush=True)

            # Resolve linked EntryMeta objects (only those present in the index).
            linked_entries = sorted(
                (self.index.by_number[n] for n in linked.get(meta.number, set())
                 if n in self.index.by_number),
                key=lambda e: e.number,
            )

            # Re-read full JSON
            data = _read_json(meta.json_path)
            remove_nested_keys(data)

            if meta.is_pr and "comments" in data:
                build_pull_timeline(data)

            html = render_entry_page(meta, data, self.config, self.md, linked_entries)
            self._write(self.config.output_dir / str(meta.number) / "index.html", html)

            del data  # Release memory

        print(f"Rendering entries... {total}/{total} done")

    def _render_contributor_pages(self) -> None:
        print("Rendering contributor pages...")
        # Index page
        html = render_contributors_page(self.index, self.config)
        self._write(self.config.output_dir / "contributors" / "index.html", html)

        # Individual pages
        for login, entries in self.index.by_contributor.items():
            avatar = self.index.contributor_avatars.get(login, "")
            html = render_contributor_page(login, entries, avatar, self.config)
            self._write(self.config.output_dir / "contributor" / login / "index.html", html)

    def _render_label_pages(self) -> None:
        print("Rendering label pages...")
        # Index page
        html = render_labels_page(self.index, self.config)
        self._write(self.config.output_dir / "labels" / "index.html", html)

        # Individual pages
        for label, entries in self.index.by_label.items():
            slug = urlize(label)
            html = render_label_page(label, entries, self.config)
            self._write(self.config.output_dir / "labels" / slug / "index.html", html)

    def _render_graph(self) -> None:
        print("Rendering graph page...")
        html = render_graph_page(self.config)
        self._write(self.config.output_dir / "graph" / "index.html", html)

    def _render_search_index(self) -> None:
        """Write index.json for MiniSearch client-side search."""
        print("Writing search index...")
        entries: list[dict[str, Any]] = []
        for meta in self.index.entries:
            entry_type = "pull" if meta.is_pr else "issue"
            entries.append({
                "title": meta.title,
                "labels": meta.labels,
                "is_pr": meta.is_pr,
                "type": entry_type,
                "contributor": meta.contributor,
                "number": f"#{meta.number}",
                "date": format_date_long(meta.date),
                "state": meta.state,
                "permalink": f"{self.config.base_url}{meta.number}/",
            })
        json_str = json.dumps(entries, ensure_ascii=False, indent=None)
        self._write(self.config.output_dir / "index.json", json_str)

    def _write_graph_json(self) -> None:
        """Write graph.json for the force-directed graph visualization."""
        print("Writing graph.json...")
        graph_data = {
            "nodes": self.index.graph.nodes,
            "links": self.index.graph.links,
        }
        json_str = json.dumps(graph_data, ensure_ascii=False, indent=2)
        self._write(self.config.output_dir / "graph.json", json_str)


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)
