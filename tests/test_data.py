"""Tests for mirror.data."""

from __future__ import annotations

import unittest
from pathlib import Path

from mirror.data import (
    remove_nested_keys,
    determine_issue_state,
    determine_pull_state,
    extract_issue_meta,
    extract_pull_meta,
    build_pull_timeline,
)


class TestRemoveNestedKeys(unittest.TestCase):
    def test_removes_known_keys(self) -> None:
        obj = {"title": "test", "url": "http://...", "node_id": "abc"}
        result = remove_nested_keys(obj)
        self.assertEqual(result, {"title": "test"})

    def test_recurses_into_dicts(self) -> None:
        obj = {"user": {"login": "alice", "gravatar_id": "xxx", "site_admin": True}}
        result = remove_nested_keys(obj)
        self.assertEqual(result, {"user": {"login": "alice"}})

    def test_recurses_into_lists(self) -> None:
        obj = [{"url": "http://...", "name": "test"}]
        result = remove_nested_keys(obj)
        self.assertEqual(result, [{"name": "test"}])

    def test_preserves_non_target_keys(self) -> None:
        obj = {"title": "hello", "body": "world", "number": 42}
        result = remove_nested_keys(obj)
        self.assertEqual(result, {"title": "hello", "body": "world", "number": 42})


class TestDetermineIssueState(unittest.TestCase):
    def test_open(self) -> None:
        self.assertEqual(determine_issue_state({"state": "open"}), "open")

    def test_closed(self) -> None:
        self.assertEqual(determine_issue_state({"state": "closed"}), "closed")

    def test_complete(self) -> None:
        self.assertEqual(
            determine_issue_state({"state": "closed", "state_reason": "completed"}),
            "complete",
        )

    def test_closed_not_completed(self) -> None:
        self.assertEqual(
            determine_issue_state({"state": "closed", "state_reason": "not_planned"}),
            "closed",
        )


class TestDeterminePullState(unittest.TestCase):
    def test_merged(self) -> None:
        self.assertEqual(
            determine_pull_state({"merged_at": "2023-01-01T00:00:00Z", "closed_at": "2023-01-01T00:00:00Z"}),
            "merged",
        )

    def test_closed(self) -> None:
        self.assertEqual(
            determine_pull_state({"merged_at": None, "closed_at": "2023-01-01T00:00:00Z", "draft": False}),
            "closed",
        )

    def test_draft(self) -> None:
        self.assertEqual(
            determine_pull_state({"merged_at": None, "closed_at": None, "draft": True}),
            "draft",
        )

    def test_open(self) -> None:
        self.assertEqual(
            determine_pull_state({"merged_at": None, "closed_at": None, "draft": False}),
            "open",
        )


class TestExtractIssueMeta(unittest.TestCase):
    def test_basic(self) -> None:
        data = {
            "issue": {
                "number": 42,
                "title": "Test issue",
                "state": "open",
                "user": {"login": "Alice", "avatar_url": "http://avatar"},
                "labels": [{"name": "bug"}, {"name": "help wanted"}],
                "created_at": "2023-06-15T10:00:00Z",
            }
        }
        meta = extract_issue_meta(data, Path("/tmp/42.json"))
        self.assertEqual(meta.number, 42)
        self.assertEqual(meta.title, "Test issue")
        self.assertEqual(meta.state, "open")
        self.assertFalse(meta.is_pr)
        self.assertEqual(meta.contributor, "Alice")
        self.assertEqual(meta.labels, ["bug", "help wanted"])


class TestExtractPullMeta(unittest.TestCase):
    def test_merged(self) -> None:
        data = {
            "pull": {
                "number": 100,
                "title": "Fix thing",
                "merged_at": "2023-06-15T10:00:00Z",
                "closed_at": "2023-06-15T10:00:00Z",
                "draft": False,
                "user": {"login": "Bob", "avatar_url": "http://avatar"},
                "labels": [],
                "created_at": "2023-06-10T10:00:00Z",
            }
        }
        meta = extract_pull_meta(data, Path("/tmp/100.json"))
        self.assertEqual(meta.number, 100)
        self.assertTrue(meta.is_pr)
        self.assertEqual(meta.state, "merged")


class TestBuildPullTimeline(unittest.TestCase):
    def test_merges_code_reviews_into_events(self) -> None:
        data = {
            "events": [
                {"event": "commented", "created_at": "2023-01-01T01:00:00Z"},
                {"event": "commented", "created_at": "2023-01-01T03:00:00Z"},
            ],
            "comments": [
                {
                    "diff_hunk": "@@ -1,3 +1,4 @@",
                    "created_at": "2023-01-01T02:00:00Z",
                    "user": {"login": "reviewer"},
                    "body": "nit",
                },
            ],
        }
        build_pull_timeline(data)
        self.assertNotIn("comments", data)
        events = data["events"]
        self.assertEqual(len(events), 3)
        # code_review should be between the two comments
        self.assertEqual(events[0]["event"], "commented")
        self.assertEqual(events[1]["event"], "code_review")
        self.assertEqual(events[2]["event"], "commented")

    def test_no_comments_key(self) -> None:
        data = {"events": [{"event": "closed", "created_at": "2023-01-01T00:00:00Z"}]}
        build_pull_timeline(data)  # should not raise
        self.assertEqual(len(data["events"]), 1)

    def test_groups_by_hunk(self) -> None:
        data = {
            "events": [],
            "comments": [
                {"diff_hunk": "hunk1", "created_at": "2023-01-01T01:00:00Z", "user": None, "body": "a"},
                {"diff_hunk": "hunk1", "created_at": "2023-01-01T01:05:00Z", "user": None, "body": "b"},
                {"diff_hunk": "hunk2", "created_at": "2023-01-01T02:00:00Z", "user": None, "body": "c"},
            ],
        }
        build_pull_timeline(data)
        events = data["events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(len(events[0]["data"]), 2)  # hunk1 has 2 comments
        self.assertEqual(len(events[1]["data"]), 1)  # hunk2 has 1 comment


if __name__ == "__main__":
    unittest.main()
