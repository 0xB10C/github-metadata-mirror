"""Tests for mirror.html.components."""

from __future__ import annotations

import unittest
from pathlib import Path

from mirror.config import Config
from mirror.html.components import timeline_event
from mirror.markdown import MarkdownRenderer


def _config(**kw) -> Config:
    defaults = dict(
        title="t",
        owner="acme",
        repository="widget",
        footer="",
        base_url="/",
        input_dir=Path("/tmp/in"),
        output_dir=Path("/tmp/out"),
    )
    defaults.update(kw)
    return Config(**defaults)


class TestTimelineEventNullFields(unittest.TestCase):
    """GitHub sends some fields as null rather than omitting them, so a .get()
    default is not enough. drop_private_events removes the events that are known
    to arrive this way; these guards are the backstop if one slips through.
    """

    def setUp(self) -> None:
        self.config = _config()
        self.md = MarkdownRenderer()

    def _render(self, event: dict) -> str:
        return timeline_event(event, 1, self.config, self.md)

    def test_referenced_with_null_commit(self) -> None:
        html = self._render({
            "event": "referenced", "actor": {"login": "alice"},
            "commit_id": None, "commit_url": None,
            "created_at": "2023-01-01T00:00:00Z",
        })
        self.assertIn("referenced this in commit", html)
        self.assertNotIn("<a href=\"\">", html)

    def test_referenced_with_commit_still_links(self) -> None:
        html = self._render({
            "event": "referenced", "actor": {"login": "alice"},
            "commit_id": "abcdef1234567890",
            "commit_url": "https://api.github.com/repos/o/r/commits/abcdef1234567890",
            "created_at": "2023-01-01T00:00:00Z",
        })
        self.assertIn('href="https://github.com/o/r/commit/abcdef1234567890"', html)
        self.assertIn(">abcdef1234<", html)

    def test_reviewed_without_submitted_at(self) -> None:
        html = self._render({
            "event": "reviewed", "state": "PENDING", "submitted_at": None,
            "body": "a draft", "user": {"login": "alice"}, "id": 7,
        })
        self.assertIn("commented:", html)

    def test_reviewed_with_submitted_at_keeps_timestamp(self) -> None:
        html = self._render({
            "event": "reviewed", "state": "APPROVED",
            "submitted_at": "2023-01-01T15:04:00Z",
            "body": "looks good", "user": {"login": "alice"}, "id": 7,
        })
        self.assertIn("commented at 3:04 PM on January 1, 2023:", html)

    def test_cross_referenced_with_null_source(self) -> None:
        html = self._render({
            "event": "cross-referenced", "actor": {"login": "alice"},
            "source": None, "created_at": "2023-01-01T00:00:00Z",
        })
        self.assertIn("cross-referenced this", html)

    def test_cross_referenced_with_null_issue(self) -> None:
        html = self._render({
            "event": "cross-referenced", "actor": {"login": "alice"},
            "source": {"type": "issue", "issue": None},
            "created_at": "2023-01-01T00:00:00Z",
        })
        self.assertIn("cross-referenced this", html)


if __name__ == "__main__":
    unittest.main()
