"""Result objects for DataSource queries."""
import re
from . import _unittest as unittest

from datatest.compare import _coerce_other
from datatest.compare import CompareSet
from datatest.compare import CompareDict
from datatest.compare import _compare_other
from datatest.compare import _compare_set
from datatest.compare import _compare_mapping
from datatest.compare import _compare_sequence

from datatest import Extra
from datatest import Missing
from datatest import Invalid
from datatest import Deviation
from datatest import NotProperSubset
from datatest import NotProperSuperset


# Comparison functions should impelement the following types of
# object comparisons:
#
#   +--------------------------------------------------------------+
#   |             OBJECT COMPARISONS AND RETURN VALUES             |
#   +-------------------+------------------------------------------+
#   |                   |              *requirement*               |
#   | *data under test* +------+---------+----------+--------------+
#   |                   | set  | mapping | sequence | str or other |
#   +===================+======+=========+==========+==============+
#   | **set**           | list |         |          | list         |
#   +-------------------+------+---------+----------+--------------+
#   | **mapping**       | list | dict    |          | dict         |
#   +-------------------+------+---------+----------+--------------+
#   | **sequence**      | list |         | dict     | dict         |
#   +-------------------+------+---------+----------+--------------+
#   | **iterable**      | list |         |          | list         |
#   +-------------------+------+---------+----------+--------------+
#   | **str or other**  |      |         |          | list         |
#   +-------------------+------+---------+----------+--------------+


class Test_compare_sequence(unittest.TestCase):
    def test_sequence(self):
        required = ['a', 'b', 'c']

        data = ['a', 'b', 'c']
        result = _compare_sequence(data, required)
        self.assertEqual(result, {})

        data = ['a', 'b', 'c', 'd']
        result = _compare_sequence(data, required)
        self.assertEqual(result, {3: Extra('d')})

        data = ['a', 'b']
        result = _compare_sequence(data, required)
        self.assertEqual(result, {2: Missing('c')})

        data = ['a', 'x', 'c', 'y']
        result = _compare_sequence(data, required)
        self.assertEqual(result, {1: Invalid('x', 'b'), 3: Extra('y')})

    def test_other(self):
        required = ['a', 'b', 'c']

        with self.assertRaises(ValueError):
            data = set(['a', 'b', 'c'])  # Set.
            _compare_sequence(data, required)

        with self.assertRaises(ValueError):
            data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}  # Mapping.
            _compare_sequence(data, required)

        with self.assertRaises(ValueError):
            data = iter(['a', 'b', 'c'])  # Iterable.
            _compare_sequence(data, required)

        with self.assertRaises(ValueError):
            _compare_sequence('abc', required)  # String.

        with self.assertRaises(ValueError):
            _compare_sequence(123, required)  # Integer.

        with self.assertRaises(ValueError):
            _compare_sequence(object(), required)  # Object.


class Test_compare_mapping(unittest.TestCase):
    def test_mapping(self):
        required = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
        result = _compare_mapping(data, required)
        self.assertEqual(result, {})

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c', 'DDD': '3'}
        result = _compare_mapping(data, required)
        self.assertEqual(result, {'DDD': Extra('3')})

        data = {'AAA': 'a', 'CCC': 'c', 'DDD': '3'}
        result = _compare_mapping(data, required)
        self.assertEqual(result, {'BBB': Missing('b'), 'DDD': Extra('3')})

    def test_other(self):
        required = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}

        with self.assertRaises(ValueError):
            _compare_mapping(123, required)

        with self.assertRaises(ValueError):
            _compare_mapping(object(), required)

        with self.assertRaises(ValueError):
            _compare_mapping('abc', required)


class Test_compare_set(unittest.TestCase):
    def test_set(self):
        required = set(['a', 'b', 'c'])

        data = set(['a', 'b', 'c'])
        result = _compare_set(data, required)
        self.assertEqual(result, [])

        data = set(['a', 'b', 'c', '3'])
        result = _compare_set(data, required)
        self.assertEqual(result, [Extra('3')])

        data = set(['a', 'c', '3'])
        result = _compare_set(data, required)
        result = set(result)
        self.assertEqual(result, set([Missing('b'), Extra('3')]))

    def test_mapping(self):
        required = set(['a', 'b', 'c'])

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
        result = _compare_set(data, required)
        self.assertEqual(result, [])

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c', 'DDD': '3'}
        result = _compare_set(data, required)
        self.assertEqual(result, [Extra('3')])

        data = {'AAA': 'a', 'CCC': 'c', 'DDD': '3'}
        result = _compare_set(data, required)
        result = set(result)
        self.assertEqual(result, set([Missing('b'), Extra('3')]))

    def test_sequence(self):
        required = set(['a', 'b', 'c'])

        data = ['a', 'b', 'c']
        result = _compare_set(data, required)
        self.assertEqual(result, [])

        data = ['a', 'b', 'c', '3']
        result = _compare_set(data, required)
        self.assertEqual(result, [Extra('3')])

        data = ['a', 'c', '3']
        result = _compare_set(data, required)
        result = set(result)
        self.assertEqual(result, set([Missing('b'), Extra('3')]))

    def test_iterable(self):
        required = set(['a', 'b', 'c'])

        data = iter(['a', 'b', 'c'])
        result = _compare_set(data, required)
        self.assertEqual(result, [])

        data = iter(['a', 'b', 'c', '3'])
        result = _compare_set(data, required)
        self.assertEqual(result, [Extra('3')])

        data = iter(['a', 'c', '3'])
        result = _compare_set(data, required)
        result = set(result)
        self.assertEqual(result, set([Missing('b'), Extra('3')]))

    def test_str_other(self):
        required = set(['a', 'b', 'c'])

        with self.assertRaises(TypeError):
            _compare_set('abc', required)

        with self.assertRaises(TypeError):
            _compare_set(123, required)

        with self.assertRaises(TypeError):
            _compare_set(object(), required)


class Test_compare_other(unittest.TestCase):
    def test_set(self):
        isalpha = lambda x: x.isalpha()

        data = set(['a', 'b', 'c'])
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [])

        data = set(['a', 'b', 'c', '3'])
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [Invalid('3', isalpha)])

    def test_mapping(self):
        isalpha = lambda x: x.isalpha()

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
        result = _compare_other(data, isalpha)
        self.assertEqual(result, {})

        data = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c', 'DDD': '3'}
        result = _compare_other(data, isalpha)
        self.assertEqual(result, {'DDD': Invalid('3', isalpha)})

    def test_sequence(self):
        isalpha = lambda x: x.isalpha()

        data = ['a', 'b', 'c']
        result = _compare_other(data, isalpha)
        self.assertEqual(result, {})

        data = ['a', 'b', 'c', '9']
        result = _compare_other(data, isalpha)
        self.assertEqual(result, {3: Invalid('9', isalpha)})

    def test_iterable(self):
        isalpha = lambda x: x.isalpha()

        data = iter(['a', 'b', 'c'])
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [])

        data = iter(['a', 'b', 'c', '9'])
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [Invalid('9', isalpha)])

    def test_str_or_noniterable(self):
        isalpha = lambda x: x.isalpha()

        data = 'ABCD'
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [])

        data = '!@#$'
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [Invalid('!@#$', isalpha)])

        data = 5
        required = lambda x: 10 < x
        result = _compare_other(data, required)
        self.assertEqual(result, [Invalid(5, required)])

    def test_multiargument_callable(self):
        """Should unpack arguments if callable expects multiple
        parameters.
        """
        data = set([(5, 2), (1, 4), (10, 8)])

        required = lambda x, y: x > y  # <- Multiple positional parameters.
        result = _compare_other(data, required)
        self.assertEqual(result, [Invalid((1, 4), required)])

        required = lambda *z: z[0] > z[1]  # <- Variable parameters.
        result = _compare_other(data, required)
        self.assertEqual(result, [Invalid((1, 4), required)])

        required = lambda a: a[0] > a[1]  # <- Single parameter.
        result = _compare_other(data, required)
        self.assertEqual(result, [Invalid((1, 4), required)])

        data = [[], [], []]
        required = lambda x, y: x > y  # <- Multiple positional params.
        with self.assertRaisesRegex(TypeError, 'missing 2|0 given'):
            _compare_other(data, required)

        data = (5, 2)
        required = lambda x, y: x > y  # <- Multiple positional params.
        with self.assertRaisesRegex(TypeError, 'missing 1|1 given'):
            _compare_other(data, required)

        data = set([(5, 2), (1, 4), (10, 8)])  # Args and params match
        def required(x, y):                    # but function raises
            raise TypeError('other error')     # some other TypeError.
        with self.assertRaisesRegex(TypeError, 'other error'):
            _compare_other(data, required)

    def test_error_condition(self):
        """If callable raises an Exception, the result is counted as
        False.
        """
        isalpha = lambda x: x.isalpha()  # Raises TypeError if given
                                         # a non-string value.

        data = set(['a', 'b', 3, '4'])  # <- Value 3 raises an error.
        result = _compare_other(data, isalpha)
        expected = [Invalid(3, isalpha), Invalid('4', isalpha)]
        self.assertEqual(set(result), set(expected))

        data = 10
        result = _compare_other(data, isalpha)
        self.assertEqual(result, [Invalid(data, isalpha)])

    def test_required_regex(self):
        data = set(['a1', 'b2', 'c3', 'd', 'e5'])
        regex = re.compile('[a-z][0-9]+')
        result = _compare_other(data, regex)
        self.assertEqual(result, [Invalid('d', regex)])

    def test_required_string(self):
        data = set(['AAA', 'BBB'])
        string_val = 'AAA'
        result = _compare_other(data, string_val)
        self.assertEqual(result, [Invalid('BBB', string_val)])

    def test_required_integer(self):
        data = set([11, 8])
        integer_val = 11
        result = _compare_other(data, integer_val)
        self.assertEqual(result, [Deviation(-3, integer_val)])

        data = {'foo': 11, 'bar': 8}
        integer_val = 11
        result = _compare_other(data, integer_val)
        self.assertEqual(result, {'bar': Deviation(-3, integer_val)})


class TestMethodDecorator(unittest.TestCase):
    """Test decorator to coerce *other* for comparison magic methods."""
    def test_coerce_other(self):
        # Mock comparison method.
        def fn(self, other):
            return other
        decorator = _coerce_other(CompareSet)
        wrapped = decorator(fn)

        data = set([1, 2, 3, 4])

        other = wrapped(None, data)            # Data set.
        self.assertIsInstance(other, CompareSet)

        other = wrapped(None, list(data))      # Data list.
        self.assertIsInstance(other, CompareSet)

        other = wrapped(None, tuple(data))     # Data tuple.
        self.assertIsInstance(other, CompareSet)

        data_gen = (v for v in data)         # Data generator.
        other = wrapped(None, data_gen)
        self.assertIsInstance(other, CompareSet)

        # Data mapping (not implemented).
        other = wrapped(None, dict(enumerate(data)))
        self.assertEqual(NotImplemented, other)


class TestCompareSet(unittest.TestCase):
    def test_init(self):
        data = set([1, 2, 3, 4])

        x = CompareSet(data)               # Data set.
        self.assertEqual(data, x)

        x = CompareSet(list(data))         # Data list.
        self.assertEqual(data, x)

        x = CompareSet(tuple(data))        # Data tuple.
        self.assertEqual(data, x)

        data_gen = (v for v in data)      # Data generator.
        x = CompareSet(data_gen)
        self.assertEqual(data, x)

        # Data mapping (type error).
        data_dict = dict(enumerate(data))
        with self.assertRaises(TypeError):
            x = CompareSet(data_dict)

        x = CompareSet(set())
        self.assertEqual(set(), x)

    def test_repr(self):
        result = CompareSet(set([1]))
        regex = r'^CompareSet\([\[\{]1[\}\]]\)$'
        self.assertRegex(repr(result), regex)

    def test_make_rows(self):
        make_set = lambda data: set(frozenset(row.items()) for row in data)

        result = CompareSet(['aaa', 'bbb', 'ccc'])
        iterable = result.make_rows('foo')
        expected = [{'foo': 'aaa'}, {'foo': 'bbb'}, {'foo': 'ccc'}]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = CompareSet(['aaa', 'bbb', 'ccc'])
        iterable = result.make_rows(['foo'])  # <- Single-item list.
        expected = [{'foo': 'aaa'}, {'foo': 'bbb'}, {'foo': 'ccc'}]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = CompareSet([
            ('aaa', 1),
            ('bbb', 2),
            ('ccc', 3)
        ])
        iterable = result.make_rows(['foo', 'bar'])
        expected = [
            {'foo': 'aaa', 'bar': 1},
            {'foo': 'bbb', 'bar': 2},
            {'foo': 'ccc', 'bar': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = CompareSet(['aaa', 'bbb', 'ccc'])
        with self.assertRaises(AssertionError):
            iterable = result.make_rows(['foo', 'bar'])  # Too many *names*.

        result = CompareSet([('aaa', 1), ('bbb', 2), ('ccc', 3)])
        with self.assertRaises(AssertionError):
            iterable = result.make_rows(['foo'])  # Too few *names*.

    def test_eq(self):
        data = set([1, 2, 3, 4])

        a = CompareSet(data)
        b = CompareSet(data)
        self.assertEqual(a, b)

        # Test coersion.
        a = CompareSet(data)
        b = [1, 2, 3, 4]  # <- Should be coerced into CompareSet internally.
        self.assertEqual(a, b)

        # Test non-comparable types.
        a = CompareSet(data)
        self.assertNotEqual(a, None)
        self.assertNotEqual(a, False)
        self.assertNotEqual(a, 0)

    def test_ne(self):
        a = CompareSet(set([1, 2, 3]))
        b = CompareSet(set([1, 2, 3, 4]))
        self.assertTrue(a != b)

    def test_compare(self):
        a = CompareSet(['aaa','bbb','ddd'])
        b = CompareSet(['aaa','bbb','ccc'])
        expected = [Extra('ddd'), Missing('ccc')]
        self.assertEqual(expected, a.compare(b))

        a = CompareSet(['aaa','bbb','ccc'])
        b = CompareSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        # Test callable other (all True).
        result = a.compare(lambda x: len(x) == 3)
        self.assertEqual([], result)

        # Test callable other (some False).
        result = a.compare(lambda x: x.startswith('b'))
        expected = set([Invalid('aaa'), Invalid('ccc')])
        self.assertEqual(expected, set(result))

        # Test callable other, multiple arguments (all True).
        a = CompareSet([(1, 1), (1, 2), (2, 1), (2, 2)])
        result = a.compare(lambda x, y: x + y > 0)
        self.assertEqual([], result)

        # Test callable other, using single vararg (all True).
        a = CompareSet([(1, 1), (1, 2), (2, 1), (2, 2)])
        result = a.compare(lambda *x: x[0] + x[1] > 0)
        self.assertEqual([], result)

        # Test callable other, multiple arguments (some False).
        a = CompareSet([(1, 1), (1, 2), (2, 1), (2, 2)])
        result = a.compare(lambda x, y: x != y)
        expected = set([Invalid((1, 1)), Invalid((2, 2))])
        self.assertEqual(expected, set(result))

        # Test subset (less-than-or-equal).
        a = CompareSet(['aaa','bbb','ddd'])
        b = CompareSet(['aaa','bbb','ccc'])
        expected = [Extra('ddd')]
        self.assertEqual(expected, a.compare(b, op='<='))

        # Test strict subset (less-than).
        a = CompareSet(['aaa','bbb'])
        b = CompareSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b, op='<'))

        # Test strict subset (less-than) assertion violation.
        a = CompareSet(['aaa','bbb','ccc'])
        b = CompareSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSubset()], a.compare(b, op='<'))

        # Test superset (greater-than-or-equal).
        a = CompareSet(['aaa','bbb','ccc'])
        b = CompareSet(['aaa','bbb','ddd'])
        expected = [Missing('ddd')]
        self.assertEqual(expected, a.compare(b, op='>='))

        # Test superset subset (greater-than).
        a = CompareSet(['aaa','bbb','ccc'])
        b = CompareSet(['aaa','bbb'])
        self.assertEqual([], a.compare(b, op='>'))

        # Test superset subset (greater-than) assertion violation.
        a = CompareSet(['aaa','bbb','ccc'])
        b = CompareSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSuperset()], a.compare(b, op='>'))

    def test_all_fn(self):
        obj = CompareSet(['aaa','bbb','ddd'])
        key = lambda x: len(x) == 3
        self.assertTrue(obj.all(key))

        obj = CompareSet(['aaa1','aaa2','bbb1'])
        key = lambda x: str(x).startswith('aaa')
        self.assertFalse(obj.all(key))


class TestCompareDict(unittest.TestCase):
    def test_init(self):
        data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}

        x = CompareDict(data, 'foo')                # dict.
        self.assertEqual(data, x)

        x = CompareDict(list(data.items()), 'foo')  # list of tuples.
        self.assertEqual(data, x)

        # Non-mapping data (data error).
        data_list = ['a', 'b', 'c', 'd']
        with self.assertRaises(ValueError):
            x = CompareDict(data_list, 'foo')

        # Single-item wrapped in collection.
        data = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        x = CompareDict(data, ['foo'])
        unwrapped = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.assertEqual(unwrapped, x)

        # Omitted *key_names*.
        data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        x = CompareDict(data)
        self.assertEqual(data, x)
        self.assertEqual(x.key_names, ('_0',))

        data = {('a', 'a'): 1, ('b', 'b'): 2, ('c', 'c'): 3}
        x = CompareDict(data)
        self.assertEqual(data, x)
        self.assertEqual(x.key_names, ('_0', '_1'))

        # IMPLEMENT THIS?
        # Mis-matched group_by and keys.
        #with self.assertRaises(ValueError):
        #    data = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        #    x = CompareDict(data, 'foo')

    def test_repr(self):
        expected = "CompareDict({'a': 1}, key_names='foo')"
        result = CompareDict({'a': 1}, 'foo')
        self.assertEqual(expected, repr(result))

        result = CompareDict({('a',): 1}, ['foo'])  # <- Single-item containers.
        self.assertEqual(expected, repr(result))  # Same "expected" as above.

        expected = "CompareDict({('a', 'b'): 1}, key_names=['foo', 'bar'])"
        result = CompareDict({('a', 'b'): 1}, ['foo', 'bar'])
        self.assertEqual(expected, repr(result))

    def test_make_rows(self):
        make_set = lambda data: set(frozenset(row.items()) for row in data)

        # Single-item keys, single-item values.
        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = CompareDict(data, 'foo')
        iterable = result.make_rows('bar')
        expected = [
            {'foo': 'aaa', 'bar': 1},
            {'foo': 'bbb', 'bar': 2},
            {'foo': 'ccc', 'bar': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        # Composite keys.
        data = {('aaa', 'xxx'): 1, ('bbb', 'yyy'): 2, ('ccc', 'zzz'): 3}
        result = CompareDict(data, ['foo', 'bar'])
        iterable = result.make_rows('baz')
        expected = [
            {'foo': 'aaa', 'bar': 'xxx', 'baz': 1},
            {'foo': 'bbb', 'bar': 'yyy', 'baz': 2},
            {'foo': 'ccc', 'bar': 'zzz', 'baz': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        # Composite values.
        data = {'aaa': ('xxx', 1), 'bbb': ('yyy', 2), 'ccc': ('zzz', 3)}
        result = CompareDict(data, 'foo')
        iterable = result.make_rows(['bar', 'baz'])
        expected = [
            {'foo': 'aaa', 'bar': 'xxx', 'baz': 1},
            {'foo': 'bbb', 'bar': 'yyy', 'baz': 2},
            {'foo': 'ccc', 'bar': 'zzz', 'baz': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = CompareDict(data, 'foo')
        with self.assertRaises(AssertionError):
            iterable = result.make_rows(['bar', 'baz'])  # Too many *names*.

        data = {'aaa': (1, 2, 3), 'bbb': (2, 4, 6), 'ccc': (3, 6, 9)}
        result = CompareDict(data, 'foo')
        with self.assertRaises(AssertionError):
            iterable = result.make_rows('bar')  # Too few *names*.

        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = CompareDict(data, 'foo')
        with self.assertRaises(ValueError):
            iterable = result.make_rows('foo')  # 'foo' conflicts with group_by.

    def test_eq(self):
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = CompareDict(data1, 'foo')
        b = CompareDict(data1, 'foo')
        self.assertTrue(a == b)

        data2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = CompareDict(data1, 'foo')
        b = CompareDict(data2, 'foo')
        self.assertFalse(a == b)

        # Test coersion of mapping.
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = CompareDict(data1, 'foo')
        self.assertTrue(a == {'a': 1, 'b': 2, 'c': 3, 'd': 4})

        # Test coersion of list of tuples.
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        data2 = [('a', 1),  # <- Should be coerced
                 ('b', 2),  #    into CompareDict
                 ('c', 3),  #    internally.
                 ('d', 4)]
        a = CompareDict(data1, 'foo')
        b = data2
        self.assertTrue(a == b)

    def test_ne(self):
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = CompareDict(data1, 'foo')
        b = CompareDict(data1, 'foo')
        self.assertFalse(a != b)

        data2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = CompareDict(data1, 'foo')
        b = CompareDict(data2, 'foo')
        self.assertTrue(a != b)

    def test_compare_numbers(self):
        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in self/subject.
        a = CompareDict({'aaa': 1, 'bbb':   0, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'bbb' is zero in other/reference.
        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(+2, 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'bbb' is missing from self/subject.
        a = CompareDict({'aaa': 1,             'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(-2.5, 2.5, foo='bbb')]  # <- QUESTION: This
        self.assertEqual(expected, a.compare(b))      #    deviation looks the
                                                      #    same as 0 vs 2.5.
                                                      #    Is this OK?

        # 'bbb' is missing from a/subject.
        a = CompareDict({'aaa': 1,           'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(None, 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'bbb' is empty string in a/subject.
        a = CompareDict({'aaa': 1, 'bbb': '', 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb':  0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation('', 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'bbb' is missing from b/reference.
        a = CompareDict({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1,           'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(0, None, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # Test coersion of *other*.
        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = {'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}
        expected = [Deviation(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_strings(self):
        a = CompareDict({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')
        b = CompareDict({'aaa': 'x', 'bbb': 'z', 'ccc': 'z'}, 'foo')
        expected = [Invalid('y', 'z', foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_function(self):
        a = CompareDict({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')

        # All True.
        result = a.compare(lambda x: len(x) == 1)
        self.assertEqual([], result)

        # Some False.
        result = a.compare(lambda a: a in ('x', 'y'))
        expected = [Invalid('z', foo='ccc')]
        self.assertEqual(expected, result)

        # All True, multiple args.
        a = CompareDict({'aaa': (1, 2), 'bbb': (1, 3), 'ccc': (4, 8)}, 'foo')
        result = a.compare(lambda x, y: x < y)
        self.assertEqual([], result)

        # Some False, multiple args.
        a = CompareDict({'aaa': (1, 0), 'bbb': (1, 3), 'ccc': (3, 2)}, 'foo')
        result = a.compare(lambda x, y: x < y)
        expected = [Invalid((1, 0), foo='aaa'), Invalid((3, 2), foo='ccc')]
        self.assertEqual(expected, result)

    def test_compare_mixed_types(self):
        a = CompareDict({'aaa':  2,  'bbb': 3,   'ccc': 'z'}, 'foo')
        b = CompareDict({'aaa': 'y', 'bbb': 4.0, 'ccc':  5 }, 'foo')
        expected = set([
            Invalid(2, 'y', foo='aaa'),
            Deviation(-1, 4, foo='bbb'),
            Invalid('z', 5, foo='ccc'),
        ])
        self.assertEqual(expected, set(a.compare(b)))

    def test_all_fn(self):
        # All True, single arg key function..
        compare_obj = CompareDict({'aaa': (1, 2), 'bbb': (1, 3), 'ccc': (4, 8)}, 'foo')
        result = compare_obj.all(lambda x: x[0] < x[1])
        self.assertTrue(result)

        # Some False, single arg key function..
        compare_obj = CompareDict({'aaa': (1, 2), 'bbb': (5, 3), 'ccc': (4, 8)}, 'foo')
        result = compare_obj.all(lambda x: x[0] < x[1])
        self.assertFalse(result)

        # All True, multi-arg key function.
        compare_obj = CompareDict({'aaa': (1, 2), 'bbb': (1, 3), 'ccc': (4, 8)}, 'foo')
        result = compare_obj.all(lambda x, y: x < y)
        self.assertTrue(result)

        # Some False,multi-arg key function.
        compare_obj = CompareDict({'aaa': (1, 2), 'bbb': (5, 3), 'ccc': (4, 8)}, 'foo')
        result = compare_obj.all(lambda x, y: x < y)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
