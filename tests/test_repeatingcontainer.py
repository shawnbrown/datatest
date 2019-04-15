#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import _unittest as unittest

try:
    import pandas
except ImportError:
    pandas = None

from datatest._compatibility.collections.abc import Iterator
from datatest._utils import IterItems
from datatest._repeatingcontainer import RepeatingContainer


class TestRepeatingContainer(unittest.TestCase):
    def test_init_sequence(self):
        group = RepeatingContainer([1, 2, 3])
        self.assertEqual(group._keys, ())
        self.assertEqual(group._objs, (1, 2, 3))

    def test_init_mapping(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        group = RepeatingContainer(data)
        self.assertEqual(group._keys, tuple(data.keys()))
        self.assertEqual(group._objs, tuple(data.values()))

    def test_init_iteritems(self):
        keys = ('a', 'b', 'c')
        values = (1, 2, 3)
        group = RepeatingContainer(IterItems(zip(keys, values)))
        self.assertEqual(group._keys, keys)
        self.assertEqual(group._objs, values)

    def test_init_exceptions(self):
        with self.assertRaises(TypeError):
            RepeatingContainer(123)

        with self.assertRaises(ValueError):
            RepeatingContainer('abc')

    def test_iter_sequence(self):
        group = RepeatingContainer([1, 2, 3])
        self.assertIsInstance(iter(group), Iterator)
        self.assertNotIsInstance(iter(group), IterItems)
        self.assertEqual(list(group), [1, 2, 3])

    def test_iter_mapping(self):
        group = RepeatingContainer({'a': 1, 'b': 2, 'c': 3})
        self.assertIsInstance(iter(group), IterItems)
        self.assertEqual(set(group), set([('a', 1), ('b', 2), ('c', 3)]))

    def test_repr(self):
        group = RepeatingContainer([1, 2, 3])
        self.assertEqual(repr(group), 'RepeatingContainer([1, 2, 3])')

        group = RepeatingContainer([1, 2])
        group._keys = ['a', 'b']
        self.assertEqual(repr(group), "RepeatingContainer({'a': 1, 'b': 2})")

    def test_repr_long(self):
        # Get longest element repr that should fit on one line.
        single_line_max = 79 - len(RepeatingContainer.__name__) - len("([''])")

        # Exactly up-to single-line limit.
        value = 'a' * single_line_max
        group = RepeatingContainer([value])
        self.assertEqual(len(repr(group)), 79)
        self.assertEqual(
            repr(group),
            "RepeatingContainer(['{0}'])".format(value),
        )

        # Multi-line repr (one char over single-line limit)
        value = 'a' * (single_line_max + 1)
        group = RepeatingContainer([value])
        self.assertEqual(len(repr(group)), 84)
        self.assertEqual(
            repr(group),
            "RepeatingContainer([\n  '{0}'\n])".format(value),
        )

    def test_getattr(self):
        class ExampleClass(object):
            attr = 123

        group = RepeatingContainer([ExampleClass(), ExampleClass()])
        group = group.attr
        self.assertIsInstance(group, RepeatingContainer)
        self.assertEqual(group._objs, (123, 123))

    def test_compatible_container(self):
        # Test RepeatingContainer of list items.
        group = RepeatingContainer([2, 4])
        self.assertTrue(
            group._compatible_container(RepeatingContainer([5, 6])),
            msg='is RepeatingContainer and _objs length matches',
        )
        self.assertFalse(
            group._compatible_container(1),
            msg='non-RepeatingContainer values are never compatible',
        )
        self.assertFalse(
            group._compatible_container(RepeatingContainer([5, 6, 7])),
            msg='not compatible when _objs length does not match',
        )
        self.assertFalse(
            group._compatible_container(RepeatingContainer({'foo': 5, 'bar': 6})),
            msg='not compatible if keys are given but original has no keys',
        )

        # Test RepeatingContainer of dict items.
        group = RepeatingContainer({'foo': 2, 'bar': 4})
        self.assertTrue(
            group._compatible_container(RepeatingContainer({'foo': 5, 'bar': 6})),
            msg='is RepeatingContainer and _keys match',
        )
        self.assertFalse(
            group._compatible_container(RepeatingContainer({'qux': 5, 'quux': 6})),
            msg='not compatible if keys do not match',
        )

    def test_normalize_value(self):
        group = RepeatingContainer([2, 4])

        result = group._normalize_value(5)
        self.assertEqual(
            result,
            (5, 5),
            msg='value is expanded to match number of _objs',
        )

        result = group._normalize_value(RepeatingContainer([5, 6]))
        self.assertEqual(
            result,
            (5, 6),
            msg='compatible RepeatingContainers are unwrapped rather than expanded',
        )

        other = RepeatingContainer([5, 6, 7])
        result = group._normalize_value(other)
        self.assertIsInstance(
            result,
            tuple,
            msg='incompatible RepeatingContainers are expanded like other values',
        )
        self.assertEqual(len(result), 2)
        equals_other = super(other.__class__, other).__eq__
        self.assertTrue(equals_other(result[0]))
        self.assertTrue(equals_other(result[1]))

        group = RepeatingContainer([2, 4])
        group._keys = ['foo', 'bar']
        other = RepeatingContainer([8, 6])
        other._keys = ['bar', 'foo']  # <- keys in different order
        result = group._normalize_value(other)
        self.assertEqual(
            result,
            (6, 8),  # <- reordered to match `group`
            msg='result order should match key names, not _obj position',
        )

    def test_expand_args_kwds(self):
        argsgroup = RepeatingContainer([2, 4])

        kwdsgroup = RepeatingContainer([2, 4])
        kwdsgroup._keys = ['foo', 'bar']

        # Unwrap RepeatingContainer.
        result = argsgroup._expand_args_kwds(RepeatingContainer([5, 6]))
        expected = [
            ((5,), {}),
            ((6,), {}),
        ]
        self.assertEqual(result, expected)

        # Expand int and unwrap RepeatingContainer.
        result = argsgroup._expand_args_kwds(1, RepeatingContainer([5, 6]))
        expected = [
            ((1, 5), {}),
            ((1, 6), {}),
        ]
        self.assertEqual(result, expected)

        # Unwrap two RepeatingContainer.
        result = argsgroup._expand_args_kwds(
            x=RepeatingContainer([5, 6]),
            y=RepeatingContainer([7, 9]),
        )
        expected = [
            ((), {'x': 5, 'y': 7}),
            ((), {'x': 6, 'y': 9}),
        ]
        self.assertEqual(result, expected)

        # Kwdsgroup expansion.
        kwdgrp2 = RepeatingContainer([5, 6])
        kwdgrp2._keys = ['foo', 'bar']

        # Unwrap keyed RepeatingContainer.
        result = kwdsgroup._expand_args_kwds(kwdgrp2)
        expected = [
            ((5,), {}),
            ((6,), {}),
        ]
        self.assertEqual(result, expected)

        # Unwrap keyed RepeatingContainer with keys in different order.
        kwdgrp_reverse = RepeatingContainer([6, 5])
        kwdgrp_reverse._keys = ['bar', 'foo']
        result = kwdsgroup._expand_args_kwds(kwdgrp_reverse)
        expected = [
            ((5,), {}),
            ((6,), {}),
        ]
        self.assertEqual(result, expected)

        # Expand int and unwrap keyed RepeatingContainer.
        result = kwdsgroup._expand_args_kwds(1, kwdgrp2)
        expected = [
            ((1, 5), {}),
            ((1, 6), {}),
        ]
        self.assertEqual(result, expected)

        # Sanity-check/quick integration test (all combinations).
        result = kwdsgroup._expand_args_kwds('a', RepeatingContainer({'foo': 'b', 'bar': 'c'}),
                                             x=1, y=RepeatingContainer({'bar': 4, 'foo': 2}))
        expected = [
            (('a', 'b'), {'x': 1, 'y': 2}),
            (('a', 'c'), {'x': 1, 'y': 4}),
        ]
        self.assertEqual(result, expected)

    def test__getattr__(self):
        number = complex(2, 3)
        group = RepeatingContainer([number, number])
        group = group.imag  # <- Gets `imag` attribute.
        self.assertEqual(group._objs, (3, 3))

    def test__call__(self):
        group = RepeatingContainer(['foo', 'bar'])
        result = group.upper()
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(result._objs, ('FOO', 'BAR'))

    def test_added_special_names(self):
        """Test some of the methods that are programmatically added to
        RepeatingContainer by the _setup_RepeatingContainer_special_names() function.
        """
        group = RepeatingContainer(['abc', 'def'])

        result = group + 'xxx'  # <- __add__()
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(result._objs, ('abcxxx', 'defxxx'))

        result = group[:2]  # <- __getitem__()
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(result._objs, ('ab', 'de'))

    def test_added_reflected_special_names(self):
        result = 100 + RepeatingContainer([1, 2])  # <- __radd__()
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(result._objs, (101, 102))

        # When the reflected method is missing, the unreflected method of
        # the *other* value is re-called on the RepeatingContainer's contents.
        # The following test case does this with strings. Since 'str' does not
        # have an __radd__() method, this calls the unreflected __add__()
        # of the original string.
        result = 'xxx' + RepeatingContainer(['abc', 'def'])  # <- unreflected __add__()
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(result._objs, ('xxxabc', 'xxxdef'))

    def test_repeatingcontainer_argument_handling(self):
        # Unwrapping RepeatingContainer args with __add__().
        group_of_ints1 = RepeatingContainer([50, 60])
        group_of_ints2 = RepeatingContainer([5, 10])
        group = group_of_ints1 + group_of_ints2
        self.assertEqual(group._objs, (55, 70))

        # Unwrapping RepeatingContainer args with __getitem__().
        group_of_indexes = RepeatingContainer([0, 1])
        group_of_strings = RepeatingContainer(['abc', 'abc'])
        group = group_of_strings[group_of_indexes]
        self.assertEqual(group._objs, ('a', 'b'))


class TestRepeatingContainerBaseMethods(unittest.TestCase):
    def setUp(self):
        self.group1 = RepeatingContainer(['foo', 'bar'])
        self.group2 = RepeatingContainer(['foo', 'baz'])

    def test__eq__(self):
        # Comparing contents of RepeatingContainer (default behavior).
        result = (self.group1 == self.group2)  # <- Call to __eq__().
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(tuple(result), (True, False))

        # Comparing RepeatingContainer objects themselves.
        result = super(RepeatingContainer, self.group1).__eq__(self.group1)
        self.assertIs(result, True)

        result = super(RepeatingContainer, self.group1).__eq__(self.group2)
        self.assertIs(result, False)

    def test__ne__(self):
        # Comparing contents of RepeatingContainer (default behavior).
        result = (self.group1 != self.group2)  # <- Call to __ne__().
        self.assertIsInstance(result, RepeatingContainer)
        self.assertEqual(tuple(result), (False, True))

        # Comparing RepeatingContainer objects themselves.
        result = super(RepeatingContainer, self.group1).__ne__(self.group2)
        self.assertIs(result, True)

        result = super(RepeatingContainer, self.group1).__ne__(self.group1)
        self.assertIs(result, False)


class TestNestedExample(unittest.TestCase):
    """Quick integration test using nested RepeatingContainers."""

    def setUp(self):
        self.group = RepeatingContainer([
            RepeatingContainer({'foo': 'abc', 'bar': 'def'}),
            'ghi',
        ])

    def test_method(self):
        result1, result2 = self.group.upper()
        self.assertEqual(dict(result1), {'foo': 'ABC', 'bar': 'DEF'})
        self.assertEqual(result2, 'GHI')

    def test_magic_method(self):
        result1, result2 = self.group + 'XYZ'
        self.assertEqual(dict(result1), {'foo': 'abcXYZ', 'bar': 'defXYZ'})
        self.assertEqual(result2, 'ghiXYZ')

    def test_unreflected_magic_method(self):
        result1, result2 = 'XYZ' + self.group
        self.assertEqual(dict(result1), {'foo': 'XYZabc', 'bar': 'XYZdef'})
        self.assertEqual(result2, 'XYZghi')

    def test_deeply_nested(self):
        group = RepeatingContainer([
            RepeatingContainer([
                RepeatingContainer(['abc', 'def']),
                RepeatingContainer(['abc', 'def']),
            ]),
            RepeatingContainer([
                RepeatingContainer(['abc', 'def']),
                RepeatingContainer(['abc', 'def'])
            ])
        ])

        result = group + ('xxx' + group.upper())  # <- Operate on RepeatingContainer.

        # Unpack various nested values.
        subresult1, subresult2 = result
        subresult1a, subresult1b = subresult1
        subresult2a, subresult2b = subresult2

        self.assertEqual(subresult1a._objs, ('abcxxxABC', 'defxxxDEF'))
        self.assertEqual(subresult1b._objs, ('abcxxxABC', 'defxxxDEF'))
        self.assertEqual(subresult2a._objs, ('abcxxxABC', 'defxxxDEF'))
        self.assertEqual(subresult2b._objs, ('abcxxxABC', 'defxxxDEF'))


@unittest.skipIf(not pandas, 'pandas not found')
class TestPandasExample(unittest.TestCase):
    """Quick integration test using a RepeatingContainer of DataFrames."""

    def setUp(self):
        data = pandas.DataFrame({
            'A': ('x', 'x', 'y', 'y', 'z', 'z'),
            'B': ('foo', 'foo', 'foo', 'bar', 'bar', 'bar'),
            'C': (20, 30, 10, 20, 10, 10),
        })
        self.group = RepeatingContainer([data, data])

    def test_summed_values(self):
        result = self.group['C'].sum()
        self.assertEqual(tuple(result), (100, 100))

    def test_selected_grouped_summed_values(self):
        result = self.group[['A', 'C']].groupby('A').sum()

        expected = pandas.DataFrame(
            data={'C': (50, 30, 20)},
            index=pandas.Index(['x', 'y', 'z'], name='A'),
        )

        df1, df2 = result  # Unpack results.
        pandas.testing.assert_frame_equal(df1, expected)
        pandas.testing.assert_frame_equal(df2, expected)

    def test_selected_filtered_grouped_summed_values(self):
        result = self.group[['A', 'C']][self.group['B'] == 'foo'].groupby('A').sum()

        expected = pandas.DataFrame(
            data={'C': (50, 10)},
            index=pandas.Index(['x', 'y'], name='A'),
        )

        df1, df2 = result  # Unpack results.
        pandas.testing.assert_frame_equal(df1, expected)
        pandas.testing.assert_frame_equal(df2, expected)


if __name__ == '__main__':
    unittest.main()
