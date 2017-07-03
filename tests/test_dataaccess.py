# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import os
import re
import tempfile
import textwrap
from . import _io as io

from . import _unittest as unittest
from datatest.utils import collections
from datatest.utils.misc import _is_nsiterable

from datatest.dataaccess import working_directory
from datatest.dataaccess import BaseElement
from datatest.dataaccess import _is_collection_of_items
from datatest.dataaccess import DictItems
from datatest.dataaccess import DataResult
from datatest.dataaccess import _map_data
from datatest.dataaccess import _filter_data
from datatest.dataaccess import _reduce_data
from datatest.dataaccess import _apply_data
from datatest.dataaccess import _apply_to_data  # <- TODO: Change function name.
from datatest.dataaccess import _sqlite_sum
from datatest.dataaccess import _sqlite_count
from datatest.dataaccess import _sqlite_avg
from datatest.dataaccess import _sqlite_min
from datatest.dataaccess import _sqlite_max
from datatest.dataaccess import _sqlite_distinct
from datatest.dataaccess import _normalize_select
from datatest.dataaccess import _parse_select
from datatest.dataaccess import RESULT_TOKEN
from datatest.dataaccess import DataQuery
from datatest.dataaccess import DataSource


class TestWorkingDirectory(unittest.TestCase):
    def setUp(self):
        self.original_dir = os.getcwd()
        self.temporary_dir =  tempfile.mkdtemp()

    def tearDown(self):
        os.chdir(self.original_dir)
        os.rmdir(self.temporary_dir)

    def test_context_manager(self):
        original_dir = os.getcwd()

        with working_directory(self.temporary_dir):
            self.assertEqual(os.getcwd(), self.temporary_dir)

        self.assertEqual(os.getcwd(), original_dir)

    def test_decorator(self):
        original_dir = os.getcwd()

        @working_directory(self.temporary_dir)
        def myfunction():
            self.assertEqual(os.getcwd(), self.temporary_dir)
        myfunction()  # <- Actually run the function.

        self.assertEqual(os.getcwd(), original_dir)


class TestBaseElement(unittest.TestCase):
    def test_type_checking(self):
        # Base data elements include non-iterables, strings, and mappings.
        self.assertTrue(isinstance(123, BaseElement))
        self.assertTrue(isinstance('123', BaseElement))
        self.assertTrue(isinstance({'abc': '123'}, BaseElement))

        # Other iterable types are not considered base data elements.
        self.assertFalse(isinstance(['123'], BaseElement))
        self.assertFalse(isinstance(set(['123']), BaseElement))
        self.assertFalse(isinstance(iter([1, 2, 3]), BaseElement))

    def test_register_method(self):
        class CustomElement(object):
            def __iter__(self):
                return iter([1, 2, 3])

        custom_element = CustomElement()
        self.assertFalse(isinstance(custom_element, BaseElement))

        BaseElement.register(CustomElement)
        self.assertTrue(isinstance(custom_element, BaseElement))

    def test_direct_subclass(self):
        class CustomElement(BaseElement):
            def __init__(self):
                pass

            def __iter__(self):
                return iter([1, 2, 3])

        custom_element = CustomElement()
        self.assertTrue(isinstance(custom_element, BaseElement))


def convert_iter_to_type(iterable, target_type):
    """Helper function to convert lists-of-lists into tuple-of-tuples."""
    if isinstance(iterable, collections.Mapping):
        dic = {}
        for k, v in iterable.items():
            dic[k] = convert_iter_to_type(v, target_type)
        output = dic
    else:
        lst = []
        for obj in iterable:
            if _is_nsiterable(obj):
                obj = convert_iter_to_type(obj, target_type)
            lst.append(obj)
        output = target_type(lst)
    return output


class TestDataResult(unittest.TestCase):
    def test_init(self):
        untyped = iter([1, 2, 3, 4])

        typed = DataResult(untyped, list)
        self.assertEqual(typed.evaluation_type, list)

        typed = DataResult(iterable=untyped, evaluation_type=list)
        self.assertEqual(typed.evaluation_type, list)

        regex = 'evaluation_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = DataResult(untyped, [1, 2])


class TestDictItems(unittest.TestCase):
    def test_list_of_items(self):
        items = DictItems([('a', 1), ('b', 2)])
        self.assertEqual(list(items), [('a', 1), ('b', 2)])

    def test_iter_of_items(self):
        items = DictItems(iter([('a', 1), ('b', 2)]))
        self.assertEqual(list(items), [('a', 1), ('b', 2)])

    def test_dict(self):
        items = DictItems({'a': 1, 'b': 2})
        self.assertEqual(set(items), set([('a', 1), ('b', 2)]))

    def test_DataResult(self):
        result = DataResult(DictItems([('a', 1), ('b', 2)]), evaluation_type=dict)
        normalized = DictItems(result)
        self.assertEqual(list(normalized), [('a', 1), ('b', 2)])

    def test_DataQuery(self):
        source = DataSource([('x', 1), ('y', 2)], fieldnames=['A', 'B'])
        query = source({'A': 'B'}).apply(lambda x: next(x))
        normalized = DictItems(query)
        self.assertEqual(list(normalized), [('x', 1), ('y', 2)])

    def test_invalid_input(self):
        source = ['x', 1, 'y', 2]
        with self.assertRaises(TypeError):
            normalized = DictItems(source)

        source = [{'x': 1}, {'y': 2}]
        with self.assertRaises(TypeError):
            normalized = DictItems(source)


class TestIsCollectionOfItems(unittest.TestCase):
    def test_dictitems(self):
        items_iter = DictItems([('a', 1), ('b', 2)])
        self.assertTrue(_is_collection_of_items(items_iter))

    def test_dict_items(self):
        dict_src = {'a': 1, 'b': 2}
        dict_items = getattr(dict_src, 'iteritems', dict_src.items)()
        self.assertTrue(_is_collection_of_items(dict_items))


class TestMapData(unittest.TestCase):
    def test_dataiter_list(self):
        iterable = DataResult([1, 2, 3], list)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [2, 4, 6])

    def test_settype_to_list(self):
        iterable = DataResult([1, 2, 3], set)  # <- Starts as 'set'.

        function = lambda x: x % 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, list) # <- Now a 'list'.
        self.assertEqual(result.fetch(), [1, 0, 1])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _map_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_containers(self):
        iterable = DataResult({'a': [1, 2], 'b': (3, 4)}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [2, 4], 'b': (6, 8)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 4, 'b': 6})

    def test_unpacking_behavior(self):
        data = [(1, 2), (1, 4), (1, 8)]

        function = lambda x, y: x / y  # <- function takes 2 args
        result = _map_data(function, DataResult(data, list))
        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [0.5, 0.25, 0.125])

        function = lambda z: z[0] / z[1]  # <- function takes 1 arg
        result = _map_data(function, DataResult(data, list))
        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [0.5, 0.25, 0.125])


class TestFilterData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([-4, -1, 2, 3], list)

        function = lambda x: x > 0
        result = _filter_data(function, iterable)
        self.assertEqual(result.fetch(), [2, 3])

    def test_bad_iterable_type(self):
        function = lambda x: x > 0
        with self.assertRaises(TypeError):
            _filter_data(function, 3)  # <- int

        function = lambda x: x == 'a'
        with self.assertRaises(TypeError):
            _filter_data(function, 'b')  # <- str

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, 3], 'b': [4, 5, 6]}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [], 'b': [4, 6]})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        iseven = lambda x: x % 2 == 0
        with self.assertRaises(TypeError):
            result = _filter_data(iseven, iterable)
            #result.fetch()


class TestReduceData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3], list)

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
        iterable = DataResult({'a': [1, 2], 'b': [3, 4]}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class TestGroupwiseApply(unittest.TestCase):
    def test_dataiter_list(self):
        iterable = DataResult([1, 2, 3], list)
        function = lambda itr: [x * 2 for x in itr]
        result = _apply_data(function, iterable)
        self.assertEqual(result, [2, 4, 6])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _apply_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_mixed_iterables(self):
        iterable = DataResult({'a': iter([1, 2]), 'b': (3, 4)}, dict)

        function = lambda itr: [x * 2 for x in itr]
        result = _apply_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [2, 4], 'b': [6, 8]})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _apply_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 4, 'b': 6})


class TestSumData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3], list)
        result = _sqlite_sum(iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        result = _sqlite_sum(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_sum('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, 2], 'b': [3, 4]}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class TestCountData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult(['a', None, 3], list)
        result = _sqlite_count(iterable)
        self.assertEqual(result, 2)

    def test_single_value(self):
        result = _sqlite_count(3)
        self.assertEqual(result, 1)

        result = _sqlite_count('abc')
        self.assertEqual(result, 1)

        result = _sqlite_count(None)
        self.assertEqual(result, 0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, None], 'b': ['x', None, 0]}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 2})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': -5, 'b': None, 'c': 'xyz'}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 0, 'c': 1})


class TestAvgData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_avg(iterable)
        self.assertEqual(result, 2.5)

    def test_single_integer(self):
        result = _sqlite_avg(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_avg('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, None],
            'b': ['xx', 1, 2, 3, None],
            'c': [None, None, None]}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1.5, 'b': 1.5, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestMinData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_min(iterable)
        self.assertEqual(result, 1)

    def test_single_integer(self):
        result = _sqlite_min(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_min('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 1, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestMaxData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_max(iterable)
        self.assertEqual(result, 4)

    def test_single_integer(self):
        result = _sqlite_max(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_max('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 'xx', 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestDistinctData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 1, 2, 3], list)
        result = _sqlite_distinct(iterable)
        self.assertEqual(result.fetch(), [1, 2, 3])

    def test_single_int(self):
        result = _sqlite_distinct(3)
        self.assertEqual(result, 3)

    def test_dataiter_dict_of_containers(self):
        iterable = DataResult({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [1, 2], 'b': (3, 4)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class Test_select_functions(unittest.TestCase):
    def test_normalize_select(self):
        no_change = 'no change for valid containers'

        self.assertEqual(_normalize_select(['A']), ['A'], msg=no_change)

        self.assertEqual(_normalize_select(set(['A'])), set(['A']), msg=no_change)

        self.assertEqual(
            _normalize_select([('A', 'B')]),
            [('A', 'B')],
            msg=no_change,
        )

        self.assertEqual(
            _normalize_select({'A': ['B']}),
            {'A': ['B']},
            msg=no_change)

        self.assertEqual(
            _normalize_select({'A': [('B', 'C')]}),
            {'A': [('B', 'C')]},
            msg=no_change)

        self.assertEqual(
            _normalize_select({('A', 'B'): ['C']}),
            {('A', 'B'): ['C']},
            msg=no_change)

        default_list = 'unwrapped column or multi-column selects should get list wrapper'

        self.assertEqual(_normalize_select('A'), ['A'], msg=no_change)

        self.assertEqual(
            _normalize_select(('A', 'B')),
            [('A', 'B')],
            msg=no_change)

        self.assertEqual(
            _normalize_select({'A': 'B'}),
            {'A': ['B']},
            msg=no_change)

        self.assertEqual(
            _normalize_select({('A', 'B'): 'C'}),
            {('A', 'B'): ['C']},
            msg=no_change)

        self.assertEqual(
            _normalize_select({'A': ('B', 'C')}),
            {'A': [('B', 'C')]},
            msg=no_change)

        unsupported = 'unsupported values should raise error'

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_select(1)

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_select({'A': {'B': ['C']}})  # Nested mapping.

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_select(['A', ['B']])  # Nested list.

    def test_parse_select(self):
        key, value = _parse_select(['A'])  # Single column.
        self.assertEqual(key, tuple())
        self.assertEqual(value, ['A'])

        key, value = _parse_select([('A', 'B')])  # Multiple colummns.
        self.assertEqual(key, tuple())
        self.assertEqual(value, [('A', 'B')])

        key, value = _parse_select({'A': ['B']})  # Mapping.
        self.assertEqual(key, 'A')
        self.assertEqual(value, ['B'])

        key, value = _parse_select({'A': [('B', 'C')]})  # Mapping with multi-column value.
        self.assertEqual(key, 'A')
        self.assertEqual(value, [('B', 'C')])

        key, value = _parse_select({('A', 'B'): ['C']})  # Mapping with multi-column key.
        self.assertEqual(key, ('A', 'B'))
        self.assertEqual(value, ['C'])


class TestDataQuery(unittest.TestCase):
    def test_init_no_data(self):
        # Use select-only syntax.
        query = DataQuery(['foo'], bar='baz')
        self.assertEqual(query._data_source, None)

        # Pass empty source explicitly.
        query = DataQuery.from_object(None, ['foo'], bar='baz')
        self.assertEqual(query._data_source, None)

        # Test query steps.
        query = DataQuery(['foo'], bar='baz')
        self.assertEqual(query._query_steps, tuple())

        # Adding query steps.
        query = query.distinct().sum()
        expected = tuple([('distinct', (), {}), ('sum', (), {})])
        self.assertEqual(query._query_steps, expected)

        # Single-string defaults to list-of-single-string.
        query = DataQuery('foo')
        self.assertEqual(query._data_args[0][0], ['foo'], 'should be wrapped as list')

        # Multi-item-container defaults to list-of-container.
        query = DataQuery(['foo', 'bar'])
        self.assertEqual(query._data_args[0][0], [['foo', 'bar']], 'should be wrapped as list')

        # Mapping with single-string defaults to list-of-single-string.
        query = DataQuery({'foo': 'bar'})
        self.assertEqual(query._data_args[0][0], {'foo': ['bar']}, 'value should be wrapped as list')

        # Mapping with multi-item-container defaults to list-of-container.
        query = DataQuery({'foo': ['bar', 'baz']})
        self.assertEqual(query._data_args[0][0], {'foo': [['bar', 'baz']]}, 'value should be wrapped as list')

    def test_init_from_object(self):
        # Using DataSource object.
        source = DataSource([(1, 2), (1, 2)], fieldnames=['A', 'B'])
        query = DataQuery.from_object(source, ['A'], B=2)
        self.assertEqual(query._data_source, source)
        self.assertEqual(query._data_args, ((['A'],), {'B': 2}))
        self.assertEqual(query._query_steps, ())

        # Using another DataQuery object.
        source = DataSource([(1, 2), (1, 2)], fieldnames=['A', 'B'])
        query1 = DataQuery.from_object(source, ['A'], B=2)
        query2 = DataQuery.from_object(query1)
        self.assertEqual(query2._data_source, source)
        self.assertEqual(query2._data_args, ((['A'],), {'B': 2}))
        self.assertEqual(query2._query_steps, ())

        # Using non-DataSource object.
        query = DataQuery.from_object([1, 3, 4, 2])
        self.assertEqual(query._data_source, [1, 3, 4, 2])
        self.assertEqual(query._data_args, ((), {}))
        self.assertEqual(query._query_steps, ())

        # Using non-DataSource object.
        with self.assertRaises(ValueError):
            query = DataQuery.from_object([1, 3, 4, 2], 'foo', bar='baz')

    def test_init_with_invalid_args(self):
        # Missing args.
        with self.assertRaises(TypeError, msg='should require select args'):
            DataQuery()

        # Bad "select" field.
        source = DataSource([(1, 2), (1, 2)], fieldnames=['A', 'B'])
        with self.assertRaises(LookupError, msg='should fail immediately when fieldname conflicts with provided source'):
            query = DataQuery.from_object(source, ['X'], B=2)

        # Bad "where" field.
        source = DataSource([(1, 2), (1, 2)], fieldnames=['A', 'B'])
        with self.assertRaises(LookupError, msg='should fail immediately when fieldname conflicts with provided "where" field'):
            query = DataQuery.from_object(source, ['A'], Y=2)

    def test_init_with_nested_dicts(self):
        """Support for nested dictionaries was removed (for now).
        It's likely that arbitrary nesting would complicate the ability
        to check complex data values that are, themselves, mappings
        (like probability mass functions represented as a dictionary).
        """
        regex = 'mappings can not be nested'
        with self.assertRaisesRegex(ValueError, regex):
            query = DataQuery({'A': {'B': 'C'}}, D='x')

    def test__copy__(self):
        # Select-arg only.
        query = DataQuery(['B'])
        copied = query.__copy__()
        self.assertEqual(copied._data_source, query._data_source)
        self.assertEqual(copied._data_args, query._data_args)
        self.assertEqual(copied._query_steps, query._query_steps)

        # Select and keyword.
        query = DataQuery(['B'], C='x')
        copied = query.__copy__()
        self.assertEqual(copied._data_source, query._data_source)
        self.assertEqual(copied._data_args, query._data_args)
        self.assertEqual(copied._query_steps, query._query_steps)

        # Source, select, and keyword.
        source = DataSource([(1, 2), (1, 2)], fieldnames=['A', 'B'])
        query = DataQuery.from_object(source, ['B'])
        copied = query.__copy__()
        self.assertEqual(copied._data_source, query._data_source)
        self.assertEqual(copied._data_args, query._data_args)
        self.assertEqual(copied._query_steps, query._query_steps)

        # Select and additional query methods.
        query = DataQuery(['B']).map(lambda x: str(x).upper())
        copied = query.__copy__()
        self.assertEqual(copied._data_source, query._data_source)
        self.assertEqual(copied._data_args, query._data_args)
        self.assertEqual(copied._query_steps, query._query_steps)

    def test_fetch_datasource(self):
        source = DataSource([('1', '2'), ('1', '2')], fieldnames=['A', 'B'])
        query = DataQuery.from_object(source, ['B'])
        query._query_steps = [
            ('map', (int,), {}),
            ('map', (lambda x: x * 2,), {}),
            ('sum', (), {}),
        ]
        result = query.fetch()
        self.assertEqual(result, 8)

    def test_execute_datasource(self):
        source = DataSource([('1', '2'), ('1', '2')], fieldnames=['A', 'B'])
        query = DataQuery.from_object(source, ['B'])
        query._query_steps = [
            ('map', (int,), {}),
            ('map', (lambda x: x * 2,), {}),
            ('sum', (), {}),
        ]
        result = query()
        self.assertEqual(result, 8)

        query = DataQuery(['A'])
        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            query(['hello', 'world'])  # <- Expects None or DataQuery, not list!

    def test_execute_other_source(self):
        query = DataQuery.from_object([1, 3, 4, 2])
        result = query()
        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.fetch(), [1, 3, 4, 2])

    def test_map(self):
        query1 = DataQuery(['col2'])
        query2 = query1.map(int)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], fieldnames=['col1', 'col2'])
        result = query2(source)
        self.assertEqual(result.fetch(), [2, 2])

    def test_filter(self):
        query1 = DataQuery(['col1'])
        query2 = query1.filter(lambda x: x == 'a')
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], fieldnames=['col1', 'col2'])
        result = query2(source)
        self.assertEqual(result.fetch(), ['a'])

        # No filter arg should default to bool()
        source = DataSource([(1,), (2,), (0,), (3,)], fieldnames=['col1'])
        query = DataQuery(set(['col1'])).filter()  # <- No arg!
        result = query(source)
        self.assertEqual(result.fetch(), set([1, 2, 3]))

    def test_reduce(self):
        query1 = DataQuery(['col1'])
        query2 = query1.reduce(lambda x, y: x + y)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], fieldnames=['col1', 'col2'])
        result = query2(source)
        self.assertEqual(result, 'ab')

    def test_optimize_aggregation(self):
        """
        Unoptimized:
            DataSource._select({'col1': ['values']}, col2='xyz').sum()

        Optimized:
            DataSource._select_aggregate('SUM', {'col1': ['values']}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
            (_apply_to_data, (_sqlite_sum, RESULT_TOKEN,), {}),
        )
        optimized = DataQuery._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_aggregate'), {}),
            (RESULT_TOKEN, ('SUM', {'col1': ['values']},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_distinct(self):
        """
        Unoptimized:
            DataSource._select({'col1': ['values']}, col2='xyz').distinct()

        Optimized:
            DataSource._select_distinct({'col1': ['values']}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
            (_sqlite_distinct, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_explain(self):
        query = DataQuery(['col1'])
        expected = """
            Data Source:
              <none given> (assuming DataSource object)
            Execution Plan:
              getattr, (<RESULT>, '_select'), {}
              <RESULT>, (['col1']), {}
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(query._explain(file=None), expected)

        # TODO: Add assert for query that can be optimized.

    def test_explain2(self):
        query = DataQuery(['label1'])

        expected = """
            Data Source:
              <none given> (assuming DataSource object)
            Execution Plan:
              getattr, (<RESULT>, '_select'), {}
              <RESULT>, (['label1']), {}
        """
        expected = textwrap.dedent(expected).strip()

        # Defaults to stdout (redirected to StringIO for testing).
        string_io = io.StringIO()
        returned_value = query._explain(file=string_io)
        self.assertIsNone(returned_value)

        printed_value = string_io.getvalue().strip()
        self.assertEqual(printed_value, expected)

        # Get result as string.
        returned_value = query._explain(file=None)
        self.assertEqual(returned_value, expected)

    def test_repr(self):
        # Check "select-only" signature.
        query = DataQuery(['label1'])
        regex = r"DataQuery\(\[u?'label1'\]\)"
        self.assertRegex(repr(query), regex)

        # Check "select-only" with keyword string.
        query = DataQuery(['label1'], label2='x')
        regex = r"DataQuery\(\[u?'label1'\], label2='x'\)"
        self.assertRegex(repr(query), regex)

        # Check "select-only" with keyword list.
        query = DataQuery(['label1'], label2=['x', 'y'])
        regex = r"DataQuery\(\[u?'label1'\], label2=\[u?'x', u?'y'\]\)"
        self.assertRegex(repr(query), regex)

        # Check "from_object" signature.
        query = DataQuery.from_object(
            DataSource([('x', 1), ('y', 2), ('z', 3)], ['A', 'B']),
            ['A'],
        )
        regex = (
            r"DataQuery\.from_object\(DataSource\(<list of records>, "
            r"fieldnames=\(u?'A', u?'B'\)\), \[u?'A'\]\)"
        )
        regex = textwrap.dedent(regex).strip()
        self.assertRegex(repr(query), regex)

        # Check query steps.
        query = DataQuery(['label1']).distinct().count()
        regex = r"DataQuery\(\[u?'label1'\]\).distinct\(\).count\(\)"
        self.assertRegex(repr(query), regex)

        # Check query steps with function argument.
        def upper(x):
            return str(x.upper())
        query = DataQuery(['label1']).map(upper)
        regex = r"DataQuery\(\[u?'label1'\]\).map\(upper\)"
        self.assertRegex(repr(query), regex)

        # Check query steps with lambda argument.
        lower = lambda x: str(x).lower()
        query = DataQuery(['label1']).map(lower)
        regex = r"DataQuery\(\[u?'label1'\]\).map\(<lambda>\)"
        self.assertRegex(repr(query), regex)


class TestDataSourceConstructors(unittest.TestCase):
    @staticmethod
    def get_table_contents(source):
        connection = source._connection
        table = source._table
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM ' + table)
        return list(cursor)

    def test_from_sequence_rows(self):
        data = [('x', 1),
                ('y', 2),
                ('z', 3)]
        fieldnames = ['A', 'B']

        source = DataSource(data, fieldnames)
        table_contents = self.get_table_contents(source)
        self.assertEqual(set(table_contents), set(data))

    def test_from_dict_rows(self):
        data = [{'A': 'x', 'B': 1},
                {'A': 'y', 'B': 2},
                {'A': 'z', 'B': 3}]

        source = DataSource(data)
        table_contents = self.get_table_contents(source)
        expected = [('x', 1), ('y', 2), ('z', 3)]
        self.assertEqual(set(table_contents), set(expected))

        source = DataSource(data, fieldnames=['B', 'A'])  # <- Set field order.
        table_contents = self.get_table_contents(source)
        expected = [(1, 'x'), (2, 'y'), (3, 'z')]
        self.assertEqual(set(table_contents), set(expected))

    @staticmethod
    def _get_filelike(string, encoding):
        """Return file-like stream object."""
        import _io as io
        import sys
        filelike = io.BytesIO(string)
        if encoding and sys.version >= '3':
            filelike = io.TextIOWrapper(filelike, encoding=encoding)
        return filelike

    def test_from_csv_file(self):
        csv_file = self._get_filelike(b'A,B\n'
                                      b'x,1\n'
                                      b'y,2\n'
                                      b'z,3\n', encoding='utf-8')
        source = DataSource.from_csv(csv_file)
        table_contents = self.get_table_contents(source)
        expected = [('x', '1'), ('y', '2'), ('z', '3')]
        self.assertEqual(set(table_contents), set(expected))

    def test_from_multiple_csv_files(self):
        file1 = self._get_filelike(b'A,B\n'
                                   b'x,1\n'
                                   b'y,2\n'
                                   b'z,3\n', encoding='utf-8')

        file2 = self._get_filelike(b'B,C\n'
                                   b'4,j\n'
                                   b'5,k\n'
                                   b'6,l\n', encoding='ascii')

        source = DataSource.from_csv([file1, file2])
        table_contents = self.get_table_contents(source)

        expected = [('x', '1', ''), ('y', '2', ''), ('z', '3', ''),
                    ('', '4', 'j'), ('', '5', 'k'), ('', '6', 'l')]
        self.assertEqual(set(table_contents), set(expected))


class TestDataSourceBasics(unittest.TestCase):
    def setUp(self):
        fieldnames = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, fieldnames)

    def test_fieldnames(self):
        expected = ('label1', 'label2', 'value')
        self.assertEqual(self.source.fieldnames, expected)

    def test_repr(self):
        data = [['x', 100], ['y', 200], ['z', 300]]
        filednames = ['A', 'B']
        source = DataSource(data, filednames)

        regex = r"DataSource\(<list of records>, fieldnames=\(u?'A', u?'B'\)\)"
        self.assertRegex(repr(source), regex)

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

    def test_select_list_of_strings(self):
        result = self.source._select(['label1'])
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(result.fetch(), expected)

    def test_select_tuple_of_strings(self):
        result = self.source._select(('label1',))
        expected = ('a', 'a', 'a', 'a', 'b', 'b', 'b')
        self.assertEqual(result.fetch(), expected)

    def test_select_set_of_strings(self):
        result = self.source._select(set(['label1']))
        expected = set(['a', 'b'])
        self.assertEqual(result.fetch(), expected)

    def test_select_field_not_found(self):
        with self.assertRaises(LookupError):
            result = self.source._select(['bad_field_name'])

    def test_select_list_of_lists(self):
        result = self.source._select([['label1']])
        expected = [['a'], ['a'], ['a'], ['a'], ['b'], ['b'], ['b']]
        self.assertEqual(result.fetch(), expected)

        result = self.source._select([['label1', 'label2']])
        expected = [['a', 'x'], ['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        self.assertEqual(result.fetch(), expected)

    def test_select_list_of_tuples(self):
        result = self.source._select([('label1',)])
        expected = [('a',), ('a',), ('a',), ('a',), ('b',), ('b',), ('b',)]
        self.assertEqual(result.fetch(), expected)

    def test_select_list_of_namedtuples(self):
        namedtup = collections.namedtuple('namedtup', ['label1', 'label2'])
        result = self.source._select([namedtup('label1', 'label2')])
        expected = [namedtup(label1='a', label2='x'),
                    namedtup(label1='a', label2='x'),
                    namedtup(label1='a', label2='y'),
                    namedtup(label1='a', label2='z'),
                    namedtup(label1='b', label2='z'),
                    namedtup(label1='b', label2='y'),
                    namedtup(label1='b', label2='x')]
        self.assertEqual(result.fetch(), expected)

    def test_select_set_of_frozensets(self):
        result = self.source._select(set([frozenset(['label1'])]))
        expected = set([frozenset(['a']), frozenset(['a']),
                        frozenset(['a']), frozenset(['a']),
                        frozenset(['b']), frozenset(['b']),
                        frozenset(['b'])])
        self.assertEqual(result.fetch(), expected)

    def test_select_dict(self):
        result = self.source._select({'label1': ['value']})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict2(self):
        result = self.source._select({('label1', 'label2'): ['value']})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict3(self):
        result = self.source._select({('label1', 'label2'): [['value']]})
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict_with_namedtuple_keys(self):
        namedtup = collections.namedtuple('namedtup', ['x', 'y'])
        result = self.source._select({namedtup('label1', 'label2'): ['value']})
        expected = {
            namedtup(x='a', y='x'): ['17', '13'],
            namedtup(x='a', y='y'): ['20'],
            namedtup(x='a', y='z'): ['15'],
            namedtup(x='b', y='x'): ['25'],
            namedtup(x='b', y='y'): ['40'],
            namedtup(x='b', y='z'): ['5'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict_with_values_container2(self):
        result = self.source._select({'label1': [('label2', 'label2')]})
        expected = {
            'a': [('x', 'x'), ('x', 'x'), ('y', 'y'), ('z', 'z')],
            'b': [('z', 'z'), ('y', 'y'), ('x', 'x')]
        }
        self.assertEqual(result.fetch(), expected)

        result = self.source._select({'label1': [set(['label2', 'label2'])]})
        expected = {
            'a': [set(['x']), set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_alternate_mapping_type(self):
        class CustomDict(dict):
            pass

        result = self.source._select(CustomDict({'label1': ['value']}))
        result = result.fetch()
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertIsInstance(result, CustomDict)
        self.assertEqual(result, expected)

    def test_select_distinct(self):
        result = self.source._select_distinct(['label1'])
        expected = ['a', 'b']
        self.assertEqual(list(result), expected)

        result = self.source._select_distinct({'label1': ['label2']})
        expected = {'a': ['x', 'y', 'z'], 'b': ['z', 'y', 'x']}
        self.assertEqual(result.fetch(), expected)

    def test_select_aggregate(self):
        # Not grouped, single result.
        result = self.source._select_aggregate('COUNT', ['label2'])
        self.assertEqual(result, 7)

        # Not grouped, single result as set.
        result = self.source._select_aggregate('COUNT', set(['label2']))
        self.assertEqual(result, 3)

        # Not grouped, multiple results.
        result = self.source._select_aggregate('SUM', [['value', 'value']])
        self.assertEqual(result, [135, 135])

        # Simple group by (grouped by keys).
        result = self.source._select_aggregate('SUM', {'label1': ['value']})
        self.assertIsInstance(result, DataResult)

        expected = {
            'a': 65,
            'b': 70,
        }
        self.assertEqual(result.fetch(), expected)

        # Composite value.
        result = self.source._select_aggregate('SUM', {'label1': [('value', 'value')]})
        expected = {
            'a': (65, 65),
            'b': (70, 70),
        }
        self.assertEqual(dict(result), expected)

        # Composite key and composite value.
        result = self.source._select_aggregate('SUM', {('label1', 'label1'): [['value', 'value']]})
        expected = {
            ('a', 'a'): [65, 65],
            ('b', 'b'): [70, 70],
        }
        self.assertEqual(dict(result), expected)

    def test_call(self):
        query = self.source(['label1'])
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.fetch(), expected)

        query = self.source([('label1', 'label2')])
        expected = [('a', 'x'), ('a', 'x'), ('a', 'y'), ('a', 'z'),
                    ('b', 'z'), ('b', 'y'), ('b', 'x')]
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.fetch(), expected)

        query = self.source([set(['label1', 'label2'])])
        expected = [set(['a', 'x']),
                    set(['a', 'x']),
                    set(['a', 'y']),
                    set(['a', 'z']),
                    set(['b', 'z']),
                    set(['b', 'y']),
                    set(['b', 'x'])]
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.fetch(), expected)

        query = self.source({'label1': ['label2']})
        expected = {'a': ['x', 'x', 'y', 'z'], 'b': ['z', 'y', 'x']}
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.fetch(), expected)
