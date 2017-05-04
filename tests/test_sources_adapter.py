# -*- coding: utf-8 -*-
from . import _unittest as unittest

# Import related objects.
from datatest.compare import CompareSet
from datatest.compare import CompareDict

from .mixins import CountTests
from .mixins import OtherTests

from .common import MinimalSource
from datatest.sources.adapter import _FilterValueError
from datatest.sources.adapter import AdapterSource


class TestAdapterSourceBasics(OtherTests, unittest.TestCase):
    def setUp(self):
        fieldnames = ['col1', 'col2', 'col3']
        source = MinimalSource(self.testdata, fieldnames)
        interface = [
            ('col1', 'label1'),
            ('col2', 'label2'),
            ('col3', 'value'),
        ]
        self.datasource = AdapterSource(source, interface)


class TestAdapterSource(unittest.TestCase):
    def setUp(self):
        self.fieldnames = ['col1', 'col2', 'col3']
        self.data = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]
        self.source = MinimalSource(self.data, self.fieldnames)

    def test_repr(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c')]
        adapted = AdapterSource(self.source, interface)
        required = ("AdapterSource(MinimalSource(<data>, <fieldnames>), "
                    "[('col1', 'a'), ('col2', 'b'), ('col3', 'c')])")
        self.assertEqual(required, repr(adapted))

    def test_unwrap_columns(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c'), (None, 'd')]
        adapted = AdapterSource(self.source, interface)
        unwrap_columns = adapted._unwrap_columns

        self.assertEqual('col1', unwrap_columns('a'))
        self.assertEqual(('col1', 'col2'), unwrap_columns(['a', 'b']))
        self.assertEqual(None, unwrap_columns('d'))
        with self.assertRaises(KeyError):
            unwrap_columns('col1')  # <- This is a hidden, adaptee column
                                    #    not a visible adapter column.

    def test_rewrap_columns(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c'), (None, 'd')]
        adapted = AdapterSource(self.source, interface)
        rewrap_columns = adapted._rewrap_columns

        self.assertEqual('a', rewrap_columns('col1'))
        self.assertEqual(('a', 'b'), rewrap_columns(['col1', 'col2']))
        self.assertEqual(None, rewrap_columns([]))
        self.assertEqual(None, rewrap_columns(None))
        with self.assertRaises(KeyError):
            rewrap_columns('c')

    def test_unwrap_filter(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c'), (None, 'd')]
        adapted = AdapterSource(self.source, interface)
        unwrap_filter = adapted._unwrap_filter

        self.assertEqual({'col1': 'foo'}, unwrap_filter({'a': 'foo'}))
        self.assertEqual({'col1': 'foo', 'col2': 'bar'}, unwrap_filter({'a': 'foo', 'b': 'bar'}))
        self.assertEqual({}, unwrap_filter({}))
        with self.assertRaises(_FilterValueError):
            unwrap_filter({'a': 'foo', 'd': 'baz'})  # <- d='baz' cannot be converted
                                                     #    because there is no adaptee
                                                     #    column mapped to 'd'.

        # It is possible, however, to filter 'd' to an empty string (the
        # default *missing* value.)
        self.assertEqual({'col1': 'foo'}, unwrap_filter({'a': 'foo', 'd': ''}))

    def test_rebuild_compareset(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c'), (None, 'd')]
        adapted = AdapterSource(self.source, interface)
        rebuild_compareset = adapted._rebuild_compareset

        # Rebuild one column result as two column result.
        orig = CompareSet(['x', 'y', 'z'])
        result = rebuild_compareset(orig, 'b', ['b', 'd'])
        expected = CompareSet([('x', ''), ('y', ''), ('z', '')])
        self.assertEqual(expected, result)

        # Rebuild two column result to three column with missing column in the middle.
        orig = CompareSet([('x1', 'x2'), ('y1', 'y2'), ('z1', 'z2')])
        result = rebuild_compareset(orig, ['b', 'c'], ['b', 'd', 'c'])
        expected = CompareSet([('x1', '', 'x2'), ('y1', '', 'y2'), ('z1', '', 'z2')])
        self.assertEqual(expected, result)

    def test_rebuild_comparedict(self):
        interface = [('col1', 'a'), ('col2', 'b'), ('col3', 'c'), (None, 'd')]
        adapted = AdapterSource(self.source, interface)
        rebuild_comparedict = adapted._rebuild_comparedict

        # Rebuild single key result as two key result.
        orig = CompareDict({'x': 1, 'y': 2, 'z': 3}, key_names='a')
        result = rebuild_comparedict(orig, 'c', 'c', 'a', ['a', 'b'], missing_col='')
        expected = CompareDict({('x', ''): 1,
                                ('y', ''): 2,
                                ('z', ''): 3},
                               key_names=['a', 'b'])
        self.assertEqual(expected, result)

        # Rebuild two key result as three key result.
        orig = CompareDict({('x', 'x'): 1, ('y', 'y'): 2, ('z', 'z'): 3}, key_names=['a', 'c'])
        result = rebuild_comparedict(orig, 'c', 'c', ['a', 'b'], ['a', 'd', 'b'], missing_col='')
        expected = CompareDict({('x', '', 'x'): 1,
                                ('y', '', 'y'): 2,
                                ('z', '', 'z'): 3},
                               key_names=['a', 'd', 'b'])
        self.assertEqual(expected, result)

        # Rebuild single value tuple result as two value result.
        orig = CompareDict({'x': (1,), 'y': (2,), 'z': (3,)}, key_names='a')
        result = rebuild_comparedict(orig, 'c', ['c', 'd'], 'a', 'a', missing_col='')
        expected = CompareDict({'x': (1, ''),
                                'y': (2, ''),
                                'z': (3, '')},
                               key_names='a')
        self.assertEqual(expected, result)

        # Rebuild single value result as two value result.
        if True:
            orig = CompareDict({'x': 1, 'y': 2, 'z': 3}, key_names='a')
            result = rebuild_comparedict(orig, 'c', ['c', 'd'], 'a', 'a', missing_col='')
            expected = CompareDict({'x': (1, ''),
                                    'y': (2, ''),
                                    'z': (3, '')},
                                   key_names=['c', 'd'])
            self.assertEqual(expected, result)

        # Rebuild two column result as three column result.
        orig = CompareDict({'x': (1, 2), 'y': (2, 4), 'z': (3, 6)}, key_names='a')
        result = rebuild_comparedict(orig, ['b', 'c'], ['b', 'd', 'c'],
                                       'a', 'a', missing_col='empty')
        expected = CompareDict({'x': (1, 'empty', 2),
                                'y': (2, 'empty', 4),
                                'z': (3, 'empty', 6)},
                               key_names='a')
        self.assertEqual(expected, result)

        # Rebuild two key and two column result as three key and three column result.
        orig = CompareDict({('x', 'x'): (1, 2),
                            ('y', 'y'): (2, 4),
                            ('z', 'z'): (3, 6)},
                            key_names=['a', 'c'])
        result = rebuild_comparedict(orig,
                                       ['b', 'c'], ['b', 'd', 'c'],
                                       ['a', 'b'], ['a', 'd', 'b'],
                                       missing_col='empty')
        expected = CompareDict({('x', '', 'x'): (1, 'empty', 2),
                                  ('y', '', 'y'): (2, 'empty', 4),
                                  ('z', '', 'z'): (3, 'empty', 6)},
                                 key_names=['a', 'd', 'b'])
        self.assertEqual(expected, result)

    def test_columns(self):
        # Test original.
        self.assertEqual(['col1', 'col2', 'col3'], self.source.columns())

        # Reorder columns.
        interface = [
            ('col3', 'col3'),
            ('col2', 'col2'),
            ('col1', 'col1'),
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['col3', 'col2', 'col1'], adapted.columns())

        # Rename columns.
        interface = [
            ('col1', 'a'),
            ('col2', 'b'),
            ('col3', 'c'),
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['a', 'b', 'c'], adapted.columns())

        # Remove column.
        interface = [
            ('col1', 'col1'),
            ('col2', 'col2'),
            # Column 'col3' omitted!
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['col1', 'col2'], adapted.columns())

        # Remove column 2.
        interface = [
            ('col1', 'col1'),
            ('col2', 'col2'),
            ('col3', None),  # Column 'col3' mapped to None!
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['col1', 'col2'], adapted.columns())

        # Add new column.
        interface = [
            ('col1', 'a'),
            ('col2', 'b'),
            ('col3', 'c'),
            (None, 'd'),  # <- New column, no corresponding original!
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['a', 'b', 'c', 'd'], adapted.columns())

        # Raise error if old name is not in original source.
        interface = [
            ('bad_column', 'a'),  # <- 'bad_column' not in original!
            ('col2', 'b'),
            ('col3', 'c'),
        ]
        with self.assertRaises(KeyError):
            adapted = AdapterSource(self.source, interface)

    def test_iter(self):
        interface = [('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        expected = [
            {'two': 'x', 'three': '17', 'four': ''},
            {'two': 'x', 'three': '13', 'four': ''},
            {'two': 'y', 'three': '20', 'four': ''},
            {'two': 'z', 'three': '15', 'four': ''},
        ]
        result = list(adapted.__iter__())
        self.assertEqual(expected, result)

    def test_distinct(self):
        # Basic usage.
        interface = [('col1', 'one'), ('col2', 'two'), ('col3', 'three')]
        adapted = AdapterSource(self.source, interface)
        required = set(['x', 'y', 'z'])
        self.assertEqual(required, adapted.distinct('two'))

        # Adapter column mapped to None.
        interface = [('col2', 'two'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)

        required = set([('x', ''), ('y', ''), ('z', '')])
        self.assertEqual(required, adapted.distinct(['two', 'four']))

        required = set([('', 'x'), ('', 'y'), ('', 'z')])
        self.assertEqual(required, adapted.distinct(['four', 'two']))

        required = set([''])
        self.assertEqual(required, adapted.distinct('four'))

        required = set([('', '')])
        self.assertEqual(required, adapted.distinct(['four', 'four']))

        # Filter on renamed column.
        interface = [('col1', 'one'), ('col2', 'two'), ('col3', 'three')]
        adapted = AdapterSource(self.source, interface)
        required = set(['17', '13'])
        self.assertEqual(required, adapted.distinct('three', two='x'))

        # Filter on column mapped to None.
        interface = [('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)

        required = set()
        self.assertEqual(required, adapted.distinct('three', four='x'))

        required = set(['17', '13', '20', '15'])
        self.assertEqual(required, adapted.distinct('three', four=''))

        # Unknown column.
        interface = [('col1', 'one'), ('col2', 'two')]
        adapted = AdapterSource(self.source, interface)
        required = set(['x', 'y', 'z'])
        with self.assertRaises(KeyError):
            adapted.distinct('three')

    def test_sum(self):
        # Basic usage (no group-by keys).
        interface = [('col1', 'one'), ('col2', 'two'), ('col3', 'three')]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(65, adapted.sum('three'))

        # No group-by keys, filter to missing column.
        interface = [('col1', 'one'), ('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(0, adapted.sum('three', four='xyz'))

        # Grouped by column 'two'.
        result = adapted.sum('three', 'two')
        self.assertEqual({'x': 30, 'y': 20, 'z': 15}, result)
        self.assertEqual(['two'], list(result.key_names))

        # Grouped by column mapped to None.
        interface = [('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('three', ['two', 'four'])
        expected = {('x', ''): 30, ('y', ''): 20, ('z', ''): 15}
        self.assertEqual(expected, result)

        # Sum over column mapped to None.
        interface = [('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('four', 'two')
        expected = {'x': 0, 'y': 0, 'z': 0}
        self.assertEqual(expected, result)

        # Grouped by and summed over column mapped to None.
        interface = [('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        with self.assertRaises(ValueError):
            adapted.sum(['three', 'four'], 'two')

        # Grouped by and summed over column mapped to None using alternate missing.
        interface = [('col1', 'one'), ('col2', 'two'), ('col3', 'three'), (None, 'four'), (None, 'five')]
        adapted = AdapterSource(self.source, interface, missing='EMPTY')
        result = adapted.sum('four', 'one')  # <- Key on existing column.
        expected = {'a': 0}
        self.assertEqual(expected, result)
        result = adapted.sum('four', 'five')  # <- Key on missing column.
        expected = {'EMPTY': 0}
        self.assertEqual(expected, result)

        # Summed over column mapped to None and nothing else.
        interface = [('col2', 'two'), ('col3', 'three'), (None, 'four')]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('four', 'two')
        expected = {'x': 0, 'y': 0, 'z': 0}
        self.assertEqual(expected, result)
