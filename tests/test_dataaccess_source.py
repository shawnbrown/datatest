# -*- coding: utf-8 -*-
from __future__ import absolute_import
import textwrap

from . import _unittest as unittest
from datatest.utils import collections
from datatest.dataaccess.source import DataSource
from datatest.dataaccess.source import DataQuery
from datatest.dataaccess.source import DataQuery2
from datatest.dataaccess.source import RESULT_TOKEN
from datatest.dataaccess.source import DataIterator
from datatest.dataaccess.source import _map_data
from datatest.dataaccess.source import _filter_data
from datatest.dataaccess.source import _reduce_data
from datatest.dataaccess.source import _aggregate_data
from datatest.dataaccess.source import _sum_data
from datatest.dataaccess.source import _count_data
from datatest.dataaccess.source import _avg_data
from datatest.dataaccess.source import _min_data
from datatest.dataaccess.source import _max_data
from datatest.dataaccess.source import _distinct_data
from datatest.dataaccess.source import _set_data
from datatest.dataaccess.source import _cast_as_set
from datatest.dataaccess.source import ItemsIter
from datatest.dataaccess.query import BaseQuery
from datatest.dataaccess.result import DataResult


class TestDataIterator(unittest.TestCase):
    def test_init(self):
        untyped = iter([1, 2, 3, 4])

        typed = DataIterator(untyped, list)
        self.assertEqual(typed.intended_type, list)

        typed = DataIterator(iterable=untyped, intended_type=list)
        self.assertEqual(typed.intended_type, list)

        regex = 'intended_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = DataIterator(untyped, [1, 2])


class TestItemsIter(unittest.TestCase):
    def test_itemsiter(self):
        foo = ItemsIter([1,2,3])
        self.assertEqual(list(foo), [1,2,3])


class TestMapData(unittest.TestCase):
    def test_dataiter_list(self):
        iterable = DataIterator([1, 2, 3], list)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, list)
        self.assertEqual(result.evaluate(), [2, 4, 6])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _map_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_containers(self):
        iterable = DataIterator({'a': [1, 2], 'b': (3, 4)}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': [2, 4], 'b': (6, 8)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 4, 'b': 6})


class TestFilterData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([-4, -1, 2, 3], list)

        function = lambda x: x > 0
        result = _filter_data(function, iterable)
        self.assertEqual(result.evaluate(), [2, 3])

    def test_bad_iterable_type(self):
        function = lambda x: x > 0
        with self.assertRaises(TypeError):
            _filter_data(function, 3)  # <- int

        function = lambda x: x == 'a'
        with self.assertRaises(TypeError):
            _filter_data(function, 'b')  # <- str

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({'a': [1, 2, 3], 'b': [4, 5, 6]}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': [2], 'b': [4, 6]})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)
        with self.assertRaises(TypeError):
            result.evaluate()


class TestReduceData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 3], list)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        function = lambda x, y: x + y
        result = _reduce_data(function, 3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        function = lambda x, y: x + y
        result = _reduce_data(function, 'abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({'a': [1, 2], 'b': [3, 4]}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestSumData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 3], list)
        result = _sum_data(iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        result = _sum_data(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sum_data('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({'a': [1, 2], 'b': [3, 4]}, dict)
        result = _aggregate_data(_sum_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)
        result = _aggregate_data(_sum_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestCountData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator(['a', None, 3], list)
        result = _count_data(iterable)
        self.assertEqual(result, 2)

    def test_single_value(self):
        result = _count_data(3)
        self.assertEqual(result, 1)

        result = _count_data('abc')
        self.assertEqual(result, 1)

        result = _count_data(None)
        self.assertEqual(result, 0)

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({'a': [1, None], 'b': ['x', None, 0]}, dict)
        result = _aggregate_data(_count_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 2})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': -5, 'b': None, 'c': 'xyz'}, dict)
        result = _aggregate_data(_count_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 0, 'c': 1})


class TestAvgData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 3, 4], list)
        result = _avg_data(iterable)
        self.assertEqual(result, 2.5)

    def test_single_integer(self):
        result = _avg_data(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _avg_data('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({
            'a': [1, 2, None],
            'b': ['xx', 1, 2, 3, None],
            'c': [None, None, None]}, dict)
        result = _aggregate_data(_avg_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1.5, 'b': 1.5, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3, 'c': None}, dict)
        result = _aggregate_data(_avg_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestMinData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 3, 4], list)
        result = _min_data(iterable)
        self.assertEqual(result, 1)

    def test_single_integer(self):
        result = _min_data(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _min_data('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _aggregate_data(_min_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 1, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3, 'c': None}, dict)
        result = _aggregate_data(_min_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestMaxData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 3, 4], list)
        result = _max_data(iterable)
        self.assertEqual(result, 4)

    def test_single_integer(self):
        result = _max_data(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _max_data('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataIterator({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _aggregate_data(_max_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 'xx', 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataIterator({'a': 2, 'b': 3, 'c': None}, dict)
        result = _aggregate_data(_max_data, iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestDistinctData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 1, 2, 3], list)
        result = _distinct_data(iterable)
        self.assertEqual(result.evaluate(), [1, 2, 3])

    def test_single_int(self):
        result = _distinct_data(3)
        self.assertEqual(result, 3)

    def test_dataiter_dict_of_containers(self):
        iterable = DataIterator({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _distinct_data(iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': [1, 2], 'b': (3, 4)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)
        result = _distinct_data(iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestSetData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataIterator([1, 2, 1, 2, 3], list)
        result = _set_data(iterable)
        self.assertEqual(result.evaluate(), set([1, 2, 3]))

    def test_single_int(self):
        result = _set_data(3)
        self.assertEqual(result.evaluate(), set([3]))

    def test_dataiter_dict_of_containers(self):
        iterable = DataIterator({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _set_data(iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': set([1, 2]), 'b': set([3, 4])})

    def test_dataiter_dict_of_ints(self):
        iterable = DataIterator({'a': 2, 'b': 3}, dict)
        result = _set_data(iterable)

        self.assertIsInstance(result, DataIterator)
        self.assertEqual(result.intended_type, dict)
        self.assertEqual(result.evaluate(), {'a': set([2]), 'b': set([3])})


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

    def test_optimize_sum(self):
        """
        Unoptimized:
            DataQuery2._select2({'col1': 'values'}, col2='xyz').sum()

        Optimized:
            DataQuery2._select2_aggregate('SUM', {'col1': 'values'}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_sum_data, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery2._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select2_aggregate'), {}),
            (RESULT_TOKEN, ('SUM', {'col1': 'values'},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_distinct(self):
        """
        Unoptimized:
            DataQuery2._select2({'col1': 'values'}, col2='xyz').distinct()

        Optimized:
            DataQuery2._select2_distinct({'col1': 'values'}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_distinct_data, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery2._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select2_distinct'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_set(self):
        """
        Unoptimized:
            DataQuery2._select2({'col1': 'values'}, col2='xyz').set()

        Optimized:
            DataQuery2._select2_distinct({'col1': 'values'}, col2='xyz')._cast_as_set()
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_set_data, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery2._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select2_distinct'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_cast_as_set, (RESULT_TOKEN,), {}),
        )
        self.assertEqual(optimized, expected)

    def test_explain(self):
        query = DataQuery2('col1')
        expected = """
            Steps:
              getattr, (<result>, '_select2'), {}
              <result>, ('col1'), {}
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(query.explain(), expected)

        # TODO: Add assert for query that can be optimized.


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
