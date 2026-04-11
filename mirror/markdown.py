"""Markdown to HTML converter using mistune."""

from __future__ import annotations

import mistune


class MarkdownRenderer:
    """Mistune-based markdown renderer. Handles the full GFM subset used
    in GitHub issue/PR comments: fenced code blocks, tables, strikethrough,
    task lists, autolinks, etc.
    """

    def __init__(self) -> None:
        self._md = mistune.create_markdown(
            plugins=["strikethrough", "table", "url", "task_lists"],
        )

    def render(self, text: str) -> str:
        if not text:
            return ""
        result = self._md(text)
        return result or ""
