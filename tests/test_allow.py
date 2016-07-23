# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest import DataError
from datatest import Missing
from datatest import Extra
from datatest.allow import allow_iter
from datatest.allow import allow_each
from datatest.allow import _walk_diff

# NOTE!!!: Currently, the allowance context managers are being tested
# as methods of DataTestCase (in test_case.py).  In the future, after
# refactoring the allowances to also work with py.test, the tests for
# these classes should be moved out of test_case and into this
# sub-module.

class TestAllowIter(unittest.TestCase):
    def test_function_all_bad(self):
        function = lambda iterable: iterable  # <- Rejects everything.
        in_diffs = [
            Extra('foo'),
            Extra('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_iter(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, in_diffs)

    def test_function_all_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.

        with allow_iter(function, 'example allowance'):
            raise DataError('example error', [Missing('foo'), Missing('bar')])

    def test_function_some_ok(self):
        function = lambda iterable: (x for x in iterable if x.value != 'bar')
        in_diffs = [
            Missing('foo'),
            Missing('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_iter(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('foo')])

    def test_kwds_all_bad(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Using keyword bbb='j' should reject all in_diffs.
            with allow_iter(function, 'example allowance', bbb='j'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, in_diffs)

    def test_kwds_all_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        # Using keyword aaa='x' should accept all in_diffs.
        with allow_iter(function, 'example allowance', aaa='x'):
            raise DataError('example error', in_diffs)

        # Using keyword bbb=['y', 'z'] should also accept all in_diffs.
        with allow_iter(function, 'example allowance', bbb=['y', 'z']):
            raise DataError('example error', in_diffs)

    def test_kwds_some_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Keyword bbb='y' should reject second in_diffs element.
            with allow_iter(function, 'example allowance', bbb='y'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('bar', aaa='x', bbb='z')])

    def test_no_exception(self):
        function = lambda iterable: list()  # <- Accepts everything.

        with self.assertRaises(AssertionError) as cm:
            with allow_iter(function):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('Allowed differences not found: <lambda>', str(exc))


class TestAllowEach(unittest.TestCase):
    """Using allow_each() requires an element-wise function."""
    def test_allow_some(self):
        function = lambda x: x.value == 'bar'
        in_diffs = [
            Missing('foo'),
            Missing('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_each(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('foo')])

    def test_allow_all(self):
        function = lambda x: isinstance(x, Missing)  # <- Allow only missing.

        with allow_each(function, 'example allowance'):
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_kwds(self):
        function = lambda x: True  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Keyword bbb='y' should reject second in_diffs element.
            with allow_each(function, 'example allowance', bbb='y'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('bar', aaa='x', bbb='z')])

    def test_no_exception(self):
        function = lambda x: False  # <- Rejects everything.

        with self.assertRaises(AssertionError) as cm:
            with allow_each(function):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('Allowed differences not found: <lambda>', str(exc))


class TestWalkValues(unittest.TestCase):
    def test_list_input(self):
        # Flat.
        generator = _walk_diff([Missing('val1'),
                                Missing('val2')])
        self.assertEqual(list(generator), [Missing('val1'),
                                           Missing('val2')])

        # Nested.
        generator = _walk_diff([Missing('val1'),
                                [Missing('val2')]])
        self.assertEqual(list(generator), [Missing('val1'),
                                           Missing('val2')])

    def test_dict_input(self):
        # Flat dictionary input.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': Missing('val2')})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('val2')]))

        # Nested dictionary input.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': {'key3': Missing('baz')}})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('baz')]))

    def test_unwrapped_input(self):
        generator = _walk_diff(Missing('val1'))
        self.assertEqual(list(generator), [Missing('val1')])

    def test_mixed_input(self):
        # Nested collection of dict, list, and unwrapped items.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': [Missing('val2'),
                                         [Missing('val3'),
                                          Missing('val4')]]})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('val2'),
                                              Missing('val3'),
                                              Missing('val4')]))

    def test_nondiff_items(self):
        # Flat list.
        with self.assertRaises(TypeError):
            generator = _walk_diff(['val1', 'val2'])
            list(generator)

        # Flat dict.
        with self.assertRaises(TypeError):
            generator = _walk_diff({'key1': 'val1', 'key2': 'val2'})
            list(generator)

        # Nested list.
        with self.assertRaises(TypeError):
            generator = _walk_diff([Missing('val1'), ['val2']])
            list(generator)

        # Nested collection of dict, list, and unwrapped items.
        with self.assertRaises(TypeError):
            generator = _walk_diff({'key1': Missing('val1'),
                                    'key2': [Missing('val2'),
                                             [Missing('val3'),
                                              'val4']]})
            list(generator)
