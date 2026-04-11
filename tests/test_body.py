"""Tests for mirror.body — ported from layouts/partials/regex-tests.html.

These test the regex link rewriting in render_body. Since our markdown
renderer is still being debugged, we use a minimal stub that converts
[text](url) links to <a> tags but otherwise passes text through. This
isolates the regex logic from markdown edge cases.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from mirror.body import render_body
from mirror.config import Config


class StubMarkdownRenderer:
    """Minimal markdown renderer that only converts [text](url) to <a> tags.

    This isolates the body regex tests from full markdown rendering.
    """

    def render(self, text: str) -> str:
        # Convert markdown links to HTML links
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2">\1</a>',
            text,
        )
        return text


def _cfg() -> Config:
    return Config(
        title="Test",
        owner="test-owner",
        repository="test-repo",
        footer="",
        base_url="/",
        input_dir=Path("/tmp"),
        output_dir=Path("/tmp"),
    )


class TestRenderBodyRegex(unittest.TestCase):
    """Tests ported from layouts/partials/regex-tests.html."""

    def setUp(self) -> None:
        self.cfg = _cfg()
        self.md = StubMarkdownRenderer()

    def _render(self, body: str) -> str:
        result = render_body(body, self.cfg, self.md)
        # Normalize whitespace for comparison (Hugo strips newlines in tests)
        return result.replace("\n", "")

    def test_normal_text(self) -> None:
        self.assertIn("normal text", self._render("normal text"))

    def test_issue_reference(self) -> None:
        result = self._render("a whlie (see #20487) it is time")
        self.assertIn('<a href="/20487/">#20487</a>', result)

    def test_multiple_issue_references(self) -> None:
        result = self._render("See e.g. #24659 #24369 #24340 #23555.")
        self.assertIn('<a href="/24659/">#24659</a>', result)
        self.assertIn('<a href="/24369/">#24369</a>', result)
        self.assertIn('<a href="/24340/">#24340</a>', result)
        self.assertIn('<a href="/23555/">#23555</a>', result)

    def test_bare_pull_url(self) -> None:
        result = self._render("See https://github.com/test-owner/test-repo/pull/20233 for details")
        self.assertIn('<a href="/20233/">#20233</a>', result)

    def test_bare_issue_url_colon(self) -> None:
        result = self._render("See https://github.com/test-owner/test-repo/issues/1337: it is good")
        self.assertIn('<a href="/1337/">#1337</a>', result)

    def test_bare_issue_url_space(self) -> None:
        result = self._render("See https://github.com/test-owner/test-repo/issues/1337 for details")
        self.assertIn('<a href="/1337/">#1337</a>', result)

    def test_pull_issuecomment_url(self) -> None:
        result = self._render("See https://github.com/test-owner/test-repo/pull/20233#issuecomment-715884174 for details")
        self.assertIn('<a href="/20233/#issuecomment-715884174">#20233 (comment)</a>', result)

    def test_issue_issuecomment_url(self) -> None:
        result = self._render("my review from https://github.com/test-owner/test-repo/issues/20205#issuecomment-716544104,")
        self.assertIn('<a href="/20205/#issuecomment-716544104">#20205 (comment)</a>', result)

    def test_pull_issuecomment_url_dot(self) -> None:
        result = self._render("my review from https://github.com/test-owner/test-repo/pull/20205#issuecomment-716544104.")
        self.assertIn('<a href="/20205/#issuecomment-716544104">#20205 (comment)</a>', result)

    def test_pull_issuecomment_url_space(self) -> None:
        result = self._render("my review from https://github.com/test-owner/test-repo/pull/20205#issuecomment-716544104 abc")
        self.assertIn('<a href="/20205/#issuecomment-716544104">#20205 (comment)</a>', result)

    def test_pull_issuecomment_url_excl(self) -> None:
        result = self._render("my review from https://github.com/test-owner/test-repo/pull/20205#issuecomment-716544104!")
        self.assertIn('<a href="/20205/#issuecomment-716544104">#20205 (comment)</a>', result)

    def test_markdown_formatted_issuecomment_link(self) -> None:
        result = self._render("on the mailinglist ([#28132 (comment)](https://github.com/test-owner/test-repo/pull/28132#issuecomment-1657206487)).\n")
        self.assertIn('<a href="/28132/#issuecomment-1657206487">#28132 (comment)</a>', result)

    def test_wrong_owner_repo_not_rewritten(self) -> None:
        result = self._render("interesting owner:repo name https://github.com/wrong-owner/wrong-repo/pull/20205#issuecomment-716544104!")
        # Should NOT be rewritten to a local link
        self.assertNotIn('<a href="/20205/#issuecomment-716544104">', result)

    def test_pull_files_url_not_rewritten(self) -> None:
        result = self._render("files https://github.com/test-owner/test-repo/pull/20205/files-abc")
        # /files-abc path should NOT be rewritten to local link
        self.assertNotIn('<a href="/20205/">', result)

    def test_discussion_review_url(self) -> None:
        result = self._render("at https://github.com/test-owner/test-repo/pull/20233#discussion_r682768076.")
        self.assertIn('<a href="/20233/#discussion_r682768076">#20233 (review)</a>', result)

    def test_markdown_pullrequestreview_link(self) -> None:
        result = self._render("[dergoegge](https://github.com/test-owner/test-repo/pull/27875#pullrequestreview-1477330163)")
        self.assertIn('<a href="/27875/#pullrequestreview-1477330163">dergoegge</a>', result)

    def test_markdown_issuecomment_link(self) -> None:
        result = self._render("[hebasto](https://github.com/test-owner/test-repo/pull/27875#issuecomment-1589290446)")
        self.assertIn('<a href="/27875/#issuecomment-1589290446">hebasto</a>', result)

    def test_at_mention(self) -> None:
        result = self._render("@0xb10c ")
        self.assertIn('<a href="/contributor/0xb10c/">@0xb10c</a>', result)

    def test_at_mention_multiple(self) -> None:
        result = self._render("@test1 @test2")
        self.assertIn('<a href="/contributor/test1/">@test1</a>', result)
        self.assertIn('<a href="/contributor/test2/">@test2</a>', result)

    def test_at_mention_with_hyphen(self) -> None:
        result = self._render("@t-bast")
        self.assertIn('<a href="/contributor/t-bast/">@t-bast</a>', result)

    def test_at_mention_case_insensitive_path(self) -> None:
        result = self._render("@MarkoFalke")
        self.assertIn('<a href="/contributor/markofalke/">@MarkoFalke</a>', result)

    def test_commit_hash_40_chars(self) -> None:
        result = self._render("A-CK 1ac09b93cdb41eb7dbc1a62364363e59507da1af.")
        self.assertIn("<span class='font-monospace text-info'>1ac09b93cdb41eb7dbc1a62364363e59507da1af</span>", result)

    def test_commit_hash_8_chars(self) -> None:
        result = self._render("NA-CK 1ac09b93,")
        self.assertIn("<span class='font-monospace text-info'>1ac09b93</span>", result)

    def test_commit_hash_10_chars(self) -> None:
        result = self._render("utA-CK 1ac09bb10c,")
        self.assertIn("<span class='font-monospace text-info'>1ac09bb10c</span>", result)

    def test_ack_highlight(self) -> None:
        for ack in ["utACK", "tACK", "ACK", "NACK", "Concept ACK", "Approach ACK"]:
            with self.subTest(ack=ack):
                result = self._render(f"{ack} commit")
                self.assertIn(f"<b class='text-warning'>{ack}</b>", result)

    def test_empty_body(self) -> None:
        result = self._render("")
        self.assertIn("No description provided", result)

    def test_none_body(self) -> None:
        result = render_body(None, self.cfg, self.md)
        self.assertIn("No description provided", result)


if __name__ == "__main__":
    unittest.main()
