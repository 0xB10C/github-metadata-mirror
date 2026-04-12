"""Tests for mirror.index."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mirror.config import Config
from mirror.index import build_index, _extract_graph_links


def _xref_event(number: int, repo_url: str, actor: str | None = None) -> dict:
    """Build a minimal cross-referenced event."""
    return {
        "event": "cross-referenced",
        "actor": {"login": actor} if actor else None,
        "source": {
            "issue": {
                "number": number,
                "repository_url": f"https://api.github.com/repos/{repo_url}",
            }
        },
    }


class TestExtractGraphLinksEvents(unittest.TestCase):
    """cross-referenced event handling."""

    def test_same_repo(self) -> None:
        data = {"events": [_xref_event(99, "owner/repo")]}
        self.assertEqual(
            _extract_graph_links(data, 42, "owner/repo"),
            [{"source": 42, "target": 99}],
        )

    def test_different_repo_excluded(self) -> None:
        data = {"events": [_xref_event(99, "other/repo")]}
        self.assertEqual(_extract_graph_links(data, 42, "owner/repo"), [])

    def test_excluded_bot_actor(self) -> None:
        data = {"events": [_xref_event(99, "owner/repo", actor="drahtbot")]}
        self.assertEqual(_extract_graph_links(data, 42, "owner/repo"), [])

    def test_excluded_bot_actor_case_insensitive(self) -> None:
        data = {"events": [_xref_event(99, "owner/repo", actor="DrahtBot")]}
        self.assertEqual(_extract_graph_links(data, 42, "owner/repo"), [])

    def test_null_actor_allowed(self) -> None:
        # actor field can be null in the JSON
        data = {"events": [_xref_event(99, "owner/repo", actor=None)]}
        self.assertEqual(
            _extract_graph_links(data, 42, "owner/repo"),
            [{"source": 42, "target": 99}],
        )

    def test_non_cross_reference_events_ignored(self) -> None:
        data = {"events": [{"event": "labeled", "created_at": "2023-01-01T00:00:00Z"}]}
        self.assertEqual(_extract_graph_links(data, 42, "owner/repo"), [])

    def test_no_events_key(self) -> None:
        self.assertEqual(_extract_graph_links({}, 42, "owner/repo"), [])

    def test_multiple_events_deduplication(self) -> None:
        # Same target appears twice (e.g. two cross-refs) — should produce one link.
        data = {
            "events": [
                _xref_event(99, "owner/repo"),
                _xref_event(99, "owner/repo"),
            ]
        }
        links = _extract_graph_links(data, 42, "owner/repo")
        self.assertEqual(links, [{"source": 42, "target": 99}])

    def test_multiple_distinct_events(self) -> None:
        data = {
            "events": [
                _xref_event(10, "owner/repo"),
                _xref_event(20, "owner/repo"),
                _xref_event(30, "other/repo"),   # excluded
            ]
        }
        links = _extract_graph_links(data, 42, "owner/repo")
        self.assertEqual(links, [
            {"source": 42, "target": 10},
            {"source": 42, "target": 20},
        ])


class TestExtractGraphLinksBody(unittest.TestCase):
    """Body parsing: same-repo GitHub URLs and plain #NNN references."""

    # --- same-repo GitHub URLs ---

    def test_same_repo_issue_url(self) -> None:
        body = "Fixes https://github.com/owner/repo/issues/100"
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 100}])

    def test_same_repo_pull_url(self) -> None:
        body = "Based on https://github.com/owner/repo/pull/200"
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 200}])

    def test_same_repo_url_case_insensitive_owner(self) -> None:
        # GitHub owner/repo comparisons are case-insensitive.
        body = "See https://github.com/Owner/Repo/issues/55"
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 55}])

    def test_other_repo_url_excluded(self) -> None:
        body = "See https://github.com/other/repo/issues/99 for background."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [])

    def test_other_repo_url_number_not_picked_up_by_hash_regex(self) -> None:
        # The number inside an other-repo URL must NOT be captured by #NNN scan.
        # e.g. "github.com/secp256k1/issues/7" — 7 should not become a link.
        body = "Similar to https://github.com/other/repo/issues/7"
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [])

    def test_multiple_same_repo_urls(self) -> None:
        body = (
            "This fixes https://github.com/owner/repo/issues/10 "
            "and https://github.com/owner/repo/pull/20."
        )
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertIn({"source": 42, "target": 10}, links)
        self.assertIn({"source": 42, "target": 20}, links)
        self.assertEqual(len(links), 2)

    def test_mixed_repos_in_urls(self) -> None:
        body = (
            "Builds on https://github.com/owner/repo/issues/5. "
            "Related: https://github.com/other/project/issues/999."
        )
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 5}])

    # --- plain #NNN references ---

    def test_plain_hash_ref(self) -> None:
        body = "This is related to #123."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 123}])

    def test_hash_ref_at_start_of_body(self) -> None:
        body = "#10 is the predecessor."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 10}])

    def test_hash_ref_self_excluded(self) -> None:
        # A body mentioning its own number should not create a self-link.
        body = "This is PR #42 which fixes things."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [])

    def test_hash_ref_inside_word_not_matched(self) -> None:
        # "issue#42" or "PR#42" should not match — the lookbehind requires non-word char.
        body = "See issue#42 for context."
        links = _extract_graph_links({}, 1, "owner/repo", body)
        self.assertEqual(links, [])

    def test_hash_ref_multiple(self) -> None:
        body = "Relates to #10, #20, and #30."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        targets = {l["target"] for l in links}
        self.assertEqual(targets, {10, 20, 30})

    def test_hash_ref_deduplicated(self) -> None:
        body = "See #99 and also #99 again."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 99}])

    def test_no_body(self) -> None:
        links = _extract_graph_links({}, 42, "owner/repo", None)
        self.assertEqual(links, [])

    def test_empty_body(self) -> None:
        links = _extract_graph_links({}, 42, "owner/repo", "")
        self.assertEqual(links, [])

    # --- interaction between URL pass and #NNN pass ---

    def test_same_repo_url_and_hash_ref_deduplication(self) -> None:
        # A full URL and a plain #NNN pointing to the same issue should not
        # produce duplicate links.
        body = "See https://github.com/owner/repo/issues/77 (i.e. #77)."
        links = _extract_graph_links({}, 42, "owner/repo", body)
        self.assertEqual(links, [{"source": 42, "target": 77}])

    def test_event_and_body_deduplication(self) -> None:
        # cross-referenced event + body mention of the same target → one link.
        data = {"events": [_xref_event(99, "owner/repo")]}
        links = _extract_graph_links(data, 42, "owner/repo", body="Also see #99.")
        self.assertEqual(links, [{"source": 42, "target": 99}])

    def test_event_and_body_combined(self) -> None:
        # Event brings in 99, body brings in 100 → both present.
        data = {"events": [_xref_event(99, "owner/repo")]}
        links = _extract_graph_links(data, 42, "owner/repo", body="#100 is related.")
        targets = {l["target"] for l in links}
        self.assertEqual(targets, {99, 100})


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
