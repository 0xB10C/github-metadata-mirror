"""Body text processing: regex link rewriting + markdown rendering.

Port of layouts/partials/render-body.html. The regex replacements must
be applied in the exact order defined here.
"""

from __future__ import annotations

import re

from mirror.config import Config
from mirror.markdown import MarkdownRenderer

DEFAULT_BODY = "_No description provided._"

# Static patterns pre-compiled at module level (owner/repo patterns are config-dependent
# and compiled per-call below).
_RE_ISSUE_REF = re.compile(r"(\s|^)#([0-9]+)")
_RE_AT_MENTION = re.compile(r"(\s|^)+@([a-zA-Z0-9-]+)(\s|$|\.|,|@|\?|\')*?")
_RE_CODE_FENCE_BRACE = re.compile(r"```(.+)\{(.*)\r?\n")
_RE_COMMIT_HASH = re.compile(r"(\s|^)([a-f0-9]{7,40})(\s|$|\W)")
_RE_ACK = re.compile(
    r"(^|\s|\W)(ACK|utACK|tACK|ack|re-ack|reACK|NACK|NAck|nack|Concept ACK|Concept NACK|crACK|cACK|Approach NACK|Approach ACK|approach ACK|Code review ACK|Stale ACK)(\s|$|\W)"
)


def render_body(body: str | None, config: Config, md: MarkdownRenderer) -> str:
    """Process a comment/issue/PR body: rewrite links, convert markdown, post-process.

    Args:
        body: Raw markdown body text (may be None or empty).
        config: Site configuration (owner, repository, base_url).
        md: Markdown renderer implementation.

    Returns:
        Safe HTML string.
    """
    if not body:
        body = DEFAULT_BODY

    base_url = config.base_url
    o = re.escape(config.owner)
    r = re.escape(config.repository)

    # --- Pre-markdown regex replacements (operating on markdown text) ---

    # 1. #123 -> local links (MUST be first — later replacements would override)
    body = _RE_ISSUE_REF.sub(rf"\1[#\2]({base_url}\2/)", body)

    # 2. Markdown-formatted GitHub URLs: ](https://github.com/owner/repo/...)
    body = re.sub(
        rf"\]\(https://github\.com/{o}/{r}/pull/([0-9]+)#issuecomment-([0-9]+)\)",
        rf"]({base_url}\1/#issuecomment-\2)",
        body,
    )
    body = re.sub(
        rf"\]\(https://github\.com/{o}/{r}/issues/([0-9]+)#issuecomment-([0-9]+)\)",
        rf"]({base_url}\1/#issuecomment-\2)",
        body,
    )
    body = re.sub(
        rf"\]\(https://github\.com/{o}/{r}/pull/([0-9]+)#pullrequestreview-([0-9]+)\)",
        rf"]({base_url}\1/#pullrequestreview-\2)",
        body,
    )

    # 3. Bare GitHub URLs with comment/review anchors
    body = re.sub(
        rf"(\s|^)https://github\.com/{o}/{r}/pull/([0-9]+)#issuecomment-([0-9]+)",
        rf"\1[#\2 (comment)]({base_url}\2/#issuecomment-\3)",
        body,
    )
    body = re.sub(
        rf"(\s|^)https://github\.com/{o}/{r}/issues/([0-9]+)#issuecomment-([0-9]+)",
        rf"\1[#\2 (comment)]({base_url}\2/#issuecomment-\3)",
        body,
    )

    # 4. Discussion review links
    body = re.sub(
        rf"(\s|^)https://github\.com/{o}/{r}/pull/([0-9]+)#discussion_r([0-9]+)",
        rf"\1[#\2 (review)]({base_url}\2/#discussion_r\3)",
        body,
    )

    # 5. Bare issue/pull URLs (not followed by / or digit, to avoid /files /commits)
    body = re.sub(
        rf"(\s|^)https://github\.com/{o}/{r}/pull/([0-9]+)([^\/0-9])",
        rf"\1[#\2]({base_url}\2/)\3",
        body,
    )
    body = re.sub(
        rf"(\s|^)https://github\.com/{o}/{r}/issues/([0-9]+)([^\/0-9])",
        rf"\1[#\2]({base_url}\2/)\3",
        body,
    )

    # 6. @username -> contributor profile links (lowercased in one pass)
    body = _RE_AT_MENTION.sub(
        lambda m: f"{m.group(1)}[@{m.group(2)}]({base_url}contributor/{m.group(2).lower()}/){m.group(3) or ''}",
        body,
    )

    # 7. Fix markdown code fence curly-brace attribute issue
    body = _RE_CODE_FENCE_BRACE.sub(r"```\n\1{\2\n", body)

    # --- Markdown -> HTML ---
    html = md.render(body)

    # --- Post-markdown processing (operating on HTML) ---

    # 8. Commit hash highlighting (7-40 hex chars)
    html = _RE_COMMIT_HASH.sub(r"\1<span class='font-monospace text-info'>\2</span>\3", html)

    # 9. ACK/NACK highlighting
    html = _RE_ACK.sub(r"\1<b class='text-warning'>\2</b>\3", html)

    # 10. Table -> responsive Bootstrap table wrapping
    html = html.replace("<table>", "<div class='table-responsive'><table class='table'>")
    html = html.replace("</table>", "</table></div>")

    return html
