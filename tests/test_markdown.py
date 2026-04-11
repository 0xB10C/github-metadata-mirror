"""Tests for mirror.markdown."""

from __future__ import annotations

import unittest

from mirror.markdown import MarkdownRenderer


class TestMarkdown(unittest.TestCase):
    def setUp(self) -> None:
        self.md = MarkdownRenderer()

    # Headings
    def test_heading_h1(self) -> None:
        self.assertIn("<h1>Title</h1>", self.md.render("# Title"))

    def test_heading_h3(self) -> None:
        self.assertIn("<h3>Subtitle</h3>", self.md.render("### Subtitle"))

    # Bold and italic
    def test_bold(self) -> None:
        result = self.md.render("**bold**")
        self.assertIn("<strong>bold</strong>", result)

    def test_italic(self) -> None:
        result = self.md.render("*italic*")
        self.assertIn("<em>italic</em>", result)

    def test_bold_italic(self) -> None:
        result = self.md.render("***bold italic***")
        self.assertIn("bold italic", result)

    def test_strikethrough(self) -> None:
        result = self.md.render("~~deleted~~")
        self.assertIn("<del>deleted</del>", result)

    # Inline code
    def test_inline_code(self) -> None:
        result = self.md.render("`code here`")
        self.assertIn("<code>code here</code>", result)

    # Code blocks
    def test_fenced_code_block(self) -> None:
        text = "```python\ndef hello():\n    pass\n```"
        result = self.md.render(text)
        self.assertIn("def hello():", result)

    def test_fenced_code_block_no_lang(self) -> None:
        text = "```\nsome code\n```"
        result = self.md.render(text)
        self.assertIn("some code", result)

    # Links
    def test_link(self) -> None:
        result = self.md.render("[text](http://example.com)")
        self.assertIn("http://example.com", result)
        self.assertIn("text", result)

    # Images
    def test_image(self) -> None:
        result = self.md.render("![alt text](http://img.png)")
        self.assertIn("http://img.png", result)
        self.assertIn("alt text", result)

    # Lists
    def test_unordered_list(self) -> None:
        text = "- item 1\n- item 2\n- item 3"
        result = self.md.render(text)
        self.assertIn("<ul>", result)
        self.assertIn("item 1", result)

    def test_ordered_list(self) -> None:
        text = "1. first\n2. second\n3. third"
        result = self.md.render(text)
        self.assertIn("<ol>", result)
        self.assertIn("first", result)

    # Blockquotes
    def test_blockquote(self) -> None:
        result = self.md.render("> quoted text")
        self.assertIn("<blockquote>", result)
        self.assertIn("quoted text", result)

    # Tables
    def test_table(self) -> None:
        text = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        result = self.md.render(text)
        self.assertIn("<table>", result)
        self.assertIn("A", result)
        self.assertIn("1", result)

    # Horizontal rule
    def test_horizontal_rule(self) -> None:
        result = self.md.render("---")
        self.assertIn("<hr", result)

    # Paragraphs
    def test_paragraph(self) -> None:
        result = self.md.render("Hello world")
        self.assertIn("Hello world", result)

    def test_two_paragraphs(self) -> None:
        result = self.md.render("Para 1\n\nPara 2")
        self.assertIn("Para 1", result)
        self.assertIn("Para 2", result)

    # HTML escaping
    def test_html_escaped(self) -> None:
        text = "Text with <b>bold</b> html"
        result = self.md.render(text)
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", result)

    # Empty input
    def test_empty(self) -> None:
        self.assertEqual(self.md.render(""), "")


if __name__ == "__main__":
    unittest.main()
