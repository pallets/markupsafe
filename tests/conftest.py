from __future__ import annotations

import typing as t
from types import ModuleType

import pytest

from markupsafe import _native
from markupsafe import Markup

try:
    from markupsafe import _speedups
except ImportError:
    _speedups = None  # type: ignore

if t.TYPE_CHECKING:
    import typing_extensions as te

    class TPEscape(te.Protocol):
        def __call__(self, s: t.Any) -> Markup:
            ...

    class TPEscapeSilent(te.Protocol):
        def __call__(self, s: t.Any | None) -> Markup:
            ...

    class TPSoftStr(te.Protocol):
        def __call__(self, s: t.Any) -> str:
            ...


@pytest.fixture(
    scope="session",
    params=(
        _native,
        pytest.param(
            _speedups,
            marks=pytest.mark.skipif(_speedups is None, reason="speedups unavailable"),
        ),
    ),
)
def _mod(request: pytest.FixtureRequest) -> ModuleType:
    return t.cast(ModuleType, request.param)


@pytest.fixture(scope="session")
def escape(_mod: ModuleType) -> TPEscape:
    return t.cast("TPEscape", _mod.escape)


@pytest.fixture(scope="session")
def escape_silent(_mod: ModuleType) -> TPEscapeSilent:
    return t.cast("TPEscapeSilent", _mod.escape_silent)


@pytest.fixture(scope="session")
def soft_str(_mod: ModuleType) -> t.Callable[[t.Any], str]:
    return t.cast("t.Callable[[t.Any], str]", _mod.soft_str)
