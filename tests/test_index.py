"""Tests for mirror.index."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mirror.config import Config
from mirror.index import build_index, _extract_graph_links


class TestExtractGraphLinks(unittest.TestCase):
    def test_cross_reference_same_repo(self) -> None:
        data = {
            "events": [
                {
                    "event": "cross-referenced",
                    "source": {
                        "issue": {
                            "number": 99,
                            "repository_url": "https://api.github.com/repos/owner/repo",
                        }
                    },
                }
            ]
        }
        links = _extract_graph_links(data, 42, "owner/repo")
        self.assertEqual(links, [{"source": 42, "target": 99}])

    def test_cross_reference_different_repo(self) -> None:
        data = {
            "events": [
                {
                    "event": "cross-referenced",
                    "source": {
                        "issue": {
                            "number": 99,
                            "repository_url": "https://api.github.com/repos/other/repo",
                        }
                    },
                }
            ]
        }
        links = _extract_graph_links(data, 42, "owner/repo")
        self.assertEqual(links, [])

    def test_non_cross_reference_events_ignored(self) -> None:
        data = {"events": [{"event": "labeled", "created_at": "2023-01-01T00:00:00Z"}]}
        links = _extract_graph_links(data, 42, "owner/repo")
        self.assertEqual(links, [])

    def test_no_events(self) -> None:
        links = _extract_graph_links({}, 42, "owner/repo")
        self.assertEqual(links, [])


class TestBuildIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        issues_dir = Path(self.tmpdir) / "issues"
        pulls_dir = Path(self.tmpdir) / "pulls"
        issues_dir.mkdir()
        pulls_dir.mkdir()

        issue_data = {
            "issue": {
                "number": 1,
                "title": "Bug report",
                "state": "open",
                "user": {"login": "Alice", "avatar_url": "http://a.png"},
                "labels": [{"name": "bug"}],
                "created_at": "2023-06-15T10:00:00Z",
            },
            "events": [],
        }
        (issues_dir / "1.json").write_text(json.dumps(issue_data))

        pull_data = {
            "pull": {
                "number": 2,
                "title": "Fix bug",
                "merged_at": "2023-06-20T10:00:00Z",
                "closed_at": "2023-06-20T10:00:00Z",
                "draft": False,
                "user": {"login": "Bob", "avatar_url": "http://b.png"},
                "labels": [{"name": "bug"}],
                "created_at": "2023-06-18T10:00:00Z",
            },
            "events": [],
        }
        (pulls_dir / "2.json").write_text(json.dumps(pull_data))

        self.config = Config(
            title="Test",
            owner="owner",
            repository="repo",
            footer="",
            base_url="/",
            input_dir=Path(self.tmpdir),
            output_dir=Path(self.tmpdir) / "output",
        )

    def test_builds_sorted_entries(self) -> None:
        index = build_index(self.config)
        self.assertEqual(len(index.entries), 2)
        # PR (2023-06-18) is more recent than issue (2023-06-15)
        self.assertEqual(index.entries[0].number, 2)
        self.assertEqual(index.entries[1].number, 1)

    def test_contributor_index(self) -> None:
        index = build_index(self.config)
        self.assertIn("alice", index.by_contributor)
        self.assertIn("bob", index.by_contributor)
        self.assertEqual(len(index.by_contributor["alice"]), 1)

    def test_label_index(self) -> None:
        index = build_index(self.config)
        self.assertIn("bug", index.by_label)
        self.assertEqual(len(index.by_label["bug"]), 2)

    def test_contributor_avatars(self) -> None:
        index = build_index(self.config)
        self.assertEqual(index.contributor_avatars["alice"], "http://a.png")
        self.assertEqual(index.contributor_avatars["bob"], "http://b.png")

    def test_graph_nodes(self) -> None:
        index = build_index(self.config)
        self.assertEqual(len(index.graph.nodes), 2)

    def test_subset_mode(self) -> None:
        config = Config(
            title="Test",
            owner="owner",
            repository="repo",
            footer="",
            base_url="/",
            input_dir=Path(self.tmpdir),
            output_dir=Path(self.tmpdir) / "output",
            subset=True,
        )
        index = build_index(config)
        self.assertEqual(len(index.entries), 2)  # only 2 files, both within subset


if __name__ == "__main__":
    unittest.main()
