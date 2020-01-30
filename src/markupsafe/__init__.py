"""
Implements an escape function and a Markup string to replace HTML
special characters with safe representations.
"""
import re
import string
from collections import abc

__version__ = "2.0.0a1"

__all__ = ["Markup", "escape", "escape_silent", "soft_str", "soft_unicode"]

_striptags_re = re.compile(r"(<!--.*?-->|<[^>]*>)")
_entity_re = re.compile(r"&([^& ;]+);")


class Markup(str):
    """A string that is ready to be safely inserted into an HTML or XML
    document, either because it was escaped or because it was marked
    safe.

    Passing an object to the constructor converts it to text and wraps
    it to mark it safe without escaping. To escape the text, use the
    :meth:`escape` class method instead.

    >>> Markup("Hello, <em>World</em>!")
    Markup('Hello, <em>World</em>!')
    >>> Markup(42)
    Markup('42')
    >>> Markup.escape("Hello, <em>World</em>!")
    Markup('Hello &lt;em&gt;World&lt;/em&gt;!')

    This implements the ``__html__()`` interface that some frameworks
    use. Passing an object that implements ``__html__()`` will wrap the
    output of that method, marking it safe.

    >>> class Foo:
    ...     def __html__(self):
    ...         return '<a href="/foo">foo</a>'
    ...
    >>> Markup(Foo())
    Markup('<a href="/foo">foo</a>')

    This is a subclass of :class:`str`. It has the same methods, but
    escapes their arguments and returns a ``Markup`` instance.

    >>> Markup("<em>%s</em>") % ("foo & bar",)
    Markup('<em>foo &amp; bar</em>')
    >>> Markup("<em>Hello</em> ") + "<foo>"
    Markup('<em>Hello</em> &lt;foo&gt;')
    """

    __slots__ = ()

    def __new__(cls, base="", encoding=None, errors="strict"):
        if hasattr(base, "__html__"):
            base = base.__html__()
        if encoding is None:
            return super().__new__(cls, base)
        return super().__new__(cls, base, encoding, errors)

    def __html__(self):
        return self

    def __add__(self, other):
        if isinstance(other, str) or hasattr(other, "__html__"):
            return self.__class__(super().__add__(self.escape(other)))
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str) or hasattr(other, "__html__"):
            return self.escape(other).__add__(self)
        return NotImplemented

    def __mul__(self, num):
        if isinstance(num, int):
            return self.__class__(super().__mul__(num))
        return NotImplemented

    __rmul__ = __mul__

    def __mod__(self, arg):
        if isinstance(arg, tuple):
            arg = tuple(_MarkupEscapeHelper(x, self.escape) for x in arg)
        else:
            arg = _MarkupEscapeHelper(arg, self.escape)
        return self.__class__(super().__mod__(arg))

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def join(self, seq):
        return self.__class__(super().join(map(self.escape, seq)))

    join.__doc__ = str.join.__doc__

    def split(self, *args, **kwargs):
        return list(map(self.__class__, super().split(*args, **kwargs)))

    split.__doc__ = str.split.__doc__

    def rsplit(self, *args, **kwargs):
        return list(map(self.__class__, super().rsplit(*args, **kwargs)))

    rsplit.__doc__ = str.rsplit.__doc__

    def splitlines(self, *args, **kwargs):
        return list(map(self.__class__, super().splitlines(*args, **kwargs)))

    splitlines.__doc__ = str.splitlines.__doc__

    def unescape(self):
        """Convert escaped markup back into a text string. This replaces
        HTML entities with the characters they represent.

        >>> Markup("Main &raquo; <em>About</em>").unescape()
        'Main » <em>About</em>'
        """
        from ._constants import HTML_ENTITIES

        def handle_match(m):
            name = m.group(1)
            if name in HTML_ENTITIES:
                return chr(HTML_ENTITIES[name])
            try:
                if name[:2] in ("#x", "#X"):
                    return chr(int(name[2:], 16))
                elif name.startswith("#"):
                    return chr(int(name[1:]))
            except ValueError:
                pass
            # Don't modify unexpected input.
            return m.group()

        return _entity_re.sub(handle_match, str(self))

    def striptags(self):
        """:meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup("Main &raquo;\t<em>About</em>").striptags()
        'Main » About'
        """
        stripped = " ".join(_striptags_re.sub("", self).split())
        return Markup(stripped).unescape()

    @classmethod
    def escape(cls, s):
        """Escape a string. Calls :func:`escape` and ensures that for
        subclasses the correct type is returned.
        """
        rv = escape(s)
        if rv.__class__ is not cls:
            return cls(rv)
        return rv

    def make_simple_escaping_wrapper(name):  # noqa: B902
        orig = getattr(str, name)

        def func(self, *args, **kwargs):
            args = _escape_argspec(list(args), enumerate(args), self.escape)
            _escape_argspec(kwargs, kwargs.items(), self.escape)
            return self.__class__(orig(self, *args, **kwargs))

        func.__name__ = orig.__name__
        func.__doc__ = orig.__doc__
        return func

    for method in (
        "__getitem__",
        "capitalize",
        "title",
        "lower",
        "upper",
        "replace",
        "ljust",
        "rjust",
        "lstrip",
        "rstrip",
        "center",
        "strip",
        "translate",
        "expandtabs",
        "swapcase",
        "zfill",
    ):
        locals()[method] = make_simple_escaping_wrapper(method)

    del method, make_simple_escaping_wrapper

    def partition(self, sep):
        return tuple(map(self.__class__, super().partition(self.escape(sep))))

    def rpartition(self, sep):
        return tuple(map(self.__class__, super().rpartition(self.escape(sep))))

    def format(self, *args, **kwargs):
        formatter = EscapeFormatter(self.escape)
        kwargs = _MagicFormatMapping(args, kwargs)
        return self.__class__(formatter.vformat(self, args, kwargs))

    def __html_format__(self, format_spec):
        if format_spec:
            raise ValueError("Unsupported format specification for Markup.")
        return self


class _MagicFormatMapping(abc.Mapping):
    """This class implements a dummy wrapper to fix a bug in the Python
    standard library for string formatting.

    See http://bugs.python.org/issue13598 for information about why
    this is necessary.
    """

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs
        self._last_index = 0

    def __getitem__(self, key):
        if key == "":
            idx = self._last_index
            self._last_index += 1
            try:
                return self._args[idx]
            except LookupError:
                pass
            key = str(idx)
        return self._kwargs[key]

    def __iter__(self):
        return iter(self._kwargs)

    def __len__(self):
        return len(self._kwargs)


class EscapeFormatter(string.Formatter):
    def __init__(self, escape):
        self.escape = escape

    def format_field(self, value, format_spec):
        if hasattr(value, "__html_format__"):
            rv = value.__html_format__(format_spec)
        elif hasattr(value, "__html__"):
            if format_spec:
                raise ValueError(
                    f"Format specifier {format_spec} given, but {type(value)} does not"
                    " define __html_format__. A class that defines __html__ must define"
                    " __html_format__ to work with format specifiers."
                )
            rv = value.__html__()
        else:
            # We need to make sure the format spec is str here as
            # otherwise the wrong callback methods are invoked.
            rv = string.Formatter.format_field(self, value, str(format_spec))
        return str(self.escape(rv))


def _escape_argspec(obj, iterable, escape):
    """Helper for various string-wrapped functions."""
    for key, value in iterable:
        if isinstance(value, str) or hasattr(value, "__html__"):
            obj[key] = escape(value)
    return obj


class _MarkupEscapeHelper:
    """Helper for :meth:`Markup.__mod__`."""

    def __init__(self, obj, escape):
        self.obj = obj
        self.escape = escape

    def __getitem__(self, item):
        return _MarkupEscapeHelper(self.obj[item], self.escape)

    def __str__(self):
        return str(self.escape(self.obj))

    def __repr__(self):
        return str(self.escape(repr(self.obj)))

    def __int__(self):
        return int(self.obj)

    def __float__(self):
        return float(self.obj)


# circular import
try:
    from ._speedups import escape, escape_silent, soft_str, soft_unicode
except ImportError:
    from ._native import escape, escape_silent, soft_str, soft_unicode
