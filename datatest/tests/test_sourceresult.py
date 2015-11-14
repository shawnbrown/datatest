"""Result objects for DataSource queries."""
from . import _unittest as unittest

from datatest.sourceresult import _coerce_other
from datatest.sourceresult import ResultSet
from datatest.sourceresult import ResultMapping

from datatest import ExtraItem
from datatest import MissingItem
from datatest import InvalidItem
from datatest import InvalidNumber
from datatest import NotProperSubset
from datatest import NotProperSuperset


class TestMethodDecorator(unittest.TestCase):
    """Test decorator to coerce *other* for comparison magic methods."""
    def test_coerce_other(self):
        # Mock comparison method.
        def fn(self, other):
            return other
        decorator = _coerce_other(ResultSet)
        wrapped = decorator(fn)

        data = set([1, 2, 3, 4])

        other = wrapped(None, data)            # Data set.
        self.assertIsInstance(other, ResultSet)

        other = wrapped(None, list(data))      # Data list.
        self.assertIsInstance(other, ResultSet)

        other = wrapped(None, tuple(data))     # Data tuple.
        self.assertIsInstance(other, ResultSet)

        data_gen = (v for v in data)         # Data generator.
        other = wrapped(None, data_gen)
        self.assertIsInstance(other, ResultSet)

        # Data mapping (not implemented).
        other = wrapped(None, dict(enumerate(data)))
        self.assertEqual(NotImplemented, other)


class TestResultSet(unittest.TestCase):
    def test_init(self):
        data = set([1, 2, 3, 4])

        x = ResultSet(data)               # Data set.
        self.assertEqual(data, x)

        x = ResultSet(list(data))         # Data list.
        self.assertEqual(data, x)

        x = ResultSet(tuple(data))        # Data tuple.
        self.assertEqual(data, x)

        data_gen = (v for v in data)      # Data generator.
        x = ResultSet(data_gen)
        self.assertEqual(data, x)

        # Data mapping (type error).
        data_dict = dict(enumerate(data))
        with self.assertRaises(TypeError):
            x = ResultSet(data_dict)

        x = ResultSet(set())
        self.assertEqual(set(), x)

    def test_make_iter(self):
        make_set = lambda data: set(frozenset(row.items()) for row in data)

        result = ResultSet(['aaa', 'bbb', 'ccc'])
        iterable = result.make_iter('foo')
        expected = [{'foo': 'aaa'}, {'foo': 'bbb'}, {'foo': 'ccc'}]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = ResultSet(['aaa', 'bbb', 'ccc'])
        iterable = result.make_iter(['foo'])  # <- Single-item list.
        expected = [{'foo': 'aaa'}, {'foo': 'bbb'}, {'foo': 'ccc'}]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = ResultSet([
            ('aaa', 1),
            ('bbb', 2),
            ('ccc', 3)
        ])
        iterable = result.make_iter(['foo', 'bar'])
        expected = [
            {'foo': 'aaa', 'bar': 1},
            {'foo': 'bbb', 'bar': 2},
            {'foo': 'ccc', 'bar': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        result = ResultSet(['aaa', 'bbb', 'ccc'])
        with self.assertRaises(AssertionError):
            iterable = result.make_iter(['foo', 'bar'])  # Too many *names*.

        result = ResultSet([('aaa', 1), ('bbb', 2), ('ccc', 3)])
        with self.assertRaises(AssertionError):
            iterable = result.make_iter(['foo'])  # Too few *names*.

    def test_eq(self):
        data = set([1, 2, 3, 4])

        a = ResultSet(data)
        b = ResultSet(data)
        self.assertEqual(a, b)

        # Test coersion.
        a = ResultSet(data)
        b = [1, 2, 3, 4]  # <- Should be coerced into ResultSet internally.
        self.assertEqual(a, b)

    def test_ne(self):
        a = ResultSet(set([1, 2, 3]))
        b = ResultSet(set([1, 2, 3, 4]))
        self.assertTrue(a != b)

    def test_compare(self):
        a = ResultSet(['aaa','bbb','ddd'])
        b = ResultSet(['aaa','bbb','ccc'])
        expected = [ExtraItem('ddd'), MissingItem('ccc')]
        self.assertEqual(expected, a.compare(b))

        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        # Test callable other (all True).
        result = a.compare(lambda x: len(x) == 3)
        self.assertEqual([], result)

        # Test callable other (some False).
        result = a.compare(lambda x: x.startswith('b'))
        expected = set([InvalidItem('aaa'), InvalidItem('ccc')])
        self.assertEqual(expected, set(result))

        # Test subset (less-than-or-equal).
        a = ResultSet(['aaa','bbb','ddd'])
        b = ResultSet(['aaa','bbb','ccc'])
        expected = [ExtraItem('ddd')]
        self.assertEqual(expected, a.compare(b, op='<='))

        # Test strict subset (less-than).
        a = ResultSet(['aaa','bbb'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b, op='<'))

        # Test strict subset (less-than) assertion violation.
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSubset()], a.compare(b, op='<'))

        # Test superset (greater-than-or-equal).
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ddd'])
        expected = [MissingItem('ddd')]
        self.assertEqual(expected, a.compare(b, op='>='))

        # Test superset subset (greater-than).
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb'])
        self.assertEqual([], a.compare(b, op='>'))

        # Test superset subset (greater-than) assertion violation.
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSuperset()], a.compare(b, op='>'))


class TestResultMapping(unittest.TestCase):
    def test_init(self):
        data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}

        x = ResultMapping(data, 'foo')                # dict.
        self.assertEqual(data, x._data)

        x = ResultMapping(list(data.items()), 'foo')  # list of tuples.
        self.assertEqual(data, x._data)

        # Non-mapping data (data error).
        data_list = ['a', 'b', 'c', 'd']
        with self.assertRaises(ValueError):
            x = ResultMapping(data_list, 'foo')

        # Single-item wrapped in collection.
        data = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        x = ResultMapping(data, ['foo'])
        unwrapped = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.assertEqual(unwrapped, x._data)

        # IMPLEMENT THIS?
        # Mis-matched group_by and keys.
        #with self.assertRaises(ValueError):
        #    data = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        #    x = ResultMapping(data, 'foo')

    def test_make_iter(self):
        make_set = lambda data: set(frozenset(row.items()) for row in data)

        # Single-item keys, single-item values.
        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = ResultMapping(data, 'foo')
        iterable = result.make_iter('bar')
        expected = [
            {'foo': 'aaa', 'bar': 1},
            {'foo': 'bbb', 'bar': 2},
            {'foo': 'ccc', 'bar': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        # Composite keys.
        data = {('aaa', 'xxx'): 1, ('bbb', 'yyy'): 2, ('ccc', 'zzz'): 3}
        result = ResultMapping(data, ['foo', 'bar'])
        iterable = result.make_iter('baz')
        expected = [
            {'foo': 'aaa', 'bar': 'xxx', 'baz': 1},
            {'foo': 'bbb', 'bar': 'yyy', 'baz': 2},
            {'foo': 'ccc', 'bar': 'zzz', 'baz': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        # Composite values.
        data = {'aaa': ('xxx', 1), 'bbb': ('yyy', 2), 'ccc': ('zzz', 3)}
        result = ResultMapping(data, 'foo')
        iterable = result.make_iter(['bar', 'baz'])
        expected = [
            {'foo': 'aaa', 'bar': 'xxx', 'baz': 1},
            {'foo': 'bbb', 'bar': 'yyy', 'baz': 2},
            {'foo': 'ccc', 'bar': 'zzz', 'baz': 3},
        ]
        self.assertEqual(make_set(expected), make_set(iterable))

        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = ResultMapping(data, 'foo')
        with self.assertRaises(AssertionError):
            iterable = result.make_iter(['bar', 'baz'])  # Too many *names*.

        data = {'aaa': (1, 2, 3), 'bbb': (2, 4, 6), 'ccc': (3, 6, 9)}
        result = ResultMapping(data, 'foo')
        with self.assertRaises(AssertionError):
            iterable = result.make_iter('bar')  # Too few *names*.

        data = {'aaa': 1, 'bbb': 2, 'ccc': 3}
        result = ResultMapping(data, 'foo')
        with self.assertRaises(ValueError):
            iterable = result.make_iter('foo')  # 'foo' conflicts with group_by.

    def test_eq(self):
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(data1, 'foo')
        b = ResultMapping(data1, 'foo')
        self.assertTrue(a == b)

        data2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = ResultMapping(data1, 'foo')
        b = ResultMapping(data2, 'foo')
        self.assertFalse(a == b)

        # Test coersion of mapping.
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(data1, 'foo')
        self.assertTrue(a == {'a': 1, 'b': 2, 'c': 3, 'd': 4})

        # Test coersion of list of tuples.
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        data2 = [('a', 1),  # <- Should be coerced
                   ('b', 2),  #    into ResultMapping
                   ('c', 3),  #    internally.
                   ('d', 4)]
        a = ResultMapping(data1, 'foo')
        b = data2
        self.assertTrue(a == b)

    def test_ne(self):
        data1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(data1, 'foo')
        b = ResultMapping(data1, 'foo')
        self.assertFalse(a != b)

        data2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = ResultMapping(data1, 'foo')
        b = ResultMapping(data2, 'foo')
        self.assertTrue(a != b)

    def test_compare_numbers(self):
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in self/subject.
        a = ResultMapping({'aaa': 1, 'bbb':   0, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is missing from self/subject.
        a = ResultMapping({'aaa': 1,             'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in other/reference.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(+2, 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is missing from other/reference.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1,           'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(+2, None, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # Test coersion of *other*.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = {'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}
        expected = [InvalidNumber(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_strings(self):
        a = ResultMapping({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')
        b = ResultMapping({'aaa': 'x', 'bbb': 'z', 'ccc': 'z'}, 'foo')
        expected = [InvalidItem('y', 'z', foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_function(self):
        a = ResultMapping({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')

        # All True.
        result = a.compare(lambda x: len(x) == 1)
        self.assertEqual([], result)

        # Some False.
        result = a.compare(lambda a: a in ('x', 'y'))
        expected = [InvalidItem('z', foo='ccc')]
        self.assertEqual(expected, result)

    def test_compare_mixed_types(self):
        a = ResultMapping({'aaa':  2,  'bbb': 3,   'ccc': 'z'}, 'foo')
        b = ResultMapping({'aaa': 'y', 'bbb': 4.0, 'ccc':  5 }, 'foo')
        expected = set([
            InvalidItem(2, 'y', foo='aaa'),
            InvalidNumber(-1, 4, foo='bbb'),
            InvalidItem('z', 5, foo='ccc'),
        ])
        self.assertEqual(expected, set(a.compare(b)))


if __name__ == '__main__':
    unittest.main()
