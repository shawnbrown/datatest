"""Custom data source template."""

##########################################################
# DEFINE CUSTOM DATA SOURCE CLASS.
#
#    For basic functionality, implement the __init__(),
#    __repr__(), columns(), and __iter__() methods.  To
#    improve performance, implement some of all of the
#    following: distinct(), sum(), count(), and reduce().
#
##########################################################
import datatest


class MySource(datatest.BaseSource):
    """Add class docstring here."""

    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def __repr__(self):
        """Return a string representation of the data source."""
        return NotImplemented

    def columns(self):
        """Return a list of column names."""
        return NotImplemented

    def __iter__(self):
        """Return iterator of dictionary rows (like csv.DictReader)."""
        return NotImplemented

    # IMPLEMENT SOME OR ALL OF THE FOLLOWING METHODS TO IMPROVE PERFORMANCE.

    #def distinct(self, column, **filter_by):
    #    """Returns distinct *column* values as a ResultSet."""

    #def sum(self, column, group_by=None, **filter_by):
    #    """Returns sum of *column* grouped by *group_by* as ResultMapping."""

    #def count(self, group_by=None, **filter_by):
    #    """Returns count of *column* grouped by *group_by* as ResultMapping."""

    #def reduce(self, function, column, group_by=None, initializer=None, **filter_by):
    #    """Apply *function* of two arguments cumulatively to the values in
    #    *column*, from left to right, so as to reduce the iterable to a single
    #    value.  If *column* is a string, the values are passed to *function*
    #    unchanged.  But if *column* is, itself, a function, it should accept a
    #    single dict-row and return a single value.  If *group_by* is omitted,
    #    the raw result is returned, otherwise returns a ResultMapping object.
    #    """


##########################################################
# DEFINE HELPER CLASS FOR UNIT TESTS.
##########################################################
import unittest

class TestCaseHelper(unittest.TestCase):
    def setUp(self):
        """Create an instance of your custome source with the following
        columns and values:

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
        data = ...
        self.source = MySource(...)


##########################################################
# UNIT TESTS FOR DATA SOURCE CLASS.
#
#     For the most part, the following tests should not
#     be changed.
#
##########################################################
if __name__ == '__main__':
    import unittest
    from collections import Iterator


    class TestA_Helper(TestCaseHelper):
        def test_01_setup(self):
            """TestCaseHelper.setUp() must define a self.source property"""
            self.assertTrue(hasattr(self, 'source'))

        def test_02_subclass(self):
            """self.source must be subclass of datatest.BaseSource"""
            self.assertIsInstance(self.source, datatest.BaseSource)


    class TestB_Repr(TestCaseHelper):
        def test_03_repr(self):
            """calling __repr__() should return a short string"""
            self.assertIsInstance(self.source.__repr__(), str)


    class TestC_Columns(TestCaseHelper):
        def test_04_sequence(self):
            """columns() should return a list"""
            msg = ('if the original source has unordered columns, they should '
                   'be sorted alphabetically by name')
            self.assertIsInstance(self.source.columns(), list, msg=msg)

        def test_05_equality(self):
            self.assertListEqual(self.source.columns(), ['foo', 'bar', 'baz'])


    class TestD_Iter(TestCaseHelper):
        def test_06_iterator(self):
            """calling __iter__() should return an iterator"""
            self.assertIsInstance(self.source.__iter__(), Iterator)

        def test_07_dictrows(self):
            """iterator should yield dict-rows (like csv.DictReader)"""
            first_item = next(self.source.__iter__())

            self.assertIsInstance(first_item, dict)

            msg = 'dict keys should match column names'
            self.assertSetEqual(set(first_item.keys()), set(['foo', 'bar', 'baz']), msg=msg)

        def test_08_equality(self):
            result = self.source.__iter__()
            expecting = [
                {'foo': 'a', 'bar': 'x', 'baz': '8'},
                {'foo': 'a', 'bar': 'y', 'baz': '4'},
                {'foo': 'a', 'bar': 'z', 'baz':  ''},
                {'foo': 'b', 'bar': 'x', 'baz': '5'},
                {'foo': 'b', 'bar':  '', 'baz': '1'},
                {'foo': 'b', 'bar': 'x', 'baz': '2'},
            ]
            compare = lambda itrbl: set(frozenset(x.items()) for x in itrbl)
            self.assertSetEqual(compare(result), compare(expecting))


    class TestE_Distinct(TestCaseHelper):
        def test_09_return_type(self):
            """should return a ResultSet object"""
            return_value = self.source.distinct(['foo', 'bar'])
            self.assertIsInstance(return_value, datatest.ResultSet)

        def test_10_tuple_keys(self):
            """calling with multiple columns should return multi-tuple keys"""
            result = self.source.distinct(['foo', 'bar'])
            expecting = [('a', 'x'), ('a', 'y'), ('a', 'z'), ('b', 'x'), ('b', '')]
            self.assertEqual(self.source.distinct(['foo', 'bar']), expecting)

        def test_11_simple_keys(self):
            """calling with single column should return simple keys"""
            result = self.source.distinct('foo')  # <- one column (as string)
            expecting = ['a', 'b']
            self.assertEqual(self.source.distinct('foo'), expecting)

            expecting = ['a', 'b']
            msg = ("Single-item lists (or other non-string containers) should "
                   "be unwrapped. The ResultSet values should be source "
                   "values--not 1-tuples.")
            self.assertEqual(self.source.distinct(['foo']), expecting, msg=msg)

        def test_12_unknown_column(self):
            """selecting an unknown column should raise a LookupError"""
            with self.assertRaises(LookupError):
                self.source.distinct(['foo', 'qux'])  # <- qux is unknown

        def test_13_keyword_filters(self):
            """distinct() should support **filter_by keyword behavior"""
            result = self.source.distinct(['foo', 'bar'], foo='a')
            expecting = [('a', 'x'), ('a', 'y'), ('a', 'z')]
            msg = ("\n\n"
                   "The following statement should return the distinct values "
                   "of 'foo' and 'baz' for records where 'foo' equals 'a':\n"
                   "\n"
                   "    source.distinct(['foo', 'baz'], foo='a')")
            self.assertEqual(result, expecting, msg=msg)

            result = self.source.distinct(['foo', 'baz'], bar=['x', 'y'])
            expecting = [('a', '8'), ('a', '4'), ('b', '5'), ('b', '2')]
            msg = ("\n\n"
                   "The following statement should return the distinct values "
                   "of 'foo' and 'baz' for records where 'bar' equals 'x' or "
                   "'y':\n"
                   "\n"
                   "    source.distinct(['foo', 'baz'], bar=['x', 'y'])"
            )
            self.assertEqual(result, expecting, msg=msg)

            result = self.source.distinct(['foo', 'baz'], foo='a', bar=['x', 'y'])
            expecting = [('a', '8'), ('a', '4')]
            msg = ("\n\n"
                   "The following statement should return the distinct values "
                   "of 'foo' and 'baz' for records where 'foo' equals 'a' and "
                   "'bar' equals 'x' or 'y':\n"
                   "\n"
                   "    source.distinct(['foo', 'baz'], foo='a', bar=['x', 'y'])"
            )
            self.assertEqual(result, expecting, msg=msg)


    class TestF_Sum(TestCaseHelper):
        def test_14_group_by_none(self):
            """if *group_by* is omitted, should return raw result (not ResultMapping)"""
            self.assertEqual(self.source.sum('baz', group_by=None), 20)

        def test_15_group_by_multiple(self):
            """two *group_by* columns should return ResultMapping with 2-tuple keys"""
            expected = {
                ('a', 'x'): 8,
                ('a', 'y'): 4,
                ('a', 'z'): 0,  # <- Empty string coerced to 0.
                ('b', 'x'): 7,  # <- 5 + 2
                ('b', '' ): 1,
            }
            self.assertDictEqual(self.source.sum('baz', group_by=['foo', 'bar']), expected)

        def test_16_group_by_one(self):
            """one *group_by* column should return ResultMapping with simple keys"""
            expected = {'a': 12, 'b': 8}
            msg = ("Calling sum() with a single *group_by* column should "
                   "return a ResultMapping with the group_by-column's values "
                   "as its keys.")
            self.assertDictEqual(self.source.sum('baz', group_by='foo'), expected, msg=msg)

            expected = {'a': 12, 'b': 8}
            msg = ("Single-item lists (or other non-string containers) should "
                   "be unwrapped. The ResultMapping keys should be source "
                   "values--not 1-tuples.")
            self.assertDictEqual(self.source.sum('baz', group_by=['foo']), expected, msg=msg)

        def test_17_keyword_filters(self):
            """sum() should support **filter_by keyword behavior"""
            expected = {('a', 'x'): 8, ('a', 'y'): 4, ('a', 'z'): 0}
            self.assertDictEqual(self.source.sum('baz', group_by=['foo', 'bar'], foo='a'), expected)

            expected = {('a', 'x'): 8, ('a', 'y'): 4, ('b', 'x'): 7}
            self.assertDictEqual(self.source.sum('baz', group_by=['foo', 'bar'], bar=['x', 'y']), expected)

            expected = {('a', 'x'): 8, ('a', 'y'): 4}
            self.assertDictEqual(self.source.sum('baz', group_by=['foo', 'bar'], foo='a', bar=['x', 'y']), expected)

            self.assertEqual(self.source.sum('baz', foo='a'), 12)

            self.assertEqual(self.source.sum('baz', bar=['x', 'y']), 19)

            self.assertEqual(self.source.sum('baz', foo='a', bar=['y', 'z']), 4)


    class TestG_Count(TestCaseHelper):
        def test_18_group_by_none(self):
            """if *group_by* is omitted, should return raw result (not ResultMapping)"""
            self.assertEqual(self.source.count(group_by=None), 6)

        def test_19_group_by_multiple(self):
            """two *group_by* columns should return ResultMapping with 2-tuple keys"""
            expected = {
                ('a', 'x'): 1,
                ('a', 'y'): 1,
                ('a', 'z'): 1,
                ('b', 'x'): 2,  # <- Two rows where foo equals 'b' and bar equals 'x'.
                ('b', '' ): 1,
            }
            self.assertDictEqual(self.source.count(group_by=['foo', 'bar']), expected)

        def test_20_group_by_one(self):
            """one *group_by* column should return ResultMapping with simple keys"""
            expected = {'a': 3, 'b': 3}
            msg = ("Calling count() with a single *group_by* column should "
                   "return a ResultMapping with the group_by-column's values "
                   "as its keys.")
            self.assertDictEqual(self.source.count(group_by='foo'), expected, msg=msg)

            expected = {'a': 3, 'b': 3}
            msg = ("Single-item lists (or other non-string containers) should "
                   "be unwrapped. The ResultMapping keys should be source "
                   "values--not 1-tuples.")
            self.assertDictEqual(self.source.count(group_by=['foo']), expected, msg=msg)

        def test_21_keyword_filters(self):
            """count() should support **filter_by keyword behavior"""
            expected = {('a', 'x'): 1, ('a', 'y'): 1, ('a', 'z'): 1}
            self.assertDictEqual(self.source.count(group_by=['foo', 'bar'], foo='a'), expected)

            expected = {('a', 'x'): 1, ('a', 'y'): 1, ('b', 'x'): 2}
            self.assertDictEqual(self.source.count(group_by=['foo', 'bar'], bar=['x', 'y']), expected)

            expected = {('a', 'x'): 1, ('a', 'y'): 1}
            self.assertDictEqual(self.source.count(group_by=['foo', 'bar'], foo='a', bar=['x', 'y']), expected)

            self.assertEqual(self.source.count(foo='a'), 3)

            self.assertEqual(self.source.count(bar=['x', 'y']), 4)

            self.assertEqual(self.source.count(foo='a', bar=['y', 'z']), 2)


    class TestH_Reduce(TestCaseHelper):
        def setUp(self):
            TestCaseHelper.setUp(self)

            def maximum(x, y):
                if x and y:
                    return max(x, float(y))
                if y:
                    return float(y)
                return x

            self.max = maximum

        def test_22_group_by_none(self):
            """if *group_by* is omitted, should return raw result (not ResultMapping)"""
            self.assertEqual(self.source.reduce(self.max, 'baz', group_by=None), 8)

        def test_23_group_by_multiple(self):
            """two *group_by* columns should return ResultMapping with 2-tuple keys"""
            expected = {
                ('a', 'x'): 8,
                ('a', 'y'): 4,
                ('a', 'z'): None,  # <- Empty string left as None.
                ('b', 'x'): 5,  # <- 5 > 2
                ('b', '' ): 1,
            }
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by=['foo', 'bar']), expected)

        def test_24_group_by_one(self):
            """one *group_by* column should return ResultMapping with simple keys"""
            expected = {'a': 8, 'b': 5}
            msg = ("Calling reduce() with a single *group_by* column should "
                   "return a ResultMapping with the group_by-column's values "
                   "as its keys.")
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by='foo'), expected, msg=msg)

            expected = {'a': 8, 'b': 5}
            msg = ("Single-item lists (or other non-string containers) should "
                   "be unwrapped. The ResultMapping keys should be source "
                   "values--not 1-tuples.")
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by=['foo']), expected, msg=msg)

        def test_25_mapping_column(self):
            """when *column* is a callable function, it is used to map values"""

            def mapfn(row):  # <- Maps from "row" to "baz times two".
                baz = row['baz']
                if baz:
                    baz = float(baz) * 2
                return baz

            expected = {
                ('a', 'x'): 16,
                ('a', 'y'): 8,
                ('a', 'z'): None,  # <- Empty remains unchanged.
                ('b', 'x'): 10,    # <- Max of 10 and 4 (5 * 2 and 2 * 2).
                ('b', '' ): 2,
            }
            msg = ('When *column* is a callable function (instead of just a '
                   'column name), it must accept a dict-row and return a '
                   'single value.  A callable column is used to map values '
                   'before running the reduce *function*.')
            self.assertDictEqual(self.source.reduce(self.max, mapfn, group_by=['foo', 'bar']), expected, msg=msg)

            msg = ('Callable *column* support should also work when group_by '
                   'is omitted')
            self.assertEqual(self.source.reduce(self.max, mapfn, group_by=None), 16, msg=msg)

        def test_26_keyword_filters(self):
            """reduce() should support **filter_by keyword behavior"""
            expected = {('a', 'x'): 8, ('a', 'y'): 4, ('a', 'z'): None}
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by=['foo', 'bar'], foo='a'), expected)

            expected = {('a', 'x'): 8, ('a', 'y'): 4, ('b', 'x'): 5}
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by=['foo', 'bar'], bar=['x', 'y']), expected)

            expected = {('a', 'x'): 8, ('a', 'y'): 4}
            self.assertDictEqual(self.source.reduce(self.max, 'baz', group_by=['foo', 'bar'], foo='a', bar=['x', 'y']), expected)

            self.assertEqual(self.source.reduce(self.max, 'baz', foo='a'), 8)

            self.assertEqual(self.source.reduce(self.max, 'baz', bar=['x', 'y']), 8)

            self.assertEqual(self.source.reduce(self.max, 'baz', foo='a', bar=['y', 'z']), 4)


    unittest.main(failfast=True)
