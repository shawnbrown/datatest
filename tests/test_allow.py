# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest import Missing

from datatest.allow import _walk_diff

# NOTE!!!: Currently, the allowance context managers are being tested
# as methods of DataTestCase (in test_case.py).  In the future, after
# refactoring the allowances to also work with py.test, the tests for
# these classes should be moved out of test_case and into this
# sub-module.


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
