"""Result objects for DataSource queries."""
from . import _unittest as unittest

from datatest.compare import _coerce_other
from datatest.compare import CompareSet
from datatest.compare import CompareDict

from datatest import Extra
from datatest import Missing
from datatest import Invalid
from datatest import Deviation
from datatest import NotProperSubset
from datatest import NotProperSuperset


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

        # 'b' is missing from self/subject.
        a = CompareDict({'aaa': 1,             'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in other/reference.
        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(+2, 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is missing from other/reference.
        a = CompareDict({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = CompareDict({'aaa': 1,           'ccc': 3, 'ddd': 4}, 'foo')
        expected = [Deviation(+2, None, foo='bbb')]
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
