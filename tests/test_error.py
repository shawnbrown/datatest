# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest.__past__.api07_diffs import xMissing
from datatest.error import xDataError


class TestDataError(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(xDataError, AssertionError))

    def test_instantiation(self):
        xDataError('column names', xMissing('foo'))
        xDataError('column names', [xMissing('foo')])
        xDataError('column names', {'foo': xMissing('bar')})
        xDataError('column names', {('foo', 'bar'): xMissing('baz')})

        with self.assertRaises(ValueError, msg='Empty error should raise exception.'):
            xDataError(msg='', differences={})

    def test_repr(self):
        error = xDataError('different columns', [xMissing('foo')])
        pattern = "xDataError: different columns:\n xMissing('foo')"
        self.assertEqual(repr(error), pattern)

        error = xDataError('different columns', xMissing('foo'))
        pattern = "xDataError: different columns:\n xMissing('foo')"
        self.assertEqual(repr(error), pattern)

        # Test pprint lists.
        error = xDataError('different columns', [xMissing('foo'),
                                                xMissing('bar')])
        pattern = ("xDataError: different columns:\n"
                   " xMissing('foo'),\n"
                   " xMissing('bar')")
        self.assertEqual(repr(error), pattern)

        # Test dictionary.
        error = xDataError('different columns', {'FOO': xMissing('bar')})
        pattern = ("xDataError: different columns:\n"
                   " 'FOO': xMissing('bar')")
        self.assertEqual(repr(error), pattern)

    def test_verbose_repr(self):
        reference = 'reference-data-source'
        subject = 'subject-data-source'
        error = xDataError('different columns', [xMissing('foo')], subject, reference)
        error._verbose = True  # <- Set verbose flag, here!

        pattern = ("xDataError: different columns:\n"
                   " xMissing('foo')\n"
                   "\n"
                   "SUBJECT:\n"
                   "subject-data-source\n"
                   "REQUIRED:\n"
                   "reference-data-source")
        self.assertEqual(repr(error), pattern)
