from __future__ import annotations

import typing as t
from types import ModuleType

import pytest

import markupsafe
from markupsafe import _native

try:
    from markupsafe import _speedups
except ImportError:
    _speedups = None  # type: ignore


@pytest.fixture(
    scope="session",
    autouse=True,
    params=(
        _native,
        pytest.param(
            _speedups,
            marks=pytest.mark.skipif(_speedups is None, reason="speedups unavailable"),
        ),
    ),
)
def _mod(request: pytest.FixtureRequest) -> None:
    mod = t.cast(ModuleType, request.param)
    markupsafe._escape_inner = mod._escape_inner  # type: ignore[attr-defined]
