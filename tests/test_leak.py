from __future__ import annotations

import gc
import platform

import pytest

from markupsafe import _escape_inner  # type: ignore[attr-defined]
from markupsafe import escape


@pytest.mark.skipif(
    _escape_inner.__module__ == "markupsafe._native",
    reason="only test memory leak with speedups",
)
def test_markup_leaks() -> None:
    counts = set()

    for _i in range(20):
        for _j in range(1000):
            escape("foo")
            escape("<foo>")
            escape("foo")
            escape("<foo>")

        if platform.python_implementation() == "PyPy":
            gc.collect()

        counts.add(len(gc.get_objects()))

    assert len(counts) == 1
