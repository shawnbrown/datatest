"""Custom data source template."""
import datatest


class MyDataSource(datatest.BaseDataSource):

    #############################
    # For basic functionality.
    #############################
    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def __str__(self):
        """Return a brief description of the data source."""
        return NotImplemented

    def columns(self):
        """Return a sequence of column names."""
        return NotImplemented

    def slow_iter(self):
        """Return iterable of dict rows (like csv.DictReader)."""
        return NotImplemented

    #############################
    # For higher performance.
    #############################
    #def unique(*column, **filter_by)
    #    """Return iterable of unique tuples of column values."""

    #def sum(column, **filter_by):
    #    """Return sum of values in column."""

    #def count(column, **filter_by):
    #    """Return count of non-empty values in column."""


if __name__ == '__main__':
    import unittest
    from collections import Sequence

    class TestMyDataSource(unittest.TestCase):
        """
            +-----+-----+-----+
            | foo | bar | baz |
            +-----+-----+-----+
            |  a  |  x  |  8  |
            |  a  |  y  |  4  |
            |  a  |  z  |     |
            |  b  |  x  |  5  |
            |  b  |     |  1  |
            |  b  |  x  |  2  |
            +-----+-----+-----+
        """
        def setUp(self):
            data = ... # <- data here
            self.source = MyDataSource(data)

        def test_1_str(self):
            """Test __str__() method."""
            # The __str__() method should return a short string.
            result = self.source.__str__()
            self.assertTrue(isinstance(result, str))

        def test_2_columns(self):
            """Test columns() method."""
            # The columns() method should return a sequence of
            # columns in their original order.  If the columns of
            # a data source are unordered, then it should return
            # the columns sorted by name.
            result = self.source.columns()
            self.assertTrue(isinstance(result), Sequence)
            self.assertEqual(['foo', 'bar', 'baz'], list(result))

        def test_3_slow_iter(self):
            """Test slow_iter() method."""
            # The slow_iter() method should return a generator to
            # support large data sources but any iterable will work
            # as long as it returns dict-rows.
            result = self.source.slow_iter()
            expecting = [
                {'foo': 'a', 'bar': 'x', 'baz': '8'},
                {'foo': 'a', 'bar': 'y', 'baz': '4'},
                {'foo': 'a', 'bar': 'z', 'baz': ''},
                {'foo': 'b', 'bar': 'x', 'baz': '5'},
                {'foo': 'b', 'bar': '',  'baz': '1'},
                {'foo': 'b', 'bar': 'x', 'baz': '2'},
            ]
            self.assertEqual(expecting, list(result))

        def test_4_unique(self):
            """Test unique() method."""
            result = list(self.source.unique('foo', 'bar'))
            expecting = [('a', 'x'),
                         ('a', 'y'),
                         ('a', 'z'),
                         ('b', 'x'),
                         ('b', '' )]
            self.assertEqual(expecting, result)

            result = list(self.source.unique('foo'))
            self.assertEqual([('a',), ('b',)], result)

            result = list(self.source.unique('foo', 'bar'), foo='a')
            expecting = [('a', 'x'),
                         ('a', 'y'),
                         ('a', 'z')]
            self.assertEqual(expecting, result)

            result = list(self.source.unique('foo', 'baz'), bar=['x', 'y'])
            expecting = [('a', 'x'),
                         ('a', 'y'),
                         ('b', 'x')]
            self.assertEqual(expecting, result)

            result = list(self.source.unique('foo', 'baz'), foo='a', bar=['x', 'y'])
            expecting = [('a', 'x'),
                         ('a', 'y')]
            self.assertEqual(expecting, result)

            # Selecting an unknown column ("qux") should raise an exception.
            with assertRaises(Exception):
                list(self.source.unique('foo', 'qux'))

        def test_5_sum(self):
            """Test sum() method."""
            self.assertEqual(20, self.source.sum('baz'))
            self.assertEqual(self.source.sum('baz', foo='a'), 12)
            self.assertEqual(self.source.sum('baz', bar=['x', 'y']), 19)
            self.assertEqual(self.source.sum('baz', foo='a', bar=['y', 'z']), 4)

        def test_6_count(self):
            """Test count() method."""
            self.assertEqual(self.source.count(), 6)
            self.assertEqual(self.source.count(foo='a'), 3)
            self.assertEqual(self.source.count(bar=['x', 'y']), 4)
            self.assertEqual(self.source.count(foo='a', bar=['x', 'y']), 2)

        def test_7_set(self):
            """Test set() method."""
            result = self.source.set('foo')
            self.assertEqual(result, {'a', 'b'})

            result = self.source.set('bar', foo='a')
            self.assertEqual(result, {'x', 'y', 'z'})


    unittest.main()

