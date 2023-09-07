from __future__ import annotations

import typing as t

import pytest

from markupsafe import Markup

if t.TYPE_CHECKING:
    from .conftest import TPEscape


@pytest.mark.parametrize(
    ("value", "expect"),
    (
        # empty
        ("", ""),
        # ascii
        ("abcd&><'\"efgh", "abcd&amp;&gt;&lt;&#39;&#34;efgh"),
        ("&><'\"efgh", "&amp;&gt;&lt;&#39;&#34;efgh"),
        ("abcd&><'\"", "abcd&amp;&gt;&lt;&#39;&#34;"),
        # 2 byte
        ("こんにちは&><'\"こんばんは", "こんにちは&amp;&gt;&lt;&#39;&#34;こんばんは"),
        ("&><'\"こんばんは", "&amp;&gt;&lt;&#39;&#34;こんばんは"),
        ("こんにちは&><'\"", "こんにちは&amp;&gt;&lt;&#39;&#34;"),
        # 4 byte
        (
            "\U0001F363\U0001F362&><'\"\U0001F37A xyz",
            "\U0001F363\U0001F362&amp;&gt;&lt;&#39;&#34;\U0001F37A xyz",
        ),
        ("&><'\"\U0001F37A xyz", "&amp;&gt;&lt;&#39;&#34;\U0001F37A xyz"),
        ("\U0001F363\U0001F362&><'\"", "\U0001F363\U0001F362&amp;&gt;&lt;&#39;&#34;"),
    ),
)
def test_escape(escape: TPEscape, value: str, expect: str) -> None:
    assert escape(value) == Markup(expect)
