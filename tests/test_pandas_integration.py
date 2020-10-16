"""Tests for Pandas accessor extensions."""
from . import _unittest as unittest

try:
    import pandas
except ImportError:
    pandas = None

from datatest import Invalid
from datatest import ValidationError
from datatest import register_accessors


@unittest.skipUnless(pandas, 'requires pandas')
class TestAccessorExtensions(unittest.TestCase):
    """Test Pandas accessors."""
    def setUp(self):          # Change to `setUpClass` when dropping
        register_accessors()  # support for Python 2.6 and 3.1.
        self.df = pandas.DataFrame(
            data=[(1, 'x'), (2, 'y'), (3, 'z')],
            columns=['A', 'B'],
        )

    def test_dataframe_success(self):
        # Should pass without error on success.
        self.df.validate((int, str))

    def test_dataframe_failure(self):
        with self.assertRaises(ValidationError) as cm:
            is_odd = lambda x: x % 2 == 1
            self.df.validate((is_odd, str))

        actual = cm.exception.differences
        expected = [Invalid((2, 'y'))]
        self.assertEqual(actual, expected)

    def test_series_success(self):
        # Should pass without error on success.
        self.df.columns.validate.order(['A', 'B'])  # Columns are a Series
        self.df['A'].validate(int)  # A selected Series of column values.

    def test_series_failure(self):
        with self.assertRaises(ValidationError) as cm:
            is_odd = lambda x: x % 2 == 1
            self.df['A'].validate(is_odd)

        self.assertEqual(cm.exception.differences, [Invalid(2)])

    def test_index_success(self):
        # Should pass without error on success.
        self.df.index.validate(int)

    def test_index_failure(self):
        with self.assertRaises(ValidationError) as cm:
            is_odd = lambda x: x % 2 == 1
            self.df.index.validate(is_odd)

        actual = cm.exception.differences
        expected = [Invalid(0), Invalid(2)]
        self.assertEqual(actual, expected)

    def test_multiindex_success(self):
        # Should pass without error on success.
        multi_index = pandas.MultiIndex.from_arrays(
            [[1, 1, 2], ['A', 'B', 'C']],
            names=('number', 'letter')
        )
        multi_index.validate((int, str))

    def test_multiindex_failure(self):
        multi_index = pandas.MultiIndex.from_arrays(
            [[1, 1, 2], ['A', 'B', 'C']],
            names=('number', 'letter')
        )
        with self.assertRaises(ValidationError) as cm:
            is_odd = lambda x: x % 2 == 1
            multi_index.validate((is_odd, str))

        self.assertEqual(cm.exception.differences, [Invalid((2, 'C'))])
