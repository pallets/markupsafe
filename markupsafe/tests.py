# -*- coding: utf-8 -*-
import gc
import unittest
from markupsafe import Markup, escape, escape_silent


class MarkupTestCase(unittest.TestCase):

    def test_markup_operations(self):
        # adding two strings should escape the unsafe one
        unsafe = '<script type="application/x-some-script">alert("foo");</script>'
        safe = Markup('<em>username</em>')
        assert unsafe + safe == unicode(escape(unsafe)) + unicode(safe)

        # string interpolations are safe to use too
        assert Markup('<em>%s</em>') % '<bad user>' == \
               '<em>&lt;bad user&gt;</em>'
        assert Markup('<em>%(username)s</em>') % {
            'username': '<bad user>'
        } == '<em>&lt;bad user&gt;</em>'

        # an escaped object is markup too
        assert type(Markup('foo') + 'bar') is Markup

        # and it implements __html__ by returning itself
        x = Markup("foo")
        assert x.__html__() is x

        # it also knows how to treat __html__ objects
        class Foo(object):
            def __html__(self):
                return '<em>awesome</em>'
            def __unicode__(self):
                return 'awesome'
        assert Markup(Foo()) == '<em>awesome</em>'
        assert Markup('<strong>%s</strong>') % Foo() == \
               '<strong><em>awesome</em></strong>'

        # escaping
        assert escape('"<>&\'') == '&#34;&lt;&gt;&amp;&#39;'
        assert Markup("<em>Foo &amp; Bar</em>").striptags() == "Foo & Bar"

    def test_unescape(self):
        assert Markup("&lt;test&gt;").unescape() == "<test>"

        assert "jack & tavi are cooler than mike & russ" == \
                Markup("jack & tavi are cooler than mike &amp; russ").unescape(), \
                Markup("jack & tavi are cooler than mike &amp; russ").unescape()

        # Test that unescape is idempotent
        original = '&foo&#x3b;'
        once = Markup(original).unescape()
        twice = Markup(once).unescape()
        expected = "&foo;"
        assert expected == once == twice, (once, twice)

    def test_formatting(self):
        assert Markup('%i') % 3.14 == '3'
        assert Markup('%.2f') % 3.14159 == '3.14'
        assert Markup('%s %s %s') % ('<',123,'>') == '&lt; 123 &gt;'
        assert Markup('<em>{awesome}</em>').format(awesome='<awesome>') == \
                '<em>&lt;awesome&gt;</em>'


    def test_all_set(self):
        import markupsafe as markup
        for item in markup.__all__:
            getattr(markup, item)

    def test_escape_silent(self):
        assert escape_silent(None) == Markup()
        assert escape(None) == Markup(None)
        assert escape_silent('<foo>') == Markup(u'&lt;foo&gt;')


class MarkupLeakTestCase(unittest.TestCase):

    def test_markup_leaks(self):
        counts = set()
        for count in xrange(20):
            for item in xrange(1000):
                escape("foo")
                escape("<foo>")
                escape(u"foo")
                escape(u"<foo>")
            counts.add(len(gc.get_objects()))
        assert len(counts) == 1, 'ouch, c extension seems to leak objects'

class EncodedMarkup(Markup):
    __slots__ = ()
    encoding = 'utf8'

    @classmethod
    def escape(cls, s):
        if isinstance(s, str):
            s = s.decode('utf8')
        return super(EncodedMarkup, cls).escape(s)

class MarkupSubclassTestCase(unittest.TestCase):
    # The Russian name of Russia (Rossija)
    russia = u'Россия'
    utf8 = russia.encode('utf8')

    def test_escape(self):
        myval = EncodedMarkup.escape(self.utf8)
        assert myval == self.russia, repr(myval)
    def test_add(self):
        myval = EncodedMarkup() + self.utf8
        assert myval == self.russia, repr(myval)
    def test_radd(self):
        myval = self.utf8 + EncodedMarkup()
        assert myval == self.russia, repr(myval)
    def test_join(self):
        myval = EncodedMarkup().join([self.utf8])
        assert myval == self.russia, repr(myval)
    def test_partition(self):
        assert EncodedMarkup(self.russia).partition(self.utf8)[1] == self.russia
        assert EncodedMarkup(self.russia).rpartition(self.utf8)[1] == self.russia
    def test_mod(self):
        assert EncodedMarkup('%s') % self.utf8 == self.russia
        assert EncodedMarkup('%r') % self.utf8 == escape(repr(self.utf8))
    def test_strip(self):
        assert EncodedMarkup(self.russia).strip(self.utf8) == u''
        assert EncodedMarkup(self.russia).rstrip(self.utf8) == u''


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MarkupTestCase))
    suite.addTest(unittest.makeSuite(MarkupSubclassTestCase))

    # this test only tests the c extension
    if not hasattr(escape, 'func_code'):
        suite.addTest(unittest.makeSuite(MarkupLeakTestCase))

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')

# vim:sts=4:sw=4:et:
