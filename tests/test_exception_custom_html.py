from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from .conftest import TPEscape


class CustomHtmlThatRaises:
    def __html__(self) -> str:
        raise ValueError(123)


def test_exception_custom_html(escape: TPEscape) -> None:
    """Checks whether exceptions in custom __html__ implementations are
    propagated correctly.

    There was a bug in the native implementation at some point:
    https://github.com/pallets/markupsafe/issues/108
    """
    obj = CustomHtmlThatRaises()
    with pytest.raises(ValueError):
        escape(obj)
