from __future__ import annotations

import typing as t

def escape_inner(s: str, /) -> str:
    return s
        .replace("&", "&amp;")
        .replace(">", "&gt;")
        .replace("<", "&lt;")
        .replace("'", "&#39;")
        .replace('"', "&#34;")
