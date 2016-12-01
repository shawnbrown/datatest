# -*- coding: utf-8 -*-
import inspect
from . import _unittest as unittest
from datatest.utils import collections

from datatest import DataError
from datatest import Missing
from datatest import Extra
from datatest import Deviation
from datatest.allow import allow_iter
from datatest.allow import allow_any
from datatest.allow import allow_missing
from datatest.allow import allow_extra
from datatest.allow import allow_deviation
from datatest.allow import allow_percent_deviation
from datatest.allow import allow_limit
from datatest.allow import allow_only


class TestAllowIter(unittest.TestCase):
    def test_iterable_all_bad(self):
        """Given a non-mapping iterable in which all items are invalid,
        *function* should return a non-mapping iterable containing all
        items.
        """
        function = lambda iterable: iterable  # <- Rejects everything.
        in_diffs = [Extra('foo'), Extra('bar')]

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

    def test_iterable_all_good(self):
        """Given a non-mapping iterable in which all items are valid,
        *function* should omit all items and simply return an empty
        iterable.
        """
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs =  [Missing('foo'), Missing('bar')]

        with allow_iter(function):  # <- Passes without error.
            raise DataError('example error', in_diffs)

    def test_empty_generator(self):
        """If all items are valid, returning an empty generator or other
        iterable non-container should work, too.
        """
        function = lambda iterable: (x for x in [])  # <- Empty generator.
        in_diffs =  [Missing('foo'), Missing('bar')]

        with allow_iter(function):  # <- Passes without error.
            raise DataError('example error', in_diffs)

    def test_iterable_some_good(self):
        """Given a non-mapping iterable, *function* should return those
        items which are invalid and omit those items which are valid.
        """
        function = lambda iterable: (x for x in iterable if x.value != 'bar')
        in_diffs = [Missing('foo'), Missing('bar')]

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(list(out_diffs), [Missing('foo')])

    def test_mapping_all_bad(self):
        """Given a mapping in which all items are invalid, *function*
        should return a mapping containing all items.
        """
        function = lambda mapping: mapping  # <- Rejects entire mapping.
        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

    def test_mapping_all_good(self):
        """Given a mapping in which all items are valid, *function*
        should omit all items and simply return an empty mapping.
        """
        function = lambda mapping: {}  # <- Accepts everything.
        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}

        with allow_iter(function):  # <- Passes without error.
            raise DataError('example error', in_diffs)

    def test_mapping_some_good(self):
        """Given a mapping in which all items are valid, *function*
        should omit all items and simply return an empty mapping.
        """
        def function(mapping):
            for key, diff in mapping.items():
                if diff.value == 'bar':
                    yield (key, diff)

        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, {('BBB', 'yyy'): Missing('bar')})

    def test_returns_sequence(self):
        """If given a mapping, *function* may return an iterable of
        sequences (instead of a mapping).  Each sequence must contain
        exactly two objects---the first object will be use as the key
        and the second object will be used as the value (same as
        Python's 'dict' behavior).
        """
        # Simple key.
        in_diffs = {'AAA': Missing('foo'),
                    'BBB': Missing('bar')}
        return_val = [['AAA', Missing('foo')],  # <- Two items.
                      ['BBB', Missing('bar')]]  # <- Two items.

        with self.assertRaises(DataError) as cm:
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

        # Compound key.
        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}
        return_val = [[('AAA', 'xxx'), Missing('foo')],  # <- Two items.
                      [('BBB', 'yyy'), Missing('bar')]]  # <- Two items.

        with self.assertRaises(DataError) as cm:
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

        # Duplicate keys--last defined value (bar) appears in mapping.
        in_diffs = {'AAA': Missing('foo'),
                    'BBB': Missing('bar')}
        return_val = [['AAA', Missing('foo')],
                      ['BBB', Missing('xxx')],  # <- Duplicate key.
                      ['BBB', Missing('yyy')],  # <- Duplicate key.
                      ['BBB', Missing('zzz')],  # <- Duplicate key.
                      ['BBB', Missing('bar')]]  # <- Duplicate key.

        with self.assertRaises(DataError) as cm:
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

    def test_returns_bad_sequence(self):
        """In place of mapping objects, *function* may instead return an
        iterable of two-item sequences but if the sequence contains more
        or less items, a ValueError should be raised.
        """
        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}

        # mapping / iterable of 1-item sequences.
        return_val = [[Missing('foo')],  # <- One item.
                      [Missing('bar')]]  # <- One item.

        regex = ('has length 1.*2 is required')
        with self.assertRaisesRegex(ValueError, regex):  # <- ValueError!
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # mapping / iterable of 3-item sequences.
        return_val = [[('AAA', 'xxx'), Missing('foo'), None],  # <- Three items.
                      [('BBB', 'yyy'), Missing('bar'), None]]  # <- Three items.

        regex = 'has length 3.*2 is required'
        with self.assertRaisesRegex(ValueError, regex):  # <- ValueError!
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

    def test_returns_bad_type(self):
        """The *function* should return the same type it was given or a
        compatible object--if not, a TypeError should be raised.
        """
        in_diffs = {('AAA', 'xxx'): Missing('foo'),
                    ('BBB', 'yyy'): Missing('bar')}

        # mapping / iterable ot 2-char strings
        return_val = ['Ax', 'By']  # <- Two-character strings.

        regex = r"must be non-string sequence.*found 'str' instead"
        with self.assertRaisesRegex(TypeError, regex):
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # mapping / iterable of non-sequence items
        return_val = [Missing('foo'),  # <- Non-sequence item.
                      Missing('bar')]  # <- Non-sequence item.

        regex = ("must be non-string sequence.*found 'Missing'")
        with self.assertRaisesRegex(TypeError, regex):
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # nonmapping / mapping
        in_diffs = [Missing('foo'), Missing('bar')]  # <- List (non-mapping)!
        return_val = {'AAA': Missing('foo'), 'BBB': Missing('bar')}  # <- Mapping!

        regex = "input was 'list' but function returned a mapping"
        with self.assertRaisesRegex(TypeError, regex):
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)


class TestAllowAny(unittest.TestCase):
    def test_keywords_omitted(self):
        regex = "keyword argument required: must be one of 'keys', 'diffs', 'items'"
        with self.assertRaisesRegex(TypeError, regex):
            with allow_any():  # <- Keyword arg omitted!
                pass

    def test_keywords_invalid(self):
        regex = "'foo' is an invalid keyword argument: must be one of"
        with self.assertRaisesRegex(TypeError, regex):
            function = lambda x: True
            with allow_any(foo=function):  # <- foo is invalid!
                pass

    def test_diffs_nonmapping(self):
        in_diffs = [Missing('foo'), Missing('bar')]
        function = lambda x: x.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(diffs=function):  # <- Using diffs keyword!
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, [Missing('bar')])

    def test_diffs_mapping(self):
        in_diffs = {'AAA': Missing('foo'), 'BBB': Missing('bar')}
        function = lambda x: x.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(diffs=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': Missing('bar')})

    def test_keys_nonmapping(self):
        # Missing required keyword 'diffs'.
        in_diffs = [Missing('foo'), Missing('bar')]
        function = lambda first, second: first == 'AAA'

        regex = "accepts only 'diffs' keyword, found 'keys'"
        with self.assertRaisesRegex(ValueError, regex):
            with allow_any(keys=function):  # <- expects 'diffs='.
                raise DataError('example error', in_diffs)

        # Disallowed keywords ('keys').
        in_diffs = [Missing('foo'), Missing('bar')]
        function = lambda first, second: first == 'AAA'

        with self.assertRaisesRegex(ValueError, "found 'keys'"):
            with allow_any(diffs=function, keys=function):  # <- 'keys=' not allowed.
                raise DataError('example error', in_diffs)

    def test_keys_mapping(self):
        # Function accepts single argument.
        in_diffs = {'AAA': Missing('foo'), 'BBB': Missing('bar')}
        function = lambda x: x == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': Missing('bar')})

        # Function accepts multiple arguments.
        in_diffs = {('AAA', 'XXX'): Missing('foo'),
                    ('BBB', 'YYY'): Missing('bar')}

        def function(first, second):  # <- Multiple args.
            return second == 'XXX'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): Missing('bar')})

    def test_items_nonmapping(self):
        # TODO: Explore the idea of accepting mapping-compatible
        # iterator of items.
        pass

    def test_items_mapping(self):
        # Function of one argument.
        in_diffs = {'AAA': Missing('foo'), 'BBB': Missing('bar')}

        def function(item):
            key, diff = item  # Unpack item tuple.
            return key == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': Missing('bar')})

        # Function of two arguments.
        in_diffs = {'AAA': Missing('foo'), 'BBB': Missing('bar')}

        def function(key, diff):
            return key == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': Missing('bar')})

        # Function of three arguments.
        in_diffs = {('AAA', 'XXX'): Missing('foo'),
                    ('BBB', 'YYY'): Missing('bar')}

        def function(key1, key2, diff):
            return key2 == 'XXX'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): Missing('bar')})

    def test_keyword_combinations(self):
        in_diffs = {('AAA', 'XXX'): Missing('foo'),
                    ('BBB', 'YYY'): Missing('foo'),
                    ('CCC', 'XXX'): Extra('bar'),
                    ('DDD', 'XXX'): Missing('foo')}

        def fn1(key1, key2):
            return key2 == 'XXX'

        def fn2(diff):
            return diff.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=fn1, diffs=fn2):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): Missing('foo'),
                                    ('CCC', 'XXX'): Extra('bar')})


class TestAllowMissing(unittest.TestCase):
    """Test allow_missing() behavior."""
    def test_allow_some(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_missing():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Extra('xxx')])

    def test_allow_all(self):
        with allow_missing():
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_diffs_keyword(self):
        in_diffs = {
            'foo': Missing('xxx'),
            'bar': Missing('yyy'),
            'baz': Extra('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x.value in ('yyy', 'zzz')

            with allow_missing(diffs=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'foo': Missing('xxx'), 'baz': Extra('zzz')})

    def test_keys_keyword(self):
        in_diffs = {
            'foo': Missing('xxx'),
            'bar': Missing('yyy'),
            'baz': Extra('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x in ('foo', 'baz')

            with allow_missing(keys=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'bar': Missing('yyy'), 'baz': Extra('zzz')})

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_missing():
                pass  # No exception raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_missing', str(exc))


class TestAllowExtra(unittest.TestCase):
    """Test allow_extra() behavior."""
    def test_allow_some(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_extra():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('yyy')])

    def test_allow_all(self):
        with allow_extra():
            raise DataError('example error', [Extra('xxx'), Extra('yyy')])

    def test_diffs_keyword(self):
        in_diffs = {
            'foo': Extra('xxx'),
            'bar': Extra('yyy'),
            'baz': Missing('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x.value in ('yyy', 'zzz')

            with allow_extra(diffs=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'foo': Extra('xxx'), 'baz': Missing('zzz')})

    def test_keys_keyword(self):
        in_diffs = {
            'foo': Extra('xxx'),
            'bar': Extra('yyy'),
            'baz': Missing('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x in ('foo', 'baz')

            with allow_extra(keys=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'bar': Extra('yyy'), 'baz': Missing('zzz')})

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_extra():
                pass  # No exception raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_extra', str(exc))


class TestAllowDeviation(unittest.TestCase):
    """Test allow_deviation() behavior."""
    def test_method_signature(self):
        """Check for prettified default signature in Python 3.3 and later."""
        try:
            sig = inspect.signature(allow_deviation)
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'kwds_func'])
        except AttributeError:
            pass  # Python 3.2 and older use ugly signature as default.

    def test_tolerance_syntax(self):
        differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+3, 10),  # <- Not in allowed range.
        }
        with self.assertRaises(DataError) as cm:
            with allow_deviation(2):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        #result_string = str(cm.exception)
        #self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'bbb': Deviation(+3, 10)}, result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            with allow_deviation(0, 3):  # <- Allows from 0 to 3.
                raise DataError('example error', differences)

        #result_string = str(cm.exception)
        #self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation(+2.9, 10),  # <- Not allowed.
            Deviation(+3.0, 10),
            Deviation(+3.0, 5),
            Deviation(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(3, 3):  # <- Allows +3 only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            Deviation(+2.9, 10),
            Deviation(+3.1, 10),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_keys_keyword(self):
        with self.assertRaises(DataError) as cm:
            differences = {
                'aaa': Deviation(-1, 10),
                'bbb': Deviation(+2, 10),
                'ccc': Deviation(+2, 10),
                'ddd': Deviation(+3, 10),
            }
            fn = lambda key: key in ('aaa', 'bbb', 'ddd')
            with allow_deviation(2, keys=fn):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        actual = cm.exception.differences
        expected = {
            'ccc': Deviation(+2, 10),  # <- Keyword value not allowed.
            'ddd': Deviation(+3, 10),  # <- Not in allowed range.
        }
        self.assertEqual(expected, actual)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_deviation(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(None, 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation('', 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [Deviation(0, float('nan'))])

    # AN OPEN QUESTION: Should deviation allowances raise an error if
    # the maximum oberved deviation is _less_ than the given tolerance?


class TestAllowPercentDeviation(unittest.TestCase):
    """Test allow_percent_deviation() behavior."""
    def test_method_signature(self):
        """Check for prettified default signature in Python 3.3 and later."""
        try:
            sig = inspect.signature(allow_percent_deviation)
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'kwds_func'])
        except AttributeError:
            pass  # Python 3.2 and older use ugly signature as default.

    def test_tolerance_syntax(self):
        differences = [
            Deviation(-1, 10),
            Deviation(+3, 10),  # <- Not in allowed range.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.2):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Deviation(+3, 10)], result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation(+2.9, 10, label='aaa'),  # <- Not allowed.
            Deviation(+3.0, 10, label='bbb'),
            Deviation(+6.0, 20, label='ccc'),
            Deviation(+3.1, 10, label='ddd'),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.3, 0.3):  # <- Allows +30% only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            Deviation(+2.9, 10, label='aaa'),
            Deviation(+3.1, 10, label='ddd'),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+2, 10),
            'ccc': Deviation(+2, 10),
            'ddd': Deviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            fn = lambda x: x in ('aaa', 'bbb', 'ddd')
            with allow_percent_deviation(0.2, keys=fn):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_set = cm.exception.differences
        expected_set = {
            'ccc': Deviation(+2, 10),  # <- Key value not 'aaa'.
            'ddd': Deviation(+3, 10),  # <- Not in allowed range.
        }
        self.assertEqual(expected_set, result_set)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_percent_deviation(-0.5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(None, 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation('', 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [Deviation(0, float('nan'))])


class TestAllowLimit(unittest.TestCase):
    """Test allow_limit() behavior."""
    def test_exceeds_limit(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_limit(1):  # <- Allows only 1 but there are 2!
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(differences, rejected)

    def test_matches_limit(self):
        with allow_limit(2):  # <- Allows 2 and there are only 2.
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_under_limit(self):
        with allow_limit(3):  # <- Allows 3 and there are only 2.
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_kwds_exceeds_limit(self):
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit(1, diffs=is_extra):  # <- Limit of 1 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(differences, rejected)

    def test_kwds_matches_limit(self):
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit(2, diffs=is_extra):  # <- Limit of 2 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual([Missing('yyy')], rejected)

    def test_kwds_under_limit(self):
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit(4, diffs=is_extra):  # <- Limit of 4 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual([Missing('yyy')], rejected)

    def test_dict_of_diffs_exceeds(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        with self.assertRaises(DataError) as cm:
            with allow_limit(1):  # <- Allows only 1 but there are 2!
                raise DataError('example error', differences)

        rejected = cm.exception.differences
        self.assertEqual(differences, rejected)

    def test_dict_of_diffs_kwds_func_under_limit(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit(2, diffs=is_extra):
                raise DataError('example error', differences)

        rejected = cm.exception.differences
        self.assertEqual({'bar': Missing('yyy')}, rejected)


class TestAllowOnly(unittest.TestCase):
    """Test allow_only() behavior."""
    def test_some_allowed(self):
        differences = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx')]

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [Missing('yyy')]
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

    def test_all_allowed(self):
        diffs = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx'), Missing('yyy')]
        with allow_only(allowed):
            raise DataError('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        differences = [Extra('xxx'), Extra('xxx'), Extra('xxx')]

        # Only allow one of them.
        with self.assertRaises(DataError) as cm:
            allowed = [Extra('xxx')]
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [Extra('xxx'), Extra('xxx')]  # Expect two remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Only allow two of them.
        with self.assertRaises(DataError) as cm:
            allowed = [Extra('xxx'), Extra('xxx')]
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [Extra('xxx')]  # Expect one remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Allow all three.
        allowed = [Extra('xxx'), Extra('xxx'), Extra('xxx')]
        with allow_only(allowed):
            raise DataError('example error', differences)

    def test_mapping_some_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {'foo': Extra('xxx')}

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = {'bar': Missing('yyy')}
        actual = cm.exception.differences
        self.assertEqual(expected, actual)

    def test_mapping_none_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {}

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        actual = cm.exception.differences
        self.assertEqual(differences, actual)

    def test_mapping_all_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = differences

        with allow_only(allowed):  # <- Catches all differences, no error!
            raise DataError('example error', differences)

    def test_mapping_mismatched_types(self):
        # Dict of diffs vs list of allowed.
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = [Extra('xxx'), Missing('yyy')]

        regex = ("expects non-mapping differences but found 'dict' of "
                 "differences")
        with self.assertRaisesRegex(ValueError, regex):
            with allow_only(allowed):
                raise DataError('example error', differences)

        # List of diffs vs dict of allowed.
        differences = [Extra('xxx'), Missing('yyy')]
        allowed = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        regex = ("expects mapping of differences but found 'list' of "
                 "differences")
        with self.assertRaisesRegex(ValueError, regex):
            with allow_only(allowed):
                raise DataError('example error', differences)
