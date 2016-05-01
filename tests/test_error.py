# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest.differences import Missing
from datatest.error import DataAssertionError


class TestDataAssertionError(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(DataAssertionError, AssertionError))

    def test_instantiation(self):
        DataAssertionError('column names', Missing('foo'))
        DataAssertionError('column names', [Missing('foo')])
        DataAssertionError('column names', {'Explanation here.': Missing('foo')})
        DataAssertionError('column names', {'Explanation here.': [Missing('foo')]})

        with self.assertRaises(ValueError, msg='Empty error should raise exception.'):
            DataAssertionError(msg='', differences={})

    def test_repr(self):
        error = DataAssertionError('different columns', [Missing('foo')])
        pattern = "DataAssertionError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        error = DataAssertionError('different columns', Missing('foo'))
        pattern = "DataAssertionError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        # Test pprint lists.
        error = DataAssertionError('different columns', [Missing('foo'),
                                                         Missing('bar')])
        pattern = ("DataAssertionError: different columns:\n"
                   " Missing('foo'),\n"
                   " Missing('bar')")
        self.assertEqual(repr(error), pattern)

        # Test dictionary with nested list.
        error = DataAssertionError('different columns', {'Omitted': [Missing('foo'),
                                                                     Missing('bar'),
                                                                     Missing('baz')]})
        pattern = ("DataAssertionError: different columns:\n"
                   " 'Omitted': [Missing('foo'),\n"
                   "             Missing('bar'),\n"
                   "             Missing('baz')]")
        self.assertEqual(repr(error), pattern)

    def test_verbose_repr(self):
        reference = 'reference-data-source'
        subject = 'subject-data-source'
        error = DataAssertionError('different columns', [Missing('foo')], subject, reference)
        error._verbose = True  # <- Set verbose flag, here!

        pattern = ("DataAssertionError: different columns:\n"
                   " Missing('foo')\n"
                   "\n"
                   "SUBJECT:\n"
                   "subject-data-source\n"
                   "REQUIRED:\n"
                   "reference-data-source")
        self.assertEqual(repr(error), pattern)
