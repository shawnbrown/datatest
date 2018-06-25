# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
import os
import re
import shutil
import sqlite3
import tempfile
import textwrap
from . import _io as io

from . import _unittest as unittest
from datatest._compatibility.builtins import *
from datatest._compatibility import collections
from datatest._utils import nonstringiter

from datatest._load.working_directory import working_directory
from datatest._query.query import (
    _to_csv,
    BaseElement,
    _is_collection_of_items,
    DictItems,
    _map_data,
    _filter_data,
    _reduce_data,
    _flatten_data,
    _apply_data,
    _apply_to_data,  # <- TODO: Change function name.
    _sqlite_sum,
    _sqlite_count,
    _sqlite_avg,
    _sqlite_min,
    _sqlite_max,
    _sqlite_distinct,
    _normalize_columns,
    _parse_columns,
    RESULT_TOKEN,
    Query,
    Result,
    Selector,
)


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
            if nonstringiter(obj):
                obj = convert_iter_to_type(obj, target_type)
            lst.append(obj)
        output = target_type(lst)
    return output


class TestResult(unittest.TestCase):
    def test_init(self):
        untyped = iter([1, 2, 3, 4])

        typed = Result(untyped, list)
        self.assertEqual(typed.evaluation_type, list)

        typed = Result(iterable=untyped, evaluation_type=list)
        self.assertEqual(typed.evaluation_type, list)

        regex = 'evaluation_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = Result(untyped, [1, 2])


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

    def test_empty_iterable(self):
        items = DictItems(iter([]))
        self.assertEqual(list(items), [])

    def test_Result(self):
        result = Result(DictItems([('a', 1), ('b', 2)]), evaluation_type=dict)
        normalized = DictItems(result)
        self.assertEqual(list(normalized), [('a', 1), ('b', 2)])

    def test_Query(self):
        source = Selector([('A', 'B'), ('x', 1), ('y', 2)])
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
        iterable = Result([1, 2, 3], list)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [2, 4, 6])

    def test_settype_to_list(self):
        iterable = Result([1, 2, 3], set)  # <- Starts as 'set'.

        function = lambda x: x % 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list) # <- Now a 'list'.
        self.assertEqual(result.fetch(), [1, 0, 1])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _map_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_containers(self):
        iterable = Result({'a': [1, 2], 'b': (3, 4)}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [2, 4], 'b': (6, 8)})

    def test_dataiter_dict_of_ints(self):
        iterable = Result({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 4, 'b': 6})

    def test_unpacking_behavior(self):
        data = [(1, 2), (1, 4), (1, 8)]

        function = lambda x, y: x / y  # <- function takes 2 args
        result = _map_data(function, Result(data, list))
        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [0.5, 0.25, 0.125])

        function = lambda z: z[0] / z[1]  # <- function takes 1 arg
        result = _map_data(function, Result(data, list))
        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.fetch(), [0.5, 0.25, 0.125])


class TestFilterData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([-4, -1, 2, 3], list)

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
        iterable = Result({'a': [1, 3], 'b': [4, 5, 6]}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [], 'b': [4, 6]})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3}, dict)

        iseven = lambda x: x % 2 == 0
        with self.assertRaises(TypeError):
            result = _filter_data(iseven, iterable)
            #result.fetch()


class TestFlattenData(unittest.TestCase):
    def test_nonmapping_iters(self):
        """Non-mapping iterables should be returned unchanged."""
        iterable = Result([-4, -1, 2, 3], list)
        result = _flatten_data(iterable)
        self.assertEqual(result.fetch(), [-4, -1, 2, 3])

        iterable = Result(set([1, 2, 3]), set)
        result = _flatten_data(iterable)
        self.assertEqual(result.fetch(), set([1, 2, 3]))

    def test_base_elements(self):
        """Base elements should be return unchanged."""
        result = _flatten_data(3)
        self.assertEqual(result, 3)

        result = _flatten_data('b')
        self.assertEqual(result, 'b')

    def test_dict_iter_of_lists(self):
        source_data = collections.OrderedDict([('a', [1, 3]), ('b', [4, 5, 6])])
        iterable = Result(source_data, dict)

        result = _flatten_data(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(
            result.fetch(),
            [('a', 1), ('a', 3), ('b', 4), ('b', 5), ('b', 6)]
        )

    def test_dict_iter_of_tuples(self):
        source_data = collections.OrderedDict([('a', (1, 2)), ('b', (3, 4))])
        iterable = Result(source_data, dict)

        result = _flatten_data(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(
            result.fetch(),
            [('a', 1, 2), ('b', 3, 4)]
        )

    def test_dict_iter_of_integers(self):
        source_data = collections.OrderedDict([('a', 2), ('b', 4)])
        iterable = Result(source_data, dict)

        result = _flatten_data(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(
            result.fetch(),
            [('a', 2), ('b', 4)]
        )

    def test_dict_iter_of_dicts(self):
        """Dicts should be treated as base elements (should not unpack
        deeply nested dicts).
        """
        source_data = collections.OrderedDict([('a', {'x': 2}), ('b', {'y': 4})])
        iterable = Result(source_data, dict)

        result = _flatten_data(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(
            result.fetch(),
            [('a', {'x': 2}), ('b', {'y': 4})]
        )

    def test_raw_dictionary(self):
        iterable = collections.OrderedDict([('a', [1, 3]), ('b', [4, 5, 6])])

        result = _flatten_data(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(
            result.fetch(),
            [('a', 1), ('a', 3), ('b', 4), ('b', 5), ('b', 6)]
        )


class TestReduceData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 3], list)

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
        iterable = Result({'a': [1, 2], 'b': [3, 4]}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class TestGroupwiseApply(unittest.TestCase):
    def test_dataiter_list(self):
        iterable = Result([1, 2, 3], list)
        function = lambda itr: [x * 2 for x in itr]
        result = _apply_data(function, iterable)
        self.assertEqual(result, [2, 4, 6])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _apply_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_mixed_iterables(self):
        iterable = Result({'a': iter([1, 2]), 'b': (3, 4)}, dict)

        function = lambda itr: [x * 2 for x in itr]
        result = _apply_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [2, 4], 'b': [6, 8]})

    def test_dataiter_dict_of_ints(self):
        iterable = Result({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _apply_data(function, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 4, 'b': 6})


class TestSumData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 3], list)
        result = _sqlite_sum(iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        result = _sqlite_sum(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_sum('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = Result({'a': [1, 2], 'b': [3, 4]}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class TestCountData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result(['a', None, 3], list)
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
        iterable = Result({'a': [1, None], 'b': ['x', None, 0]}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 2})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': -5, 'b': None, 'c': 'xyz'}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 0, 'c': 1})


class TestAvgData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 3, 4], list)
        result = _sqlite_avg(iterable)
        self.assertEqual(result, 2.5)

    def test_single_integer(self):
        result = _sqlite_avg(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_avg('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = Result({
            'a': [1, 2, None],
            'b': ['xx', 1, 2, 3, None],
            'c': [None, None, None]}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1.5, 'b': 1.5, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestMinData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 3, 4], list)
        result = _sqlite_min(iterable)
        self.assertEqual(result, 1)

    def test_single_integer(self):
        result = _sqlite_min(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_min('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = Result({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 1, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestMaxData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 3, 4], list)
        result = _sqlite_max(iterable)
        self.assertEqual(result, 4)

    def test_single_integer(self):
        result = _sqlite_max(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_max('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = Result({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 3, 'b': 'xx', 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = Result({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3, 'c': None})


class TestDistinctData(unittest.TestCase):
    def test_list_iter(self):
        iterable = Result([1, 2, 1, 2, 3], list)
        result = _sqlite_distinct(iterable)
        self.assertEqual(result.fetch(), [1, 2, 3])

    def test_single_int(self):
        result = _sqlite_distinct(3)
        self.assertEqual(result, 3)

    def test_dataiter_dict_of_containers(self):
        iterable = Result({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': [1, 2], 'b': (3, 4)})

    def test_dataiter_dict_of_ints(self):
        iterable = Result({'a': 2, 'b': 3}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, Result)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.fetch(), {'a': 2, 'b': 3})


class Test_select_functions(unittest.TestCase):
    def test_normalize_columns(self):
        no_change = 'no change for valid containers'

        self.assertEqual(_normalize_columns(['A']), ['A'], msg=no_change)

        self.assertEqual(_normalize_columns(set(['A'])), set(['A']), msg=no_change)

        self.assertEqual(
            _normalize_columns([('A', 'B')]),
            [('A', 'B')],
            msg=no_change,
        )

        self.assertEqual(
            _normalize_columns({'A': ['B']}),
            {'A': ['B']},
            msg=no_change)

        self.assertEqual(
            _normalize_columns({'A': [('B', 'C')]}),
            {'A': [('B', 'C')]},
            msg=no_change)

        self.assertEqual(
            _normalize_columns({('A', 'B'): ['C']}),
            {('A', 'B'): ['C']},
            msg=no_change)

        default_list = 'unwrapped column or multi-column selects should get list wrapper'

        self.assertEqual(_normalize_columns('A'), ['A'], msg=no_change)

        self.assertEqual(
            _normalize_columns(('A', 'B')),
            [('A', 'B')],
            msg=no_change)

        self.assertEqual(
            _normalize_columns({'A': 'B'}),
            {'A': ['B']},
            msg=no_change)

        self.assertEqual(
            _normalize_columns({('A', 'B'): 'C'}),
            {('A', 'B'): ['C']},
            msg=no_change)

        self.assertEqual(
            _normalize_columns({'A': ('B', 'C')}),
            {'A': [('B', 'C')]},
            msg=no_change)

        unsupported = 'unsupported values should raise error'

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_columns(1)

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_columns({'A': {'B': ['C']}})  # Nested mapping.

        with self.assertRaises(ValueError, msg=unsupported):
            _normalize_columns(['A', ['B']])  # Nested list.

    def test_parse_columns(self):
        key, value = _parse_columns(['A'])  # Single column.
        self.assertEqual(key, tuple())
        self.assertEqual(value, ['A'])

        key, value = _parse_columns([('A', 'B')])  # Multiple colummns.
        self.assertEqual(key, tuple())
        self.assertEqual(value, [('A', 'B')])

        key, value = _parse_columns({'A': ['B']})  # Mapping.
        self.assertEqual(key, 'A')
        self.assertEqual(value, ['B'])

        key, value = _parse_columns({'A': [('B', 'C')]})  # Mapping with multi-column value.
        self.assertEqual(key, 'A')
        self.assertEqual(value, [('B', 'C')])

        key, value = _parse_columns({('A', 'B'): ['C']})  # Mapping with multi-column key.
        self.assertEqual(key, ('A', 'B'))
        self.assertEqual(value, ['C'])


class TestQuery(unittest.TestCase):
    def test_init_no_data(self):
        # Use column and where syntax.
        query = Query(['foo'], bar='baz')
        self.assertEqual(query.source, None)

        # Test query steps.
        query = Query(['foo'], bar='baz')
        self.assertEqual(query._query_steps, [])

        # Adding query steps.
        query = query.distinct().sum()
        expected = [
            ('distinct', (), {}),
            ('sum', (), {}),
        ]
        self.assertEqual(query._query_steps, expected)

        # Single-string defaults to list-of-single-string.
        query = Query('foo')
        self.assertEqual(query.args[0], ['foo'], 'should be wrapped as list')

        # Multi-item-container defaults to list-of-container.
        query = Query(['foo', 'bar'])
        self.assertEqual(query.args[0], [['foo', 'bar']], 'should be wrapped as list')

        # Mapping with single-string defaults to list-of-single-string.
        query = Query({'foo': 'bar'})
        self.assertEqual(query.args[0], {'foo': ['bar']}, 'value should be wrapped as list')

        # Mapping with multi-item-container defaults to list-of-container.
        query = Query({'foo': ['bar', 'baz']})
        self.assertEqual(query.args[0], {'foo': [['bar', 'baz']]}, 'value should be wrapped as list')

    def test_init_with_selector(self):
        source = Selector([('A', 'B'), (1, 2), (1, 2)])
        query = Query(source, ['A'], B=2)
        self.assertEqual(query.source, source)
        self.assertEqual(query.args, (['A'],))
        self.assertEqual(query.kwds, {'B': 2})
        self.assertEqual(query._query_steps, [])

        with self.assertRaises(TypeError):
            query = Query(None, ['foo'], bar='baz')

    def test_init_from_object(self):
        query1 = Query.from_object([1, 3, 4, 2])
        self.assertEqual(query1.source, [1, 3, 4, 2])
        self.assertEqual(query1.args, ())
        self.assertEqual(query1.kwds, {})
        self.assertEqual(query1._query_steps, [])

        query2 = Query.from_object({'a': 1, 'b': 2})
        self.assertEqual(query2.source, {'a': 1, 'b': 2})
        self.assertEqual(query2.args, ())
        self.assertEqual(query2.kwds, {})
        self.assertEqual(query2._query_steps, [])

        # When from_object() receives a Query, it should return
        # a copy rather than trying to use it as a data object.
        query3 = Query.from_object(query2)
        self.assertIsNot(query3, query2)
        self.assertEqual(query3.source, {'a': 1, 'b': 2})
        self.assertEqual(query3.args, ())
        self.assertEqual(query3.kwds, {})
        self.assertEqual(query3._query_steps, [])

        query4 = Query.from_object('abc')
        self.assertEqual(query4.source, ['abc'], msg=\
            'Strings or non-iterables should be wrapped as a list')
        self.assertEqual(query4.args, ())
        self.assertEqual(query4.kwds, {})
        self.assertEqual(query4._query_steps, [])

        query5 = Query.from_object(123)
        self.assertEqual(query5.source, [123], msg=\
            'Strings or non-iterables should be wrapped as a list')
        self.assertEqual(query5.args, ())
        self.assertEqual(query5.kwds, {})
        self.assertEqual(query5._query_steps, [])

    def test_init_with_invalid_args(self):
        # Missing args.
        with self.assertRaises(TypeError, msg='should require select args'):
            Query()

        # Bad "select" field.
        source = Selector([('A', 'B'), (1, 2), (1, 2)])
        with self.assertRaises(LookupError, msg='should fail immediately when fieldname conflicts with provided source'):
            query = Query(source, ['X'], B=2)

        # Bad "where" field.
        source = Selector([('A', 'B'), (1, 2), (1, 2)])
        with self.assertRaises(LookupError, msg='should fail immediately when fieldname conflicts with provided "where" field'):
            query = Query(source, ['A'], Y=2)

    def test_init_with_nested_dicts(self):
        """Support for nested dictionaries was removed (for now).
        It's likely that arbitrary nesting would complicate the ability
        to check complex data values that are, themselves, mappings
        (like probability mass functions represented as a dictionary).
        """
        regex = 'mappings can not be nested'
        with self.assertRaisesRegex(ValueError, regex):
            query = Query({'A': {'B': 'C'}}, D='x')

    def test__copy__(self):
        # Select-arg only.
        query = Query(['B'])
        copied = query.__copy__()
        self.assertIs(copied.source, query.source)
        self.assertEqual(copied.args, query.args)
        self.assertEqual(copied.kwds, query.kwds)
        self.assertEqual(copied._query_steps, query._query_steps)
        self.assertIsNot(copied.kwds, query.kwds)
        self.assertIsNot(copied._query_steps, query._query_steps)

        # Select and keyword.
        query = Query(['B'], C='x')
        copied = query.__copy__()
        self.assertIs(copied.source, query.source)
        self.assertEqual(copied.args, query.args)
        self.assertEqual(copied.kwds, query.kwds)
        self.assertEqual(copied._query_steps, query._query_steps)

        # Source, columns, and keyword.
        source = Selector([('A', 'B'), (1, 2), (1, 2)])
        query = Query(source, ['B'])
        copied = query.__copy__()
        self.assertIs(copied.source, query.source)
        self.assertEqual(copied.args, query.args)
        self.assertEqual(copied.kwds, query.kwds)
        self.assertEqual(copied._query_steps, query._query_steps)

        # Select and additional query methods.
        query = Query(['B']).map(lambda x: str(x).upper())
        copied = query.__copy__()
        self.assertIs(copied.source, query.source)
        self.assertEqual(copied.args, query.args)
        self.assertEqual(copied.kwds, query.kwds)
        self.assertEqual(copied._query_steps, query._query_steps)

    def test_fetch_datasource(self):
        select = Selector([('A', 'B'), ('1', '2'), ('1', '2')])
        query = Query(select, ['B'])
        query._query_steps = [
            ('map', (int,), {}),
            ('map', (lambda x: x * 2,), {}),
            ('sum', (), {}),
        ]
        result = query.fetch()
        self.assertEqual(result, 8)

    def test_execute_datasource(self):
        select = Selector([('A', 'B'), ('1', '2'), ('1', '2')])
        query = Query(select, ['B'])
        query._query_steps = [
            ('map', (int,), {}),
            ('map', (lambda x: x * 2,), {}),
            ('sum', (), {}),
        ]
        result = query.execute()
        self.assertEqual(result, 8)

        query = Query(['A'])
        regex = "expected 'Selector', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            query.execute(['hello', 'world'])  # <- Expects None or Query, not list!

    def test_execute_other_source(self):
        query = Query.from_object([1, 3, 4, 2])
        result = query.execute()
        self.assertIsInstance(result, Result)
        self.assertEqual(result.fetch(), [1, 3, 4, 2])

    def test_map(self):
        query1 = Query(['col2'])
        query2 = query1.map(int)
        self.assertIsNot(query1, query2, 'should return new object')

        source = Selector([('col1', 'col2'), ('a', '2'), ('b', '2')])
        result = query2.execute(source)
        self.assertEqual(result.fetch(), [2, 2])

    def test_filter(self):
        query1 = Query(['col1'])
        query2 = query1.filter(lambda x: x == 'a')
        self.assertIsNot(query1, query2, 'should return new object')

        source = Selector([('col1', 'col2'), ('a', '2'), ('b', '2')])
        result = query2.execute(source)
        self.assertEqual(result.fetch(), ['a'])

        # No filter arg should default to bool()
        source = Selector([('col1',), (1,), (2,), (0,), (3,)])
        query = Query(set(['col1'])).filter()  # <- No arg!
        result = query.execute(source)
        self.assertEqual(result.fetch(), set([1, 2, 3]))

    def test_reduce(self):
        query1 = Query(['col1'])
        query2 = query1.reduce(lambda x, y: x + y)
        self.assertIsNot(query1, query2, 'should return new object')

        source = Selector([('col1', 'col2'), ('a', '2'), ('b', '2')])
        result = query2.execute(source)
        self.assertEqual(result, 'ab')

    def test_flatten(self):
        query1 = Query({'col1': ('col2', 'col2')})
        query2 = query1.flatten()
        self.assertIsNot(query1, query2, 'should return new object')

        source = Selector([('col1', 'col2'), ('a', '2'), ('b', '2')])
        result = query2.execute(source)
        self.assertEqual(result.fetch(), [('a', '2', '2'), ('b', '2', '2')])

    def test_optimize_aggregation(self):
        """
        Unoptimized:
            Selector._select({'col1': ['values']}, col2='xyz').sum()

        Optimized:
            Selector._select_aggregate('SUM', {'col1': ['values']}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
            (_apply_to_data, (_sqlite_sum, RESULT_TOKEN,), {}),
        )
        optimized = Query._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_aggregate'), {}),
            (RESULT_TOKEN, ('SUM', {'col1': ['values']},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_distinct(self):
        """
        Unoptimized:
            Selector._select({'col1': ['values']}, col2='xyz').distinct()

        Optimized:
            Selector._select_distinct({'col1': ['values']}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
            (_sqlite_distinct, (RESULT_TOKEN,), {}),
        )
        optimized = Query._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
            (RESULT_TOKEN, ({'col1': ['values']},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_explain(self):
        query = Query(['col1'])
        expected = """
            Data Source:
              <none given> (assuming Selector object)
            Execution Plan:
              getattr, (<RESULT>, '_select'), {}
              <RESULT>, (['col1']), {}
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(query._explain(file=None), expected)

        # TODO: Add assert for query that can be optimized.

    def test_explain2(self):
        query = Query(['label1'])

        expected = """
            Data Source:
              <none given> (assuming Selector object)
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
        # Check "no selector" signature.
        query = Query(['label1'])
        regex = r"Query\(\[u?'label1'\]\)"
        self.assertRegex(repr(query), regex)

        # Check "no selector" with keyword string.
        query = Query(['label1'], label2='x')
        regex = r"Query\(\[u?'label1'\], label2='x'\)"
        self.assertRegex(repr(query), regex)

        # Check "no selector" with keyword list.
        query = Query(['label1'], label2=['x', 'y'])
        regex = r"Query\(\[u?'label1'\], label2=\[u?'x', u?'y'\]\)"
        self.assertRegex(repr(query), regex)

        # Check "selector-provided" signature.
        select = Selector([('A', 'B'), ('x', 1), ('y', 2), ('z', 3)])
        query = Query(select, ['B'])
        short_repr = super(Selector, select).__repr__()
        expected = "Query({0}, {1!r})".format(short_repr, ['B'])
        #print(repr(query))
        self.assertEqual(repr(query), expected)

        # Check "from_object" signature.
        query = Query.from_object([1, 2, 3])
        expected = "Query.from_object([1, 2, 3])"
        self.assertEqual(repr(query), expected)

        # Check query steps.
        query = Query(['label1']).distinct().count()
        regex = r"Query\(\[u?'label1'\]\).distinct\(\).count\(\)"
        self.assertRegex(repr(query), regex)

        # Check query steps with function argument.
        def upper(x):
            return str(x.upper())
        query = Query(['label1']).map(upper)
        regex = r"Query\(\[u?'label1'\]\).map\(upper\)"
        self.assertRegex(repr(query), regex)

        # Check query steps with lambda argument.
        lower = lambda x: str(x).lower()
        query = Query(['label1']).map(lower)
        regex = r"Query\(\[u?'label1'\]\).map\(<lambda>\)"
        self.assertRegex(repr(query), regex)


class TestSelector(unittest.TestCase):
    def setUp(self):
        data = [['label1', 'label2', 'value'],
                ['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = Selector(data)

    def test_empty_selector(self):
        select = Selector()

    def test_fieldnames(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.source.fieldnames, expected)

        select = Selector()  # <- Empty selector.
        self.assertEqual(select.fieldnames, [], msg='should be empty list')

    def test_load_data(self):
        select = Selector()  # <- Empty selector.
        self.assertEqual(select.fieldnames, [])

        readerlike1 = [['col1', 'col2'], ['a', 1], ['b', 2]]
        select.load_data(readerlike1)
        self.assertEqual(select.fieldnames, ['col1', 'col2'])

        readerlike2 = [['col1', 'col3'], ['c', 'x'], ['d', 'y']]
        select.load_data(readerlike2)
        self.assertEqual(select.fieldnames, ['col1', 'col2', 'col3'])

    def test_repr(self):
        data = [['A', 'B'], ['x', 100], ['y', 200]]

        # Empty selector.
        select = Selector()
        self.assertEqual(repr(select), '<Selector (no data loaded)>')

        # Data-only (no args)
        select = Selector(data)
        expected = "<Selector [['A', 'B'], ['x', 100], ['y', 200]]>"
        self.assertEqual(repr(select), expected)

        # Data with args (args don't affect repr)
        iterable = iter(data)
        select = Selector(iterable, 'foo', bar='baz')
        regex = '<Selector <[a-z_]+ object at [^\n>]+>>'
        self.assertRegex(repr(select), regex)

        # Extended after instantiation.
        select = Selector()
        select.load_data([['A', 'B'], ['z', 300]])
        select.load_data([['A', 'B'], ['y', 200]])
        select.load_data([['A', 'B'], ['x', 100]])

        expected = (
            "<Selector (3 sources):\n"
            "    [['A', 'B'], ['x', 100]]\n"
            "    [['A', 'B'], ['y', 200]]\n"
            "    [['A', 'B'], ['z', 300]]>"
        )
        self.assertEqual(repr(select), expected)

        # Test long repr truncation.
        select = Selector([
            ['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'],
            ['yyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'],
        ])

        self.assertEqual(len(repr(select)), 72)

        expected = "<Selector [['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'], ['yyyyyyyyyyy...yyyyy']]>"
        self.assertEqual(repr(select), expected)

    def test_build_where_clause(self):
        _build_where_clause = Selector._build_where_clause

        result = _build_where_clause({'A': 'x'})
        expected = ('A=?', ['x'])
        self.assertEqual(result, expected)

        result = _build_where_clause({'A': ['x', 'y']})
        expected = ('A IN (?, ?)', ['x', 'y'])
        self.assertEqual(result, expected)

        userfunc = lambda x: len(x) == 1
        result = _build_where_clause({'A': userfunc})
        expected = ('FUNC{0}(A)'.format(id(userfunc)), [])
        self.assertEqual(result, expected)

    def test_execute_query(self):
        data = [['A', 'B'], ['x', 101], ['y', 202], ['z', 303]]
        source = Selector(data)

        # Test where-clause function.
        def isodd(x):
            return x % 2 == 1
        result = source('A', B=isodd).fetch()
        self.assertEqual(result, ['x', 'z'])

        # Test replacing function.
        def iseven(x):
            return x % 2 == 0
        result = source('A', B=iseven).fetch()
        self.assertEqual(result, ['y'])

        # Test callable-but-unhashable.
        class IsEven(object):
            __hash__ = None

            def __call__(self, x):
                return x % 2 == 0

        unhashable_iseven = IsEven()
        result = source('A', B=unhashable_iseven).fetch()
        self.assertEqual(result, ['y'])

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
        result = result.fetch()
        expected = {'a': ['x', 'y', 'z'], 'b': ['z', 'y', 'x']}

        self.assertIsInstance(result, dict)

        # Sort values for SQLite versions earlier than 3.7.12
        if (3, 7, 12) > sqlite3.sqlite_version_info:
            sortvalues = lambda x: dict((k, sorted(v)) for k, v in x.items())
            result = sortvalues(result)
            expected = sortvalues(expected)
        self.assertEqual(result, expected)

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
        self.assertIsInstance(result, Result)

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
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

        query = self.source([('label1', 'label2')])
        expected = [('a', 'x'), ('a', 'x'), ('a', 'y'), ('a', 'z'),
                    ('b', 'z'), ('b', 'y'), ('b', 'x')]
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

        query = self.source([set(['label1', 'label2'])])
        expected = [set(['a', 'x']),
                    set(['a', 'x']),
                    set(['a', 'y']),
                    set(['a', 'z']),
                    set(['b', 'z']),
                    set(['b', 'y']),
                    set(['b', 'x'])]
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

        query = self.source({'label1': ['label2']})
        expected = {'a': ['x', 'x', 'y', 'z'], 'b': ['z', 'y', 'x']}
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)


class TestToCsv(unittest.TestCase):
    def test_iterable_of_rows(self):
        iterable = [['a', 1], ['b', 2]]
        csvfile = io.StringIO()

        _to_csv(iterable, csvfile)

        csvfile.seek(0)
        self.assertEqual(csvfile.readlines(), ['a,1\r\n', 'b,2\r\n'])

    def test_fieldnames(self):
        fieldnames = ['A', 'B']
        iterable = [['a', 1], ['b', 2]]
        csvfile = io.StringIO()

        _to_csv(iterable, csvfile, fieldnames)

        csvfile.seek(0)
        self.assertEqual(csvfile.readlines(), ['A,B\r\n', 'a,1\r\n', 'b,2\r\n'])

    def test_fmtparams(self):
        iterable = [['a', 1], ['b', 2]]
        csvfile = io.StringIO()

        _to_csv(iterable, csvfile, delimiter='|', lineterminator='\n')

        csvfile.seek(0)
        self.assertEqual(csvfile.readlines(), ['a|1\n', 'b|2\n'])

    def test_actual_file(self):
        try:
            tmpdir = tempfile.mkdtemp()
            path = os.path.join(tmpdir, 'tempfile.csv')

            iterable = [['a', 1], ['b', 2]]

            _to_csv(iterable, path)

            with open(path) as fh:
                self.assertEqual(fh.read(), 'a,1\nb,2\n')

        finally:
            shutil.rmtree(tmpdir)
