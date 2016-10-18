# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest.differences import Missing
from datatest.error import DataError


class TestDataError(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(DataError, AssertionError))

    def test_instantiation(self):
        DataError('column names', Missing('foo'))
        DataError('column names', [Missing('foo')])
        DataError('column names', {'foo': Missing('bar')})
        DataError('column names', {('foo', 'bar'): Missing('baz')})

        with self.assertRaises(ValueError, msg='Empty error should raise exception.'):
            DataError(msg='', differences={})

    def test_repr(self):
        error = DataError('different columns', [Missing('foo')])
        pattern = "DataError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        error = DataError('different columns', Missing('foo'))
        pattern = "DataError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        # Test pprint lists.
        error = DataError('different columns', [Missing('foo'),
                                                Missing('bar')])
        pattern = ("DataError: different columns:\n"
                   " Missing('foo'),\n"
                   " Missing('bar')")
        self.assertEqual(repr(error), pattern)

        # Test dictionary.
        error = DataError('different columns', {'FOO': Missing('bar')})
        pattern = ("DataError: different columns:\n"
                   " 'FOO': Missing('bar')")
        self.assertEqual(repr(error), pattern)

    def test_verbose_repr(self):
        reference = 'reference-data-source'
        subject = 'subject-data-source'
        error = DataError('different columns', [Missing('foo')], subject, reference)
        error._verbose = True  # <- Set verbose flag, here!

        pattern = ("DataError: different columns:\n"
                   " Missing('foo')\n"
                   "\n"
                   "SUBJECT:\n"
                   "subject-data-source\n"
                   "REQUIRED:\n"
                   "reference-data-source")
        self.assertEqual(repr(error), pattern)
