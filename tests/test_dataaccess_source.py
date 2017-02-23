# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest.utils import collections
from datatest.dataaccess.source import DataSource
from datatest.dataaccess.source import DataQuery
from datatest.dataaccess.source import DataQuery2
from datatest.dataaccess.source import RESULT_TOKEN
from datatest.dataaccess.source import TypedIterator
from datatest.dataaccess.source import _map_data
from datatest.dataaccess.source import ABCItemsIter
from datatest.dataaccess.source import ItemsIter
from datatest.dataaccess.query import BaseQuery
from datatest.dataaccess.result import DataResult


class TestTypedIterator(unittest.TestCase):
    def test_init(self):
        untyped = iter([1, 2, 3, 4])

        typed = TypedIterator(untyped, list)
        self.assertEqual(typed.intended_type, list)

        typed = TypedIterator(iterable=untyped, intended_type=list)
        self.assertEqual(typed.intended_type, list)

        regex = 'intended_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = TypedIterator(untyped, [1, 2])


class TestItemsIter(unittest.TestCase):
    def test_issubclass(self):
        self.assertTrue(issubclass(ABCItemsIter, ABCItemsIter))  # Sanity check.

        self.assertTrue(issubclass(collections.ItemsView, ABCItemsIter))
        self.assertTrue(issubclass(ItemsIter, ABCItemsIter))

    def test_thestuff(self):
        foo = ItemsIter([1,2,3])
        self.assertEqual(list(foo), [1,2,3])


class Test_map_data(unittest.TestCase):
    def test_foo(self):
        function = lambda x: x * 2
        #iterable = TypedIterator([1, 2, 3], list)
        iterable = [1, 2, 3]

        result = _map_data(function, iterable)
        expected = [2, 4, 6]
        self.assertEqual(list(result), expected)

        #query1 = DataQuery2('col2')
        #query2 = query1.map(int)
        #self.assertIsNot(query1, query2, 'should return new object')

        #source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        #result = query2.execute(source)
        #self.assertEqual(result, [2, 2])



class TestDataQuery2(unittest.TestCase):
    def test_init(self):
        query = DataQuery2('foo', bar='baz')
        expected = tuple([
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, ('foo',), {'bar': 'baz'}),
        ])
        self.assertEqual(query._query_steps, expected)
        self.assertEqual(query._initializer, None)

        with self.assertRaises(TypeError, msg='should require select args'):
            DataQuery2()

    def test_from_parts(self):
        source = DataSource([(1, 2), (1, 2)], columns=['A', 'B'])
        query = DataQuery2._from_parts(initializer=source)
        self.assertEqual(query._query_steps, tuple())
        self.assertIs(query._initializer, source)

        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            wrong_type = ['hello', 'world']
            query = DataQuery2._from_parts(initializer=wrong_type)

    def test_execute(self):
        source = DataSource([('1', '2'), ('1', '2')], columns=['A', 'B'])
        query = DataQuery2._from_parts(initializer=source)
        query._query_steps = [
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, ('B',), {}),
            (map, (int, RESULT_TOKEN), {}),
            (map, (lambda x: x * 2, RESULT_TOKEN), {}),
            (sum, (RESULT_TOKEN,), {}),
        ]
        result = query.execute()
        self.assertEqual(result, 8)

    def test_map(self):
        query1 = DataQuery2('col2')
        query2 = query1.map(int)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, [2, 2])

    def test_filter(self):
        query1 = DataQuery2('col1')
        query2 = query1.filter(lambda x: x == 'a')
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, ['a'])

    def test_reduce(self):
        query1 = DataQuery2('col1')
        query2 = query1.reduce(lambda x, y: x + y)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, 'ab')


class TestDataQuery(unittest.TestCase):
    def test_from_parts(self):
        source = DataSource([(1, 2), (1, 2)], columns=['A', 'B'])
        query = DataQuery._from_parts(initializer=source)
        self.assertIsInstance(query, BaseQuery)  # <- Subclass of BaseQuery.

        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            wrong_type = ['hello', 'world']
            query = DataQuery._from_parts(initializer=wrong_type)

    def test_eval(self):
        query = DataQuery()
        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            query.eval(['hello', 'world'])  # <- Expects None or DataQuery, not list!


class TestDataSourceBasics(unittest.TestCase):
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_columns(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.source.columns(), expected)

    def test_iter(self):
        """Test __iter__."""
        result = [row for row in self.source]
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, result)

    def test_select2_column_no_container(self):
        result = self.source._select2('label1')
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(list(result), expected)

        #result = self.source._select2(['label1'])
        #expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        #self.assertEqual(list(result), expected)

        #result = self.source._select2({'label1'})
        #expected = {'a', 'b'}
        #self.assertEqual(list(result), expected)


    def test_select2_column_as_list(self):
        result = self.source._select2(['label1'])
        expected = [['a'], ['a'], ['a'], ['a'], ['b'], ['b'], ['b']]
        self.assertEqual(list(result), expected)

        result = self.source._select2(['label1', 'label2'])
        expected = [['a', 'x'], ['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        self.assertEqual(list(result), expected)

    def test_select2_column_as_tuple(self):
        result = self.source._select2(('label1',))
        expected = [('a',), ('a',), ('a',), ('a',), ('b',), ('b',), ('b',)]
        self.assertEqual(list(result), expected)

    def test_select2_column_as_set(self):
        result = self.source._select2(set(['label1']))
        expected = [set(['a']), set(['a']), set(['a']), set(['a']),
                    set(['b']), set(['b']), set(['b'])]
        self.assertEqual(list(result), expected)

    def test_select2_dict(self):
        result = self.source._select2({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_dict_with_values_container(self):
        result = self.source._select2({('label1', 'label2'): ['value']})
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_dict_frozenset_key(self):
        result = self.source._select2({frozenset(['label1']): 'label2'})
        expected = {
            frozenset(['a']): ['x', 'x', 'y', 'z'],
            frozenset(['b']): ['z', 'y', 'x'],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_dict_with_values_container2(self):
        result = self.source._select2({'label1': ['label2', 'label2']})
        expected = {
            'a': [['x', 'x'], ['x', 'x'], ['y', 'y'], ['z', 'z']],
            'b': [['z', 'z'], ['y', 'y'], ['x', 'x']]
        }
        self.assertEqual(dict(result), expected)

        result = self.source._select2({'label1': set(['label2', 'label2'])})
        expected = {
            'a': [set(['x']), set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_distinct_column_no_container(self):
        result = self.source._select2_distinct('label1')
        expected = ['a', 'b']
        self.assertEqual(list(result), expected)

    def test_select2_distinct_column_as_list(self):
        result = self.source._select2_distinct(['label1'])
        expected = [['a'], ['b']]
        self.assertEqual(list(result), expected)

        result = self.source._select2_distinct(['label1', 'label2'])
        expected = [['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        self.assertEqual(list(result), expected)

    def test_select2_distinct_column_as_tuple(self):
        result = self.source._select2_distinct(('label1',))
        expected = [('a',), ('b',)]
        self.assertEqual(list(result), expected)

    def test_select2_distinct_column_as_set(self):
        result = self.source._select2_distinct(set(['label1']))
        expected = [set(['a']), set(['b'])]
        self.assertEqual(list(result), expected)

    def test_select2_distinct_dict(self):
        result = self.source._select2_distinct({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_distinct_dict_with_values_container(self):
        result = self.source._select2_distinct({('label1', 'label2'): ['value']})
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_distinct_dict_frozenset_key(self):
        result = self.source._select2_distinct({frozenset(['label1']): 'label2'})
        expected = {
            frozenset(['a']): ['x', 'y', 'z'],
            frozenset(['b']): ['z', 'y', 'x'],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_distinct_dict_with_values_container2(self):
        result = self.source._select2_distinct({'label1': ['label2', 'label2']})
        expected = {
            'a': [['x', 'x'], ['y', 'y'], ['z', 'z']],
            'b': [['z', 'z'], ['y', 'y'], ['x', 'x']]
        }
        self.assertEqual(dict(result), expected)

        result = self.source._select2_distinct({'label1': set(['label2', 'label2'])})
        expected = {
            'a': [set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        self.assertEqual(dict(result), expected)

    def test_select2_aggregate(self):
        # Not grouped, single result.
        result = self.source._select2_aggregate('SUM', 'value')
        self.assertEqual(result, 135)

        # Not grouped, multiple results.
        result = self.source._select2_aggregate('SUM', ['value', 'value'])
        self.assertEqual(result, [135, 135])

        # Simple group by (grouped by keys).
        result = self.source._select2_aggregate('SUM', {'label1': 'value'})
        expected = {
            'a': 65,
            'b': 70,
        }
        self.assertEqual(dict(result), expected)

        # Composite value.
        result = self.source._select2_aggregate('SUM', {'label1': ['value', 'value']})
        expected = {
            'a': [65, 65],
            'b': [70, 70],
        }
        self.assertEqual(dict(result), expected)

        # Composite key and composite value.
        result = self.source._select2_aggregate('SUM', {('label1', 'label1'): ['value', 'value']})
        expected = {
            ('a', 'a'): [65, 65],
            ('b', 'b'): [70, 70],
        }
        self.assertEqual(dict(result), expected)

    def test_select_single_value(self):
        result = self.source._select('label1')
        self.assertIsInstance(result, DataResult)
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(list(result), expected)

        arg_dict = {'label1': 'value'}
        result = self.source._select(arg_dict)
        self.assertEqual(arg_dict, {'label1': 'value'}, 'should not alter arg_dict')

    def test_select_tuple_of_values(self):
        result = self.source._select('label1', 'label2')  # <- Using varargs.
        expected = [
            ('a', 'x'),
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),
            ('b', 'y'),
            ('b', 'x'),
        ]
        self.assertEqual(list(result), expected)

    def test_select_values_with_container(self):
        result = self.source._select(['label1', 'label2'])  # <- Using container.
        expected = [
            ('a', 'x'),
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),
            ('b', 'y'),
            ('b', 'x'),
        ]
        self.assertEqual(list(result), expected)

        result = self.source._select(['label1'])  # <- Single-item container.
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(list(result), expected)

        msg = ('should fail if the method call mixes '
               'container and variable arguments')
        with self.assertRaises(ValueError, msg=msg):
            self.source._select(['label1'], 'label2')

    def test_select_dict_of_values(self):
        result = self.source._select({'label1': 'value'})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_value_tuples(self):
        result = self.source._select({'label1': ('label2', 'value')})
        expected = {
            'a': [
                ('x', '17'),
                ('x', '13'),
                ('y', '20'),
                ('z', '15'),
            ],
            'b': [
                ('z', '5'),
                ('y', '40'),
                ('x', '25'),
            ],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_key_tuples(self):
        result = self.source._select({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_key_and_value_tuples(self):
        result = self.source._select({('label1', 'label2'): ('label2', 'value')})
        expected = {
            ('a', 'x'): [('x', '17'), ('x', '13')],
            ('a', 'y'): [('y', '20')],
            ('a', 'z'): [('z', '15')],
            ('b', 'z'): [('z', '5')],
            ('b', 'y'): [('y', '40')],
            ('b', 'x'): [('x', '25')],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_nested_dicts(self):
        """Support for nested dictionaries was removed (for now).
        It's likely that arbitrary nesting would complicate the ability
        to check complex data types that are, themselves, mappings.
        """
        regex = "{'label2': 'value'} not in DataSource"
        with self.assertRaisesRegex(LookupError, regex):
            self.source._select({'label1': {'label2': 'value'}})

    def test_call(self):
        result = self.source('label1')
        self.assertIsInstance(result, DataQuery)

        result = list(result.eval())
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(result, expected)

        result = self.source({'label1': 'label2'})
        self.assertIsInstance(result, DataQuery)

        result = dict(result.eval())
        expected = {
            'a': ['x', 'x', 'y', 'z'],
            'b': ['z', 'y', 'x'],
        }
        self.assertEqual(result, expected)


class TestDataSourceOptimizations(unittest.TestCase):
    """."""
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_select_aggregate(self):
        result = self.source._select_aggregate('SUM', 'value')
        self.assertEqual(result, 135)

        result = self.source._select_aggregate('SUM', 'value', label1='a')
        self.assertEqual(result, 65)

        result = self.source._select_aggregate('SUM', 'value', label1='z')
        self.assertEqual(result, None)

        with self.assertRaises(ValueError):
            self.source._select_aggregate('SUM', 'value', 'value')

    def test_select_aggregate_grouped(self):
        result = self.source._select_aggregate('SUM', {'label1': 'value'})
        self.assertEqual(result.eval(), {'a': 65, 'b': 70})

        result = self.source._select_aggregate('MAX', {'label1': 'value'})
        self.assertEqual(result.eval(), {'a': '20', 'b': '5'})

        result = self.source._select_aggregate('SUM', {'label1': 'value'}, label2='x')
        self.assertEqual(result.eval(), {'a': 30, 'b': 25})

        result = self.source._select_aggregate('SUM', {('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): 30,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'x'): 25,
            ('b', 'y'): 40,
            ('b', 'z'): 5,
        }
        self.assertEqual(result.eval(), expected)

        result = self.source._select_aggregate('COUNT', {'label2': 'value'})
        self.assertEqual(result.eval(), {'x': 3, 'y': 2, 'z': 2})
