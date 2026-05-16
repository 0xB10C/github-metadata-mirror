"""Tests for mirror.markdown_page."""

from __future__ import annotations

import unittest
from pathlib import Path

from mirror.config import Config
from mirror.markdown_page import _trim_diff_hunk, render_entry_markdown, render_llms_txt
from mirror.models import EntryMeta


def _config(**kw) -> Config:
    defaults = dict(
        title="t",
        owner="acme",
        repository="widget",
        footer="",
        base_url="/",
        input_dir=Path("/tmp/in"),
        output_dir=Path("/tmp/out"),
        markdown=True,
    )
    defaults.update(kw)
    return Config(**defaults)


def _issue_meta(state: str = "open", number: int = 42) -> EntryMeta:
    return EntryMeta(
        number=number,
        title="Hello: world",
        state=state,
        is_pr=False,
        contributor="alice",
        avatar_url="",
        labels=["bug"],
        date="2024-01-15T10:00:00Z",
        json_path=Path(f"/tmp/{number}.json"),
    )


def _pr_meta(state: str = "merged", number: int = 100) -> EntryMeta:
    return EntryMeta(
        number=number,
        title="Fix bug",
        state=state,
        is_pr=True,
        contributor="bob",
        avatar_url="",
        labels=[],
        date="2024-02-01T10:00:00Z",
        json_path=Path(f"/tmp/{number}.json"),
    )


class TestFrontMatter(unittest.TestCase):
    def test_issue_basic_fields(self) -> None:
        meta = _issue_meta(state="open")
        data = {
            "issue": {
                "number": 42,
                "title": "Hello: world",
                "state": "open",
                "user": {"login": "alice"},
                "author_association": "CONTRIBUTOR",
                "created_at": "2024-01-15T10:00:00Z",
                "labels": [{"name": "bug"}],
                "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("---\n", out)
        self.assertIn("number: 42", out)
        self.assertIn("type: issue", out)
        # Title with colon must be JSON-quoted
        self.assertIn('title: "Hello: world"', out)
        self.assertIn("state: open", out)
        self.assertNotIn("state_reason:", out)
        self.assertIn("author: \"alice\"", out)
        self.assertIn("author_association: contributor", out)
        self.assertIn("labels:\n  - \"bug\"", out)
        self.assertIn("linked: []", out)
        # No PR-only fields
        self.assertNotIn("merged_at:", out)
        self.assertNotIn("draft:", out)

    def test_issue_with_state_reason(self) -> None:
        meta = _issue_meta(state="complete")
        data = {
            "issue": {
                "number": 42,
                "title": "x",
                "state": "closed",
                "state_reason": "completed",
                "user": {"login": "alice"},
                "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z",
                "labels": [],
                "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("state: complete", out)
        self.assertIn("state_reason: completed", out)
        self.assertIn("labels: []", out)

    def test_issue_with_milestone(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "NONE",
                "created_at": "2024-01-15T10:00:00Z", "labels": [],
                "milestone": {"title": "v25.0"}, "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('milestone: "v25.0"', out)

    def test_pr_fields(self) -> None:
        meta = _pr_meta(state="merged")
        data = {
            "pull": {
                "number": 100, "title": "Fix bug", "state": "closed",
                "merged_at": "2024-02-10T10:00:00Z",
                "user": {"login": "bob"}, "author_association": "MEMBER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "base": {"label": "owner:master"},
                "head": {"label": "bob:feature"},
                "commits": 4, "changed_files": 2, "additions": 50, "deletions": 10,
                "draft": False,
                "requested_reviewers": [{"login": "alice"}, {"login": "carol"}],
                "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("type: pull", out)
        self.assertIn('merged_at: "2024-02-10T10:00:00Z"', out)
        self.assertIn('base: "owner:master"', out)
        self.assertIn('head: "bob:feature"', out)
        self.assertIn("commits: 4", out)
        self.assertIn("changed_files: 2", out)
        self.assertIn("additions: 50", out)
        self.assertIn("deletions: 10", out)
        self.assertIn("draft: false", out)
        self.assertIn('requested_reviewers:\n  - "alice"\n  - "carol"', out)

    def test_linked_entries(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "NONE",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [],
        }
        linked = [
            EntryMeta(123, "Some other issue", "open", False, "z", "", [], "2024-01-01T00:00:00Z", Path("/tmp/123.json")),
            EntryMeta(456, 'Title with "quotes"', "merged", True, "z", "", [], "2024-01-01T00:00:00Z", Path("/tmp/456.json")),
        ]
        out = render_entry_markdown(meta, data, _config(), linked)
        self.assertIn("linked:\n  - number: 123\n    title: \"Some other issue\"\n  - number: 456\n    title: \"Title with \\\"quotes\\\"\"", out)


class TestCommentEvents(unittest.TestCase):
    def test_commented_renders_block_with_raw_body(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [],
                "body": "Initial body refers to #99 and @bob.",
            },
            "events": [
                {
                    "event": "commented",
                    "id": 555,
                    "created_at": "2024-01-16T10:00:00Z",
                    "actor": {"login": "carol"},
                    "author_association": "CONTRIBUTOR",
                    "body": "Reply with #123 and @bob -- raw markdown.",
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # Raw body has unmodified #99 and @bob references (no link rewriting)
        self.assertIn("Initial body refers to #99 and @bob.", out)
        # Comment header with id, login, association (lowercased), date
        self.assertIn("### Comment -- @carol -- 2024-01-16T10:00:00Z", out)
        # ID and author_association are no longer in per-comment headers
        timeline = out.split("## Timeline", 1)[1]
        self.assertNotIn("555", timeline)
        self.assertNotIn("(contributor)", timeline)
        # Comment body unmodified
        self.assertIn("Reply with #123 and @bob -- raw markdown.", out)
        # Timeline header present
        self.assertIn("## Timeline", out)

    def test_missing_author_association_renders_none(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": None,
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [
                {
                    "event": "commented", "id": 1, "created_at": "2024-01-16T10:00:00Z",
                    "actor": {"login": "dave"}, "author_association": None,
                    "body": "hi",
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("author_association: none", out)
        self.assertIn("### Comment -- @dave -- 2024-01-16T10:00:00Z", out)


class TestCodeReviewEvent(unittest.TestCase):
    def test_code_review_block(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [
                {
                    "event": "code_review",
                    "created_at": "2024-02-02T10:00:00Z",
                    "data": [
                        {
                            "id": 999,
                            "user": {"login": "reviewer"},
                            "author_association": "MEMBER",
                            "created_at": "2024-02-02T10:00:00Z",
                            "diff_hunk": "@@ -1,3 +1,4 @@\n line a\n-old\n+new",
                            "path": "src/foo.py",
                            "line": 42,
                            "body": "nit: rename",
                        },
                        {
                            "id": 1000,
                            "user": {"login": "author"},
                            "author_association": "CONTRIBUTOR",
                            "created_at": "2024-02-02T11:00:00Z",
                            "diff_hunk": "@@ -1,3 +1,4 @@\n line a\n-old\n+new",
                            "path": "src/foo.py",
                            "line": 42,
                            "body": "ack",
                        },
                    ],
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("### Code review on `src/foo.py:42` -- 2024-02-02T10:00:00Z", out)
        self.assertIn("```diff\n@@ -1,3 +1,4 @@\n line a\n-old\n+new\n```", out)
        self.assertIn("#### Review comment -- @reviewer -- 2024-02-02T10:00:00Z", out)
        self.assertIn("nit: rename", out)
        self.assertIn("#### Review comment -- @author -- 2024-02-02T11:00:00Z", out)
        self.assertIn("ack", out)


class TestTrimDiffHunk(unittest.TestCase):
    def test_short_hunk_unchanged(self) -> None:
        hunk = "@@ -1,3 +1,4 @@\n line a\n-old\n+new"
        self.assertEqual(_trim_diff_hunk(hunk, tail_lines=12), hunk)

    def test_long_hunk_keeps_header_and_tail(self) -> None:
        header = "@@ -1,50 +1,50 @@"
        body = [f" line {i}" for i in range(30)]
        body.append("-bad")
        body.append("+good")
        hunk = "\n".join([header] + body)

        trimmed = _trim_diff_hunk(hunk, tail_lines=5)
        trimmed_lines = trimmed.split("\n")

        # Header preserved
        self.assertEqual(trimmed_lines[0], header)
        # Elision marker present
        self.assertTrue(trimmed_lines[1].startswith("... ("))
        self.assertIn("earlier lines elided", trimmed_lines[1])
        # Exactly tail_lines lines at the end
        self.assertEqual(trimmed_lines[-5:], body[-5:])
        # Total = header + marker + 5 tail = 7 lines
        self.assertEqual(len(trimmed_lines), 7)

    def test_no_header_still_works(self) -> None:
        body = [f" line {i}" for i in range(20)]
        hunk = "\n".join(body)
        trimmed = _trim_diff_hunk(hunk, tail_lines=4)
        trimmed_lines = trimmed.split("\n")
        # No @@ header, so marker is first
        self.assertTrue(trimmed_lines[0].startswith("... ("))
        self.assertEqual(trimmed_lines[-4:], body[-4:])

    def test_empty_hunk(self) -> None:
        self.assertEqual(_trim_diff_hunk("", 12), "")

    def test_at_threshold_unchanged(self) -> None:
        # 1 header + 12 body lines = exactly tail_lines + 1 total
        header = "@@ -1,12 +1,12 @@"
        body = [f" line {i}" for i in range(12)]
        hunk = "\n".join([header] + body)
        self.assertEqual(_trim_diff_hunk(hunk, tail_lines=12), hunk)


class TestCodeReviewTrimming(unittest.TestCase):
    def test_large_hunk_trimmed_in_output(self) -> None:
        meta = _pr_meta()
        header = "@@ -1,40 +1,40 @@"
        body_lines = [f" context line {i}" for i in range(30)]
        body_lines.append("-bad code")
        body_lines.append("+good code")
        large_hunk = "\n".join([header] + body_lines)

        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [{
                "event": "code_review",
                "created_at": "2024-02-02T10:00:00Z",
                "data": [{
                    "id": 1, "user": {"login": "r"},
                    "author_association": "MEMBER",
                    "created_at": "2024-02-02T10:00:00Z",
                    "diff_hunk": large_hunk,
                    "path": "f.py", "line": 40,
                    "body": "nit",
                }],
            }],
        }
        out = render_entry_markdown(meta, data, _config(), [])

        # Header still present
        self.assertIn(header, out)
        # Elision marker present
        self.assertIn("earlier lines elided", out)
        # Commented line (tail) still present
        self.assertIn("+good code", out)
        self.assertIn("-bad code", out)
        # Early context lines are gone
        self.assertNotIn(" context line 0", out)
        self.assertNotIn(" context line 5", out)


class TestReviewedEvent(unittest.TestCase):
    def test_approved_with_body(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [
                {
                    "event": "reviewed",
                    "id": 777,
                    "state": "APPROVED",
                    "submitted_at": "2024-02-03T10:00:00Z",
                    "user": {"login": "reviewer"},
                    "author_association": "MEMBER",
                    "body": "LGTM",
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # State is folded into the header; no separate italic state line
        self.assertNotIn("*@reviewer approved", out)
        self.assertIn("### Review -- @reviewer (approved) -- 2024-02-03T10:00:00Z", out)
        self.assertIn("LGTM", out)

    def test_approved_without_body_keeps_state_line(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [{
                "event": "reviewed", "id": 5, "state": "APPROVED",
                "submitted_at": "2024-02-03T10:00:00Z",
                "user": {"login": "reviewer"}, "author_association": "MEMBER",
                "body": "",
            }],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("*@reviewer approved -- 2024-02-03T10:00:00Z*", out)
        self.assertNotIn("### Review", out)

    def test_commented_state_no_state_line(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [
                {
                    "event": "reviewed", "id": 1, "state": "COMMENTED",
                    "submitted_at": "2024-02-03T10:00:00Z",
                    "user": {"login": "r"}, "author_association": "NONE",
                    "body": "some thoughts",
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # No "*@r commented*" italic line for commented state
        self.assertNotIn("commented --", out)
        self.assertIn("### Review -- @r -- 2024-02-03T10:00:00Z", out)


class TestSimpleEvents(unittest.TestCase):
    def _wrap(self, events: list[dict]) -> str:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": events,
        }
        return render_entry_markdown(meta, data, _config(), [])

    def test_labeled(self) -> None:
        out = self._wrap([{
            "event": "labeled",
            "created_at": "2024-01-16T10:00:00Z",
            "actor": {"login": "alice"},
            "label": {"name": "bug"},
        }])
        self.assertIn("*@alice added label `bug` -- 2024-01-16T10:00:00Z*", out)

    def test_closed(self) -> None:
        out = self._wrap([{
            "event": "closed",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
        }])
        self.assertIn("*@alice closed this -- 2024-01-17T10:00:00Z*", out)

    def test_renamed(self) -> None:
        out = self._wrap([{
            "event": "renamed",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "rename": {"from": "Old title", "to": "New title"},
        }])
        self.assertIn('*@alice renamed: "Old title" -> "New title" -- 2024-01-17T10:00:00Z*', out)

    def test_committed_uses_git_author_name(self) -> None:
        out = self._wrap([{
            "event": "committed",
            "sha": "7bfae739e3abcdef1234567890",
            "author": {"name": "Jane Developer", "email": "jane@example.com"},
            "message": "build: add skeleton for new silentpayments module\n\nlonger body",
        }])
        self.assertIn(
            "*Jane Developer committed 7bfae739e3: build: add skeleton for new silentpayments module*",
            out,
        )
        self.assertNotIn("@unknown", out)

    def test_committed_without_author_omits_name(self) -> None:
        out = self._wrap([{
            "event": "committed",
            "sha": "abc1234567",
            "message": "fix: thing",
        }])
        self.assertIn("*committed abc1234567: fix: thing*", out)
        self.assertNotIn("@unknown", out)

    def test_referenced_includes_commit_url(self) -> None:
        out = self._wrap([{
            "event": "referenced",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "commit_id": "1c8233acf208a6f935fc11161feda6c0775945e6",
            "commit_url": "https://api.github.com/repos/acme/widget/commits/1c8233acf208a6f935fc11161feda6c0775945e6",
        }])
        self.assertIn(
            "*@alice referenced this in commit 1c8233acf2 "
            "(https://github.com/acme/widget/commit/1c8233acf208a6f935fc11161feda6c0775945e6) "
            "-- 2024-01-17T10:00:00Z*",
            out,
        )

    def test_referenced_without_url(self) -> None:
        out = self._wrap([{
            "event": "referenced",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "commit_id": "abc1234567",
        }])
        self.assertIn("*@alice referenced this in commit abc1234567 -- 2024-01-17T10:00:00Z*", out)

    def test_force_pushed_includes_sha(self) -> None:
        out = self._wrap([{
            "event": "head_ref_force_pushed",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "commit_id": "445f2e835fdd81a23784d5b398f1180453a74c55",
        }])
        self.assertIn("*@alice force-pushed to 445f2e835f -- 2024-01-17T10:00:00Z*", out)

    def test_force_pushed_without_sha(self) -> None:
        out = self._wrap([{
            "event": "head_ref_force_pushed",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
        }])
        self.assertIn("*@alice force-pushed -- 2024-01-17T10:00:00Z*", out)

    def test_base_ref_force_pushed_includes_sha(self) -> None:
        out = self._wrap([{
            "event": "base_ref_force_pushed",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "commit_id": "deadbeefcafebabe1234567890",
        }])
        self.assertIn("*@alice force-pushed the base branch to deadbeefca -- 2024-01-17T10:00:00Z*", out)

    def test_cross_referenced(self) -> None:
        out = self._wrap([{
            "event": "cross-referenced",
            "created_at": "2024-01-17T10:00:00Z",
            "actor": {"login": "alice"},
            "source": {"type": "issue", "issue": {
                "number": 99, "title": "Other", "user": {"login": "carol"}
            }},
        }])
        self.assertIn("*@alice cross-referenced this from #99 (Other) by @carol -- 2024-01-17T10:00:00Z*", out)


class TestSilentEvents(unittest.TestCase):
    def test_silent_events_produce_no_output(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [
                {"event": "subscribed", "created_at": "2024-01-16T10:00:00Z", "actor": {"login": "z"}},
                {"event": "mentioned", "created_at": "2024-01-16T10:00:00Z", "actor": {"login": "z"}},
                {"event": "line-commented", "created_at": "2024-01-16T10:00:00Z", "actor": {"login": "z"}},
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # No timeline section, since all events were silent
        self.assertNotIn("## Timeline", out)
        self.assertNotIn("@z", out)


class TestTitleEscaping(unittest.TestCase):
    def test_title_with_colon_and_quote(self) -> None:
        meta = _issue_meta()
        meta.title = 'Strange: "quoted" title'
        data = {
            "issue": {
                "number": 42,
                "title": 'Strange: "quoted" title',
                "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # JSON encoding escapes inner quotes
        self.assertIn('title: "Strange: \\"quoted\\" title"', out)


class TestTimestampFields(unittest.TestCase):
    def test_updated_and_closed_at_emitted_when_present(self) -> None:
        meta = _issue_meta(state="closed")
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "closed",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-20T10:00:00Z",
                "closed_at": "2024-01-19T10:00:00Z",
                "labels": [], "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('updated_at: "2024-01-20T10:00:00Z"', out)
        self.assertIn('closed_at: "2024-01-19T10:00:00Z"', out)

    def test_closed_at_omitted_when_null(self) -> None:
        meta = _issue_meta(state="open")
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z",
                "closed_at": None, "updated_at": None,
                "labels": [], "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertNotIn("closed_at:", out)
        self.assertNotIn("updated_at:", out)

    def test_pr_has_all_three_dates(self) -> None:
        meta = _pr_meta(state="merged")
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "closed",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z",
                "updated_at": "2024-02-10T10:00:00Z",
                "closed_at": "2024-02-10T10:00:00Z",
                "merged_at": "2024-02-10T10:00:00Z",
                "labels": [], "draft": False, "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('created_at: "2024-02-01T10:00:00Z"', out)
        self.assertIn('updated_at: "2024-02-10T10:00:00Z"', out)
        self.assertIn('closed_at: "2024-02-10T10:00:00Z"', out)
        self.assertIn('merged_at: "2024-02-10T10:00:00Z"', out)


class TestSourceURL(unittest.TestCase):
    def test_issue_source_url(self) -> None:
        meta = _issue_meta(number=42)
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('source: "https://github.com/acme/widget/issues/42"', out)

    def test_pr_source_url(self) -> None:
        meta = _pr_meta(number=100)
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('source: "https://github.com/acme/widget/pull/100"', out)


class TestParticipants(unittest.TestCase):
    def test_author_only_when_no_events(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('participants:\n  - "alice"', out)

    def test_deduplicates_and_preserves_appearance_order(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [
                {"event": "commented", "id": 1, "created_at": "2024-01-16T10:00:00Z",
                 "actor": {"login": "bob"}, "body": "hi"},
                {"event": "commented", "id": 2, "created_at": "2024-01-16T11:00:00Z",
                 "actor": {"login": "carol"}, "body": "yo"},
                {"event": "commented", "id": 3, "created_at": "2024-01-16T12:00:00Z",
                 "actor": {"login": "bob"}, "body": "back"},
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn(
            'participants:\n  - "alice"\n  - "bob"\n  - "carol"',
            out,
        )

    def test_includes_code_review_authors(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [
                {
                    "event": "code_review",
                    "created_at": "2024-02-02T10:00:00Z",
                    "data": [
                        {"id": 1, "user": {"login": "reviewer"}, "created_at": "2024-02-02T10:00:00Z",
                         "diff_hunk": "@@", "path": "f.py", "line": 1, "body": "nit"},
                        {"id": 2, "user": {"login": "bob"}, "created_at": "2024-02-02T11:00:00Z",
                         "diff_hunk": "@@", "path": "f.py", "line": 1, "body": "ack"},
                    ],
                },
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn(
            'participants:\n  - "bob"\n  - "reviewer"',
            out,
        )

    def test_excludes_non_content_actors(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [], "body": "",
            },
            "events": [
                # Pure actor events should NOT make someone a participant
                {"event": "labeled", "created_at": "2024-01-16T10:00:00Z",
                 "actor": {"login": "labeler"}, "label": {"name": "bug"}},
                {"event": "closed", "created_at": "2024-01-16T11:00:00Z",
                 "actor": {"login": "closer"}},
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn('participants:\n  - "alice"\n', out)
        self.assertNotIn("labeler", out.split("---")[1])  # not in front matter
        self.assertNotIn("closer", out.split("---")[1])

    def test_reviewed_without_body_not_participant(self) -> None:
        meta = _pr_meta()
        data = {
            "pull": {
                "number": 100, "title": "x", "state": "open",
                "user": {"login": "bob"}, "author_association": "OWNER",
                "created_at": "2024-02-01T10:00:00Z", "labels": [],
                "draft": False, "body": "",
            },
            "events": [
                # Approval without a comment body -- not a substantive participant
                {"event": "reviewed", "id": 1, "state": "APPROVED",
                 "submitted_at": "2024-02-03T10:00:00Z",
                 "user": {"login": "approver"}, "body": ""},
            ],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        front = out.split("---")[1]
        self.assertNotIn("approver", front)
        self.assertIn('participants:\n  - "bob"', out)


class TestBodyAndStructure(unittest.TestCase):
    def test_h1_and_body(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "My title", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [],
                "body": "Body line 1\n\nBody line 2 with @user and #123",
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        self.assertIn("# My title (#42)", out)
        # Body passed through raw
        self.assertIn("Body line 1\n\nBody line 2 with @user and #123", out)
        # Output ends with trailing newline
        self.assertTrue(out.endswith("\n"))

    def test_empty_body_omits_body_section(self) -> None:
        meta = _issue_meta()
        data = {
            "issue": {
                "number": 42, "title": "x", "state": "open",
                "user": {"login": "alice"}, "author_association": "OWNER",
                "created_at": "2024-01-15T10:00:00Z", "labels": [],
                "body": None,
            },
            "events": [],
        }
        out = render_entry_markdown(meta, data, _config(), [])
        # H1 is there, but no body content beyond it
        self.assertIn("# x (#42)", out)


class TestLlmsTxt(unittest.TestCase):
    def test_basic_content(self) -> None:
        out = render_llms_txt(_config(title="My Mirror"))
        self.assertTrue(out.startswith("# My Mirror\n"))
        self.assertIn("[acme/widget](https://github.com/acme/widget)", out)
        self.assertIn("`/{number}/index.md`", out)
        self.assertIn("[Search index](/index.json)", out)
        self.assertIn("[Cross-reference graph](/graph.json)", out)
        self.assertIn("https://github.com/0xB10C/github-metadata-mirror", out)

    def test_respects_base_url(self) -> None:
        out = render_llms_txt(_config(base_url="/mirror/"))
        self.assertIn("`/mirror/{number}/index.md`", out)
        self.assertIn("[Search index](/mirror/index.json)", out)
        self.assertIn("[Cross-reference graph](/mirror/graph.json)", out)


if __name__ == "__main__":
    unittest.main()
