# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datetime import timedelta
from . import _unittest as unittest
from datatest import _utils
from datatest._utils import IterItems
from datatest._utils import pretty_timedelta_repr


class TestIterItems(unittest.TestCase):
    def test_type_error(self):
        regex = "expected iterable or mapping, got 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            IterItems(123)

    def test_non_exhaustible(self):
        items_list = [('a', 1), ('b', 2)]  # <- Non-exhaustible input.

        items = IterItems(items_list)
        self.assertIs(iter(items), iter(items), msg='exhaustible output')
        self.assertEqual(list(items), items_list)
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_exhaustible(self):
        items_iter = iter([('a', 1), ('b', 2)])  # <- Exhaustible iterator.

        items = IterItems(items_iter)
        self.assertIs(iter(items), iter(items))
        self.assertEqual(list(items), [('a', 1), ('b', 2)])
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_dict(self):
        mapping = {'a': 1, 'b': 2}

        items = IterItems(mapping)
        self.assertEqual(set(items), set([('a', 1), ('b', 2)]))
        self.assertEqual(set(items), set(), msg='already exhausted')

    def test_dictitems(self):
        dic = {'a': 1}

        if hasattr(dic, 'iteritems'):  # <- Python 2
            dic_items = dic.iteritems()

            items = IterItems(dic_items)
            self.assertEqual(list(items), [('a', 1)])
            self.assertEqual(list(items), [], msg='already exhausted')

        dic_items = dic.items()

        items = IterItems(dic_items)
        self.assertEqual(list(items), [('a', 1)])
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_empty_iterable(self):
        empty = iter([])

        items = IterItems(empty)
        self.assertEqual(list(items), [])

    def test_repr(self):
        items = IterItems([1, 2])

        repr_part = repr(iter([])).partition(' ')[0]
        repr_start = 'IterItems({0}'.format(repr_part)
        self.assertTrue(repr(items).startswith(repr_start))

        generator = (x for x in [1, 2])
        items = IterItems(generator)
        self.assertEqual(repr(items), 'IterItems({0!r})'.format(generator))

    def test_subclasshook(self):
        items = IterItems(iter([]))
        self.assertIsInstance(items, IterItems)

        try:
            items = dict([]).iteritems()  # <- For Python 2
        except AttributeError:
            items = dict([]).items()  # <- For Python 3
        self.assertIsInstance(items, IterItems)

        items = enumerate([])
        self.assertIsInstance(items, IterItems)

    def test_virtual_subclass(self):
        class OtherClass(object):
            pass

        oth_cls = OtherClass()

        IterItems.register(OtherClass)  # <- Register virtual subclass.
        self.assertIsInstance(oth_cls, IterItems)


class TestMakeSentinel(unittest.TestCase):
    def test_basic(self):
        sentinel = _utils._make_sentinel(
            'TheName', '<the repr>', 'The docstring.'
        )
        self.assertEqual(sentinel.__class__.__name__, 'TheName')
        self.assertEqual(repr(sentinel), '<the repr>')
        self.assertEqual(sentinel.__doc__, 'The docstring.')
        self.assertTrue(bool(sentinel))

    def test_falsy(self):
        sentinel = _utils._make_sentinel(
            'TheName', '<the repr>', 'The docstring.', truthy=False
        )
        self.assertFalse(bool(sentinel))


class TestPrettyTimedeltaRepr(unittest.TestCase):
    def test_already_normalized_units(self):
        """When the units align to timedelta's internal normalization,
        the pretty repr should make no additional changes (other than
        omitting the module prefix.
        """
        delta = timedelta(days=6, seconds=27, microseconds=100)

        actual = pretty_timedelta_repr(delta)
        expected = 'timedelta(days=6, seconds=27, microseconds=100)'
        self.assertEqual(actual, expected)

    def test_default_behavior(self):
        """When there are no *extras*, positive deltas should have
        the same repr as timedelta's native repr.
        """
        delta = timedelta(days=11, seconds=49600)

        actual = pretty_timedelta_repr(delta, extras=None)  # <- No extras!
        expected = 'timedelta(days=11, seconds=49600)'
        self.assertEqual(actual, expected)

    def test_extras_weeks(self):
        """Test breaking out units into 'weeks'."""
        delta = timedelta(days=11, seconds=49600)

        actual = pretty_timedelta_repr(delta, extras='weeks')
        expected = 'timedelta(weeks=1, days=4, seconds=49600)'
        self.assertEqual(actual, expected)

    def test_extras_hours_minutes(self):
        """The *extras* argument defauls to 'hours,minutes'."""
        delta = timedelta(days=11, seconds=49600)

        actual = pretty_timedelta_repr(delta, extras='hours,minutes')
        expected = 'timedelta(days=11, hours=13, minutes=46, seconds=40)'
        self.assertEqual(actual, expected)

    def test_negative_delta_default_behavior(self):
        delta = timedelta(days=-9, seconds=-49600)

        actual = pretty_timedelta_repr(delta)
        expected = 'timedelta(days=-9, seconds=-49600)'
        self.assertEqual(actual, expected)

    def test_negative_delta_extras_hours_minutes(self):
        """The builtin repr for timedelta is awful for readability,
        the pretty repr is more natural to read.
        """
        delta = timedelta(microseconds=-1)

        actual = pretty_timedelta_repr(delta, extras='hours,minutes')
        expected = 'timedelta(microseconds=-1)'
        self.assertEqual(actual, expected)

        delta = timedelta(days=-9, seconds=-49600)

        actual = pretty_timedelta_repr(delta, extras='hours,minutes')
        expected = 'timedelta(days=-9, hours=-13, minutes=-46, seconds=-40)'
        self.assertEqual(actual, expected)

    def test_negative_delta_custom_extras(self):
        """Test breaking out units into 'weeks'."""
        delta = timedelta(days=-9, seconds=-49600)

        actual = pretty_timedelta_repr(delta, extras='weeks')
        expected = 'timedelta(weeks=-1, days=-2, seconds=-49600)'
        self.assertEqual(actual, expected)
