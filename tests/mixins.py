# -*- coding: utf-8 -*-
"""Mixin test cases common to all data source classes."""

from datatest import CompareSet
from datatest import ExcelSource


class CountTests(object):
    """Test count() method with the following data set:

        label1  label2  value
        ------  ------  -----
        'a'     'x'     '17'
        'a'     'x'     '13'
        'a'     'y'     '20'
        'a'     ''      '15'
        'b'     'z'     '5'
        'b'     'y'     '40'
        'b'     'x'     '25'
        'b'     None    '0'
        'b'     ''      '1'
    """
    fieldnames = ['label1', 'label2', 'value']
    testdata = [
        ['a', 'x', '17'],
        ['a', 'x', '13'],
        ['a', 'y', '20'],
        ['a', '',  '15'],
        ['b', 'z', '5' ],
        ['b', 'y', '40'],
        ['b', 'x', '25'],
        ['b', None, '0'],
        ['b', '', '1'],
    ]

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(9, count('label1'))

        expected = {'a': 4, 'b': 5}
        result = count('label1', ['label1'])
        self.assertEqual(expected, result)

        expected = {'a': 3, 'b': 3}  # Counts only truthy values (not '' or None).
        result = count('label2', ['label1'])
        self.assertEqual(expected, result)

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', ''): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
            ('b', None): 1,
            ('b', ''): 1,
        }
        result = count('label1', ['label1', 'label2'])
        self.assertEqual(expected, result)

        expected = {'x': 2, 'y': 1, '': 1}
        result = count('label1', 'label2', label1='a')
        self.assertEqual(expected, result)


class OtherTests(object):
    fieldnames = ['label1', 'label2', 'value']
    testdata = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]

    @staticmethod
    def _value_to_str(result):
        # TODO: REMOVE IN THE FUTURE AND CLEAN UP THESE TESTS!
        new_result = []
        for dic in result:
            value = dic['value']
            if isinstance(value, (int, float)):
                value = str(value)
                if value.endswith('.0'):
                    value = value[:-2]
                dic['value'] = value
            new_result.append(dic)
        return new_result

    def test_for_datasource(self):
        msg = '{0} missing `datasource` attribute.'
        msg = msg.format(self.__class__.__name__)
        self.assertTrue(hasattr(self, 'datasource'), msg)

    def test_iter(self):
        """Test __iter__."""
        result = [row for row in self.datasource]
        if isinstance(self.datasource, ExcelSource):
            result = self._value_to_str(result)

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

    def test_filter_rows(self):
        """Test filter iterator."""
        # Filter by single value (where label1 is 'a').
        results = self.datasource.filter_rows(label1='a')
        results = list(results)
        if isinstance(self.datasource, ExcelSource):
            results = self._value_to_str(results)

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(expected, results)

        # Filter by multiple values (where label2 is 'x' OR 'y').
        results = self.datasource.filter_rows(label2=['x', 'y'])
        results = list(results)
        if isinstance(self.datasource, ExcelSource):
            results = self._value_to_str(results)

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, results)

        # Filter by multiple columns (where label1 is 'a', label2 is 'x' OR 'y').
        results = self.datasource.filter_rows(label1='a', label2=['x', 'y'])
        results = list(results)
        if isinstance(self.datasource, ExcelSource):
            results = self._value_to_str(results)

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
        ]
        self.assertEqual(expected, results)

        # Call with no filter kewords at all.
        results = self.datasource.filter_rows()  # <- Should return all rows.
        results = list(results)
        if isinstance(self.datasource, ExcelSource):
            results = self._value_to_str(results)

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, results)

    def test_columns(self):
        header = self.datasource.columns()
        self.assertEqual(header, ['label1', 'label2', 'value'])

    def test_mapreduce(self):
        mapreduce = self.datasource.mapreduce

        # No keys, single *columns* value.
        self.assertEqual(40, mapreduce(int, max, 'value'))

        # No keys, multiple *columns*.
        mapper = lambda a: (a[0], int(a[1]))
        reducer = lambda x, y: (min(x[0], y[0]), max(x[1], y[1]))
        #tup = namedtuple('tup', ['label1', 'value'])
        #mapper = lambda a: tup(a.label1, int(a.value))
        #reducer = lambda x, y: tup(min(x.label1, y.label1), max(x.value, y.value))
        expected = ('a', 40)
        self.assertEqual(expected, mapreduce(mapper, reducer, ['label1', 'value']))

        # No keys, missing column.
        with self.assertRaises(TypeError):
            self.assertEqual(None, mapreduce(int, max))

        # Single group_by column.
        expected = {'a': 20, 'b': 40}
        self.assertEqual(expected, mapreduce(int, max, 'value', 'label1'))
        self.assertEqual(expected, mapreduce(int, max, 'value', ['label1']))  # 1-item container

        # Two group_by columns.
        expected = {
            ('a', 'x'): 17,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'z'):  5,
            ('b', 'y'): 40,
            ('b', 'x'): 25,
        }
        self.assertEqual(expected, mapreduce(int, max, 'value', ['label1', 'label2']))

        # Group by with filter.
        expected = {'x': 17, 'y': 20, 'z': 15}
        self.assertEqual(expected, mapreduce(int, max, 'value', 'label2', label1='a'))

        # Attempt to reduce column that does not exist.
        with self.assertRaises(LookupError):
            result = mapreduce(int, max, 'value_x')

        # Tuple argument for mapper.
        mapper = lambda a: (int(a[0]), str(a[1]))
        maxmin = lambda x, y: (min(x[0], y[0]), max(x[1], y[1]))
        expected = {'a': (13, 'z'), 'b': (5, 'z')}
        self.assertEqual(expected, mapreduce(mapper, maxmin, ['value', 'label2'], 'label1'))

        # Namedtuple argument for mapper.
        #mapper = lambda a: (int(a.value), a.label2)  # <- Using namedtuples.
        #maxmin = lambda x, y: (max(x[0], y[0]), min(x[1], y[1]))
        #expected = {'a': (20, 'x'), 'b': (40, 'x')}
        #self.assertEqual(expected, mapreduce(mapper, maxmin, ['value', 'label2'], 'label1'))

        # Tuple argument for reducer.
        maketwo = lambda x: (int(x), int(x))
        maxmin = lambda x, y: (max(x[0], y[0]), min(x[1], y[1]))
        expected = {'a': (20, 13), 'b': (40, 5)}
        self.assertEqual(expected, mapreduce(maketwo, maxmin, 'value', 'label1'))

    def test_sum(self):
        sum = self.datasource.sum

        self.assertEqual(135, sum('value'))

        expected = {'a': 65, 'b': 70}
        self.assertEqual(expected, sum('value', 'label1'))

        expected = {('a',): 65, ('b',): 70}
        self.assertEqual(expected, sum('value', ['label1']))

        expected = {
            ('a', 'x'): 30,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'z'): 5,
            ('b', 'y'): 40,
            ('b', 'x'): 25,
        }
        self.assertEqual(expected, sum('value', ['label1', 'label2']))

        expected = {'x': 30, 'y': 20, 'z': 15}
        self.assertEqual(expected, sum('value', 'label2', label1='a'))

        # Test multiple/non-string column (not valid).
        with self.assertRaises((TypeError, ValueError)):
            sum(['value', 'value'])

        with self.assertRaises((TypeError, ValueError)):
            sum(['value', 'value'], 'label2', label1='a')

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(7, count('label1'))

        expected = {'a': 4, 'b': 3}
        self.assertEqual(expected, count('label1', 'label1'))

        expected = {('a',): 4, ('b',): 3}
        self.assertEqual(expected, count('label1', ['label1']))

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', 'z'): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
        }
        self.assertEqual(expected, count('label1', ['label1', 'label2']))
        expected = {'x': 2, 'y': 1, 'z': 1}
        self.assertEqual(expected, count('label2', 'label2', label1='a'))

    def test_distinct(self):
        distinct = self.datasource.distinct

        # Test single column.
        expected = ['a', 'b']
        self.assertEqual(expected, distinct('label1'))
        self.assertEqual(expected, distinct(['label1']))

        # Test single column wrapped in iterable (list).
        expected = [('a',), ('b',)]
        self.assertEqual(expected, distinct('label1'))
        self.assertEqual(expected, distinct(['label1']))

        # Test multiple columns.
        expected = [
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),  # <- ordered (if possible)
            ('b', 'y'),  # <- ordered (if possible)
            ('b', 'x'),  # <- ordered (if possible)
        ]
        self.assertEqual(expected, distinct(['label1', 'label2']))

        # Test multiple columns with filter.
        expected = [('a', 'x'),
                    ('a', 'y'),
                    ('b', 'y'),
                    ('b', 'x')]
        self.assertEqual(expected, distinct(['label1', 'label2'], label2=['x', 'y']))

        # Test multiple columns with filter on non-grouped column.
        expected = [('a', '17'),
                    ('a', '13'),
                    ('b', '25')]
        result = distinct(['label1', 'value'], label2='x')
        if isinstance(self.datasource, ExcelSource):
            result = CompareSet((x, str(int(y))) for x, y in result)
        self.assertEqual(expected, result)

        # Test when specified column is missing.
        msg = 'Error should reference missing column.'
        with self.assertRaisesRegex(Exception, 'label3', msg=msg):
            result = distinct(['label1', 'label3'], label2='x')

    def test_assert_columns_exist(self):
        self.datasource._assert_columns_exist('label1')
        self.datasource._assert_columns_exist(['label1'])
        self.datasource._assert_columns_exist(['label1', 'label2'])

        with self.assertRaisesRegex(LookupError, "'label_x' not in \w+Source"):
            self.datasource._assert_columns_exist('label_x')
