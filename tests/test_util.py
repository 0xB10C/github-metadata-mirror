"""Tests for mirror.util."""

from __future__ import annotations

import unittest

from mirror.util import (
    fnv1a_32,
    format_date_long,
    format_date_medium,
    format_time_short,
    format_datetime_utc,
    html_escape,
    urlize,
    truncate,
)
from datetime import datetime, timezone


class TestFnv1a32(unittest.TestCase):
    def test_empty_string(self) -> None:
        self.assertEqual(fnv1a_32(""), 0x811C9DC5)

    def test_known_values(self) -> None:
        # Known FNV-1a 32-bit test vectors
        self.assertEqual(fnv1a_32("a"), 0xE40C292C)
        self.assertEqual(fnv1a_32("foobar"), 0xBF9CF968)

    def test_label_color_deterministic(self) -> None:
        hue = fnv1a_32("bug") % 360
        self.assertIsInstance(hue, int)
        self.assertGreaterEqual(hue, 0)
        self.assertLess(hue, 360)
        # Same input always gives same output
        self.assertEqual(hue, fnv1a_32("bug") % 360)

    def test_unicode(self) -> None:
        # Should hash UTF-8 bytes
        result = fnv1a_32("cafe\u0301")
        self.assertIsInstance(result, int)


class TestDateFormatting(unittest.TestCase):
    def test_format_date_long(self) -> None:
        self.assertEqual(format_date_long("2006-01-02T15:04:05Z"), "January 2, 2006")
        self.assertEqual(format_date_long("2023-12-25T00:00:00Z"), "December 25, 2023")

    def test_format_date_medium(self) -> None:
        self.assertEqual(format_date_medium("2006-01-02T15:04:05Z"), "Jan 2, 2006")
        self.assertEqual(format_date_medium("2023-12-25T00:00:00Z"), "Dec 25, 2023")

    def test_format_time_short(self) -> None:
        self.assertEqual(format_time_short("2006-01-02T15:04:05Z"), "3:04 PM")
        self.assertEqual(format_time_short("2006-01-02T00:00:00Z"), "12:00 AM")
        self.assertEqual(format_time_short("2006-01-02T12:00:00Z"), "12:00 PM")
        self.assertEqual(format_time_short("2006-01-02T09:05:00Z"), "9:05 AM")

    def test_format_datetime_utc(self) -> None:
        dt = datetime(2006, 1, 2, 15, 4, 0, tzinfo=timezone.utc)
        self.assertEqual(format_datetime_utc(dt), "2006-01-02 15:04 UTC")


class TestHtmlEscape(unittest.TestCase):
    def test_escapes_special_chars(self) -> None:
        self.assertEqual(html_escape('<script>alert("xss")</script>'),
                         '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')

    def test_ampersand(self) -> None:
        self.assertEqual(html_escape("a & b"), "a &amp; b")

    def test_plain_text(self) -> None:
        self.assertEqual(html_escape("hello"), "hello")


class TestUrlize(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(urlize("Bug"), "bug")

    def test_spaces_to_hyphens(self) -> None:
        self.assertEqual(urlize("Good First Issue"), "good-first-issue")

    def test_special_chars_stripped(self) -> None:
        self.assertEqual(urlize("C++ / feature"), "c-feature")

    def test_already_lowercase(self) -> None:
        self.assertEqual(urlize("refactoring"), "refactoring")


class TestTruncate(unittest.TestCase):
    def test_short_string(self) -> None:
        self.assertEqual(truncate("abc", 10), "abc")

    def test_exact_length(self) -> None:
        self.assertEqual(truncate("abcdefghij", 10), "abcdefghij")

    def test_truncates(self) -> None:
        self.assertEqual(truncate("abcdefghijklmnop", 10), "abcdefghij")


if __name__ == "__main__":
    unittest.main()
