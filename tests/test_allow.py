# -*- coding: utf-8 -*-
import inspect
from . import _unittest as unittest
from datatest.utils import collections
from datatest.dataaccess import ItemsIter

from datatest.error import DataError
from datatest.differences import xMissing
from datatest.differences import xExtra
from datatest.differences import xDeviation
from datatest.allow import allow_iter
from datatest.allow import allow_any
from datatest.allow import allow_missing
from datatest.allow import allow_extra
from datatest.allow import allow_deviation
from datatest.allow import allow_percent_deviation
from datatest.allow import allow_limit
from datatest.allow import allow_only

from datatest.allow import allow_iter2
from datatest.allow import _allow_element
from datatest.allow import allow_any2
from datatest.allow import allow_all2
from datatest.allow import allow_missing2
from datatest.allow import allow_extra2
from datatest.allow import allow_deviation2
from datatest.allow import allow_percent_deviation2
from datatest.allow import allow_specified2
from datatest.allow import allow_limit2
from datatest.allow import getvalue
from datatest.allow import getkey
from datatest.errors import ValidationErrors
from datatest.errors import DataError as DataError2
from datatest.errors import Missing as Missing2
from datatest.errors import Extra as Extra2
from datatest.errors import Deviation as Deviation2


# FOR TESTING: A minimal subclass of DataError. DataError itself
# is a base class that should not be instantiated directly.
class MinimalDataError(DataError):
    pass


class TestAllowIter2(unittest.TestCase):
    def test_iterable_all_good(self):
        function = lambda iterable: list()  # <- empty list
        with allow_iter2(function):  # <- Should pass without error.
            raise ValidationErrors('example error', [Missing2('x')])

        function = lambda iterable: iter([])  # <- empty iterator
        with allow_iter2(function):  # <- Should pass pass without error.
            raise ValidationErrors('example error', [Missing2('x')])

    def test_iterable_some_bad(self):
        function = lambda iterable: [Missing2('foo')]
        in_diffs = [Missing2('foo'), Missing2('bar')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_iter2(function):
                raise ValidationErrors('example error', in_diffs)

        errors = cm.exception.errors
        self.assertEqual(list(errors), [Missing2('foo')])

    def test_mismatched_types(self):
        """When given a non-mapping container, a non-mapping container
        should be returned for any remaining errors. Likewise, when
        given a mapping, a mapping should be returned for any remaining
        errors. If the intput and output types are mismatched, a
        TypeError should be raised.
        """
        # List input and dict output.
        errors_list =  [Missing2('foo'), Missing2('bar')]
        function = lambda iterable: {'a': Missing2('foo')}  # <- dict type
        with self.assertRaises(TypeError):
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_list)

        # Dict input and list output.
        errors_dict =  {'a': Missing2('foo'), 'b': Missing2('bar')}
        function = lambda iterable: [Missing2('foo')]  # <- list type
        with self.assertRaises(TypeError):
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_dict)

        # Dict input and list-item output.
        errors_dict =  {'a': Missing2('foo'), 'b': Missing2('bar')}
        function = lambda iterable: [('a', Missing2('foo'))]  # <- list of items
        with self.assertRaises(ValidationErrors) as cm:
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_dict)

        errors = cm.exception.errors
        #self.assertIsInstance(errors, DictItems)
        self.assertEqual(dict(errors), {'a': Missing2('foo')})


class TestAllowSpecified2(unittest.TestCase):
    def test_some_allowed(self):
        errors = [Extra2('xxx'), Missing2('yyy')]
        allowed = [Extra2('xxx')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Missing2('yyy')]
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

    def test_single_diff_without_container(self):
        errors = [Extra2('xxx'), Missing2('yyy')]
        allowed = Extra2('xxx')  # <- Single diff, not in list.

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Missing2('yyy')]
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

    def test_all_allowed(self):
        diffs = [Extra2('xxx'), Missing2('yyy')]
        allowed = [Extra2('xxx'), Missing2('yyy')]
        with allow_specified2(allowed):
            raise ValidationErrors('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        errors = [Extra2('xxx'), Extra2('xxx'), Extra2('xxx')]

        # Only allow one of them.
        with self.assertRaises(ValidationErrors) as cm:
            allowed = [Extra2('xxx')]
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Extra2('xxx'), Extra2('xxx')]  # Expect two remaining.
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

        # Only allow two of them.
        with self.assertRaises(ValidationErrors) as cm:
            allowed = [Extra2('xxx'), Extra2('xxx')]
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Extra2('xxx')]  # Expect one remaining.
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

        # Allow all three.
        allowed = [Extra2('xxx'), Extra2('xxx'), Extra2('xxx')]
        with allow_specified2(allowed):
            raise ValidationErrors('example error', errors)

    def test_error_mapping_allowance_list(self):
        differences = {'foo': [Extra2('xxx')], 'bar': [Extra2('xxx'), Missing2('yyy')]}
        allowed = [Extra2('xxx')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        expected = {'bar': [Missing2('yyy')]}
        actual = cm.exception.errors
        self.assertEqual(expected, actual)

    def test_mapping_some_allowed(self):
        differences = {'foo': Extra2('xxx'), 'bar': Missing2('yyy')}
        allowed = {'foo': Extra2('xxx')}

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        expected = {'bar': Missing2('yyy')}
        actual = cm.exception.errors
        self.assertEqual(expected, actual)

    def test_mapping_none_allowed(self):
        differences = {'foo': Extra2('xxx'), 'bar': Missing2('yyy')}
        allowed = {}

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        actual = cm.exception.errors
        self.assertEqual(differences, actual)

    def test_mapping_all_allowed(self):
        errors = {'foo': Extra2('xxx'), 'bar': Missing2('yyy')}
        allowed = errors

        with allow_specified2(allowed):  # <- Catches all differences, no error!
            raise ValidationErrors('example error', errors)

    def test_mapping_mismatched_types(self):
        error_list = [Extra2('xxx'), Missing2('yyy')]
        allowed_dict = {'foo': Extra2('xxx'), 'bar': Missing2('yyy')}

        regex = "'list' of errors cannot be matched.*requires non-mapping type"
        with self.assertRaisesRegex(ValueError, regex):
            with allow_specified2(allowed_dict):
                raise ValidationErrors('example error', error_list)

    def test_integration(self):
        """This is a bit of an integration test."""
        differences = {'foo': Extra2('xxx'), 'bar': Missing2('zzz')}
        allowed = [Extra2('xxx'), Missing2('yyy')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)
        actual = cm.exception.errors

        # Item-by-item assertion used to because Exception()
        # can not be tested for equality.
        self.assertIsInstance(actual, dict)
        self.assertEqual(set(actual.keys()), set(['foo', 'bar']))
        self.assertEqual(len(actual), 2)
        self.assertEqual(
            actual['foo'][0].args[0],
            "allowed errors not found: [Missing('yyy')]"
        )
        self.assertEqual(actual['bar'][0], Missing2('zzz'))
        self.assertEqual(
            actual['bar'][1].args[0],
            "allowed errors not found: [Extra('xxx'), Missing('yyy')]"
        )


class TestAllowLimit2(unittest.TestCase):
    """Test allow_limit() behavior."""
    def test_exceeds_limit(self):
        errors = [Extra2('xxx'), Missing2('yyy')]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_limit2(1):  # <- Allows only 1 but there are 2!
                raise ValidationErrors('example error', errors)

        remaining = list(cm.exception.errors)
        self.assertEqual(remaining, errors)

    def test_matches_limit(self):
        errors = [Extra2('xxx'), Missing2('yyy')]
        with allow_limit2(2):  # <- Allows 2 and there are only 2.
            raise ValidationErrors('example error', errors)

    def test_under_limit(self):
        errors = [Extra2('xxx'), Missing2('yyy')]
        with allow_limit2(3):  # <- Allows 3 and there are only 2.
            raise ValidationErrors('example error', errors)

    def test_function_exceeds_limit(self):
        errors = [Extra2('xxx'), Missing2('yyy'), Extra2('zzz')]
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra2)
            with allow_limit2(1, is_extra):  # <- Limit of 1 and is_extra().
                raise ValidationErrors('example error', errors)

        # Returned errors can be in different order.
        actual = list(cm.exception.errors)
        expected = [Missing2('yyy'), Extra2('xxx'), Extra2('zzz')]
        self.assertEqual(actual, expected)

    def test_function_under_limit(self):
        errors = [Extra2('xxx'), Missing2('yyy'), Extra2('zzz')]
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra2)
            with allow_limit2(4, is_extra):  # <- Limit of 4 and is_extra().
                raise ValidationErrors('example error', errors)

        actual = list(cm.exception.errors)
        self.assertEqual(actual, [Missing2('yyy')])

    def test_dict_of_diffs_exceeds_and_match(self):
        errors = {
            'foo': [Extra2('xxx'), Missing2('yyy')],
            'bar': [Extra2('zzz')],
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_limit2(1):  # <- Allows only 1 but there are 2!
                raise ValidationErrors('example error', errors)

        actual = cm.exception.errors
        expected = {'foo': [Extra2('xxx'), Missing2('yyy')]}
        self.assertEqual(dict(actual), expected)

    def test_dict_of_diffs_and_function(self):
        errors = {
            'foo': [Extra2('xxx'), Missing2('yyy')],
            'bar': [Extra2('zzz')],
        }
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra2)
            with allow_limit2(1, is_extra):
                raise ValidationErrors('example error', errors)

        actual = cm.exception.errors
        expected = {'foo': [Missing2('yyy')]}
        self.assertEqual(dict(actual), expected)


class TestAllowElement(unittest.TestCase):
    def test_list_of_errors(self):
        errors =  [Missing2('X'), Missing2('Y')]
        func1 = lambda x: True
        func2 = lambda x: False

        with _allow_element(any, (func1,)):
            raise ValidationErrors('one True', errors)

        with _allow_element(any, (func1, func2)):
            raise ValidationErrors('one True, one False', errors)

        with self.assertRaises(ValidationErrors) as cm:
            with _allow_element(any, (func2, func2)):
                raise ValidationErrors('none True', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), errors)

    def test_dict_of_errors(self):
        errors =  {'a': Missing2('X'), 'b': Missing2('Y')}  # <- Each value
        func1 = lambda x: True                              #    is a single
        func2 = lambda x: False                             #    error.

        with _allow_element(any, (func1,)):
            raise ValidationErrors('one True', errors)

        with _allow_element(any, (func1, func2)):
            raise ValidationErrors('one True, one False', errors)

        with self.assertRaises(ValidationErrors) as cm:
            with _allow_element(any, (func2, func2)):
                raise ValidationErrors('none True', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(dict(remaining_errors), errors)

    def test_dict_of_lists(self):
        errors =  {'a': [Missing2('X'), Missing2('Y')]}  # <- Value is a list
        func1 = lambda x: isinstance(x, DataError2)      #    of errors.
        func2 = lambda x: x.args[0] == 'Z'

        with _allow_element(any, (func1,)):
            raise ValidationErrors('one True', errors)

        with _allow_element(any, (func1, func2)):
            raise ValidationErrors('one True, one False', errors)

        with self.assertRaises(ValidationErrors) as cm:
            with _allow_element(any, (func2, func2)):
                raise ValidationErrors('none True', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(dict(remaining_errors), errors)


class TestAllowAny_and_AllowAll(unittest.TestCase):
    def test_allow_any(self):
        errors =  [Missing2('X'), Missing2('Y'), Extra2('Z')]
        func1 = lambda x: isinstance(x, Missing2)
        func2 = lambda x: x.args[0] == 'X'

        with self.assertRaises(ValidationErrors) as cm:
            with allow_any2(func1, func2):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra2('Z')])

    def test_allow_all(self):
        errors =  [Missing2('X'), Missing2('Y'), Extra2('Z')]
        func1 = lambda x: isinstance(x, Missing2)
        func2 = lambda x: x.args[0] == 'X'

        with self.assertRaises(ValidationErrors) as cm:
            with allow_all2(func1, func2):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing2('Y'), Extra2('Z')])


class TestAllowMissing_and_AllowExtra(unittest.TestCase):
    def test_allow_missing(self):
        errors =  [Missing2('X'), Missing2('Y'), Extra2('X')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_missing2():  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra2('X')])

        with self.assertRaises(ValidationErrors) as cm:
            func = lambda x: x.args[0] == 'X'
            with allow_missing2(func):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing2('Y'), Extra2('X')])

    def test_allow_extra(self):
        errors =  [Extra2('X'), Extra2('Y'), Missing2('X')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_extra2():  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing2('X')])

        with self.assertRaises(ValidationErrors) as cm:
            func = lambda x: x.args[0] == 'X'
            with allow_extra2(func):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra2('Y'), Missing2('X')])


class TestAllowDeviation2(unittest.TestCase):
    """Test allow_deviation() behavior."""
    def test_method_signature(self):
        """Check for prettified default signature in Python 3.3 and later."""
        try:
            sig = inspect.signature(allow_deviation2)
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'kwds_func'])
        except AttributeError:
            pass  # Python 3.2 and older use ugly signature as default.

    def test_tolerance_syntax(self):
        differences = {
            'aaa': Deviation2(-1, 10),
            'bbb': Deviation2(+3, 10),  # <- Not in allowed range.
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(2):  # <- Allows +/- 2.
                raise ValidationErrors('example error', differences)

        remaining_errors = cm.exception.errors
        self.assertEqual(remaining_errors, {'bbb': Deviation2(+3, 10)})

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation2(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation2(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(0, 3):  # <- Allows from 0 to 3.
                raise ValidationErrors('example error', differences)

        result_diffs = cm.exception.errors
        self.assertEqual({'aaa': Deviation2(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation2(+2.9, 10),  # <- Not allowed.
            Deviation2(+3.0, 10),
            Deviation2(+3.0, 5),
            Deviation2(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(3, 3):  # <- Allows +3 only.
                raise ValidationErrors('example error', differences)

        result_diffs = list(cm.exception.errors)
        expected_diffs = [
            Deviation2(+2.9, 10),
            Deviation2(+3.1, 10),
        ]
        self.assertEqual(expected_diffs, result_diffs)

    def test_getkey_decorator(self):
        with self.assertRaises(ValidationErrors) as cm:
            differences = {
                'aaa': Deviation2(-1, 10),
                'bbb': Deviation2(+2, 10),
                'ccc': Deviation2(+2, 10),
                'ddd': Deviation2(+3, 10),
            }
            @getkey
            def fn(key):
                return key in ('aaa', 'bbb', 'ddd')
            with allow_deviation2(2, fn):  # <- Allows +/- 2.
                raise ValidationErrors('example error', differences)

        actual = cm.exception.errors
        expected = {
            'ccc': Deviation2(+2, 10),  # <- Keyword value not allowed.
            'ddd': Deviation2(+3, 10),  # <- Not in allowed range.
        }
        self.assertEqual(expected, actual)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_deviation2(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(None, 0)])

        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(0, None)])

        # Test empty string.
        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2('', 0)])

        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_deviation2(0):
                raise ValidationErrors('example error', [Deviation2(float('nan'), 0)])

        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_deviation2(0):
                raise ValidationErrors('example error', [Deviation2(0, float('nan'))])

    # AN OPEN QUESTION: Should deviation allowances raise an error if
    # the maximum oberved deviation is _less_ than the given tolerance?


class TestAllowPercentDeviation2(unittest.TestCase):
    """Test allow_percent_deviation() behavior."""
    def test_method_signature(self):
        """Check for prettified default signature in Python 3.3 and later."""
        try:
            sig = inspect.signature(allow_percent_deviation2)
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'kwds_func'])
        except AttributeError:
            pass  # Python 3.2 and older use ugly signature as default.

    def test_tolerance_syntax(self):
        differences = [
            Deviation2(-1, 10),
            Deviation2(+3, 10),  # <- Not in allowed range.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.2):  # <- Allows +/- 20%.
                raise ValidationErrors('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = list(cm.exception.errors)
        self.assertEqual([Deviation2(+3, 10)], result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation2(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation2(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise ValidationErrors('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = cm.exception.errors
        self.assertEqual({'aaa': Deviation2(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        from decimal import Decimal
        differences = [
            Deviation2(+2.9, 10),  # <- Not allowed.
            Deviation2(+3.0, 10),
            Deviation2(+6.0, 20),
            Deviation2(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.3, 0.3):  # <- Allows +30% only.
                raise ValidationErrors('example error', differences)

        result_diffs = list(cm.exception.errors)
        expected_diffs = [
            Deviation2(+2.9, 10),
            Deviation2(+3.1, 10),
        ]
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = {
            'aaa': Deviation2(-1, 10),
            'bbb': Deviation2(+2, 10),
            'ccc': Deviation2(+2, 10),
            'ddd': Deviation2(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            fn = lambda x: x in ('aaa', 'bbb', 'ddd')
            fn = getkey(fn)
            with allow_percent_deviation2(0.2, fn):  # <- Allows +/- 20%.
                raise ValidationErrors('example error', differences)

        result_set = cm.exception.errors
        expected_set = {
            'ccc': Deviation2(+2, 10),  # <- Key value not 'aaa'.
            'ddd': Deviation2(+3, 10),  # <- Not in allowed range.
        }
        self.assertEqual(expected_set, result_set)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_percent_deviation2(-0.5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(None, 0)])

        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(0, None)])

        # Test empty string.
        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2('', 0)])

        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation2(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_percent_deviation2(0):
                raise ValidationErrors('example error', [Deviation2(float('nan'), 0)])

        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_percent_deviation2(0):
                raise ValidationErrors('example error', [Deviation2(0, float('nan'))])


class TestGetKeyDecorator(unittest.TestCase):
    def test_key_strings(self):
        @getkey  # <- Apply decorator!
        def func(key):
            return key == 'aa'

        self.assertTrue(func('aa', None))
        self.assertFalse(func('bb', None))

    def test_key_tuples(self):
        """Keys of non-string containers are unpacked before passing
        to function.
        """
        @getkey  # <- Apply decorator!
        def func(letter, number):  # <- Non-string iterable keys are unpacked.
            return letter == 'aa'

        self.assertTrue(func(('aa', 1), None))
        self.assertFalse(func(('bb', 2), None))


class TestAllowIter(unittest.TestCase):
    def test_iterable_all_bad(self):
        """Given a non-mapping iterable in which all items are invalid,
        *function* should return a non-mapping iterable containing all
        items.
        """
        function = lambda iterable: iterable  # <- Rejects everything.
        in_diffs = [xExtra('foo'), xExtra('bar')]

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
        in_diffs =  [xMissing('foo'), xMissing('bar')]

        with allow_iter(function):  # <- Passes without error.
            raise DataError('example error', in_diffs)

    def test_empty_generator(self):
        """If all items are valid, returning an empty generator or other
        iterable non-container should work, too.
        """
        function = lambda iterable: (x for x in [])  # <- Empty generator.
        in_diffs =  [xMissing('foo'), xMissing('bar')]

        with allow_iter(function):  # <- Passes without error.
            raise DataError('example error', in_diffs)

    def test_iterable_some_good(self):
        """Given a non-mapping iterable, *function* should return those
        items which are invalid and omit those items which are valid.
        """
        function = lambda iterable: (x for x in iterable if x.value != 'bar')
        in_diffs = [xMissing('foo'), xMissing('bar')]

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(list(out_diffs), [xMissing('foo')])

    def test_mapping_all_bad(self):
        """Given a mapping in which all items are invalid, *function*
        should return a mapping containing all items.
        """
        function = lambda mapping: mapping  # <- Rejects entire mapping.
        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}

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
        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}

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

        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}

        with self.assertRaises(DataError) as cm:
            with allow_iter(function):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, {('BBB', 'yyy'): xMissing('bar')})

    def test_returns_sequence(self):
        """If given a mapping, *function* may return an iterable of
        sequences (instead of a mapping).  Each sequence must contain
        exactly two objects---the first object will be use as the key
        and the second object will be used as the value (same as
        Python's 'dict' behavior).
        """
        # Simple key.
        in_diffs = {'AAA': xMissing('foo'),
                    'BBB': xMissing('bar')}
        return_val = [['AAA', xMissing('foo')],  # <- Two items.
                      ['BBB', xMissing('bar')]]  # <- Two items.

        with self.assertRaises(DataError) as cm:
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

        # Compound key.
        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}
        return_val = [[('AAA', 'xxx'), xMissing('foo')],  # <- Two items.
                      [('BBB', 'yyy'), xMissing('bar')]]  # <- Two items.

        with self.assertRaises(DataError) as cm:
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        out_diffs = cm.exception.differences
        self.assertEqual(out_diffs, in_diffs)

        # Duplicate keys--last defined value (bar) appears in mapping.
        in_diffs = {'AAA': xMissing('foo'),
                    'BBB': xMissing('bar')}
        return_val = [['AAA', xMissing('foo')],
                      ['BBB', xMissing('xxx')],  # <- Duplicate key.
                      ['BBB', xMissing('yyy')],  # <- Duplicate key.
                      ['BBB', xMissing('zzz')],  # <- Duplicate key.
                      ['BBB', xMissing('bar')]]  # <- Duplicate key.

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
        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}

        # mapping / iterable of 1-item sequences.
        return_val = [[xMissing('foo')],  # <- One item.
                      [xMissing('bar')]]  # <- One item.

        regex = ('has length 1.*2 is required')
        with self.assertRaisesRegex(ValueError, regex):  # <- ValueError!
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # mapping / iterable of 3-item sequences.
        return_val = [[('AAA', 'xxx'), xMissing('foo'), None],  # <- Three items.
                      [('BBB', 'yyy'), xMissing('bar'), None]]  # <- Three items.

        regex = 'has length 3.*2 is required'
        with self.assertRaisesRegex(ValueError, regex):  # <- ValueError!
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

    def test_returns_bad_type(self):
        """The *function* should return the same type it was given or a
        compatible object--if not, a TypeError should be raised.
        """
        in_diffs = {('AAA', 'xxx'): xMissing('foo'),
                    ('BBB', 'yyy'): xMissing('bar')}

        # mapping / iterable ot 2-char strings
        return_val = ['Ax', 'By']  # <- Two-character strings.

        regex = r"must be non-string sequence.*found 'str' instead"
        with self.assertRaisesRegex(TypeError, regex):
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # mapping / iterable of non-sequence items
        return_val = [xMissing('foo'),  # <- Non-sequence item.
                      xMissing('bar')]  # <- Non-sequence item.

        regex = ("must be non-string sequence.*found 'xMissing'")
        with self.assertRaisesRegex(TypeError, regex):
            with allow_iter(lambda x: return_val):
                raise DataError('example error', in_diffs)

        # nonmapping / mapping
        in_diffs = [xMissing('foo'), xMissing('bar')]  # <- List (non-mapping)!
        return_val = {'AAA': xMissing('foo'), 'BBB': xMissing('bar')}  # <- Mapping!

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
        in_diffs = [xMissing('foo'), xMissing('bar')]
        function = lambda x: x.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(diffs=function):  # <- Using diffs keyword!
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, [xMissing('bar')])

    def test_diffs_mapping(self):
        in_diffs = {'AAA': xMissing('foo'), 'BBB': xMissing('bar')}
        function = lambda x: x.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(diffs=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': xMissing('bar')})

    def test_keys_nonmapping(self):
        # xMissing required keyword 'diffs'.
        in_diffs = [xMissing('foo'), xMissing('bar')]
        function = lambda first, second: first == 'AAA'

        regex = "accepts only 'diffs' keyword, found 'keys'"
        with self.assertRaisesRegex(ValueError, regex):
            with allow_any(keys=function):  # <- expects 'diffs='.
                raise DataError('example error', in_diffs)

        # Disallowed keywords ('keys').
        in_diffs = [xMissing('foo'), xMissing('bar')]
        function = lambda first, second: first == 'AAA'

        with self.assertRaisesRegex(ValueError, "found 'keys'"):
            with allow_any(diffs=function, keys=function):  # <- 'keys=' not allowed.
                raise DataError('example error', in_diffs)

    def test_keys_mapping(self):
        # Function accepts single argument.
        in_diffs = {'AAA': xMissing('foo'), 'BBB': xMissing('bar')}
        function = lambda x: x == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': xMissing('bar')})

        # Function accepts multiple arguments.
        in_diffs = {('AAA', 'XXX'): xMissing('foo'),
                    ('BBB', 'YYY'): xMissing('bar')}

        def function(first, second):  # <- Multiple args.
            return second == 'XXX'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): xMissing('bar')})

    def test_items_nonmapping(self):
        # TODO: Explore the idea of accepting mapping-compatible
        # iterator of items.
        pass

    def test_items_mapping(self):
        # Function of one argument.
        in_diffs = {'AAA': xMissing('foo'), 'BBB': xMissing('bar')}

        def function(item):
            key, diff = item  # Unpack item tuple.
            return key == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': xMissing('bar')})

        # Function of two arguments.
        in_diffs = {'AAA': xMissing('foo'), 'BBB': xMissing('bar')}

        def function(key, diff):
            return key == 'AAA'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'BBB': xMissing('bar')})

        # Function of three arguments.
        in_diffs = {('AAA', 'XXX'): xMissing('foo'),
                    ('BBB', 'YYY'): xMissing('bar')}

        def function(key1, key2, diff):
            return key2 == 'XXX'

        with self.assertRaises(DataError) as cm:
            with allow_any(items=function):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): xMissing('bar')})

    def test_keyword_combinations(self):
        in_diffs = {('AAA', 'XXX'): xMissing('foo'),
                    ('BBB', 'YYY'): xMissing('foo'),
                    ('CCC', 'XXX'): xExtra('bar'),
                    ('DDD', 'XXX'): xMissing('foo')}

        def fn1(key1, key2):
            return key2 == 'XXX'

        def fn2(diff):
            return diff.value == 'foo'

        with self.assertRaises(DataError) as cm:
            with allow_any(keys=fn1, diffs=fn2):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {('BBB', 'YYY'): xMissing('foo'),
                                    ('CCC', 'XXX'): xExtra('bar')})


class TestAllowMissing(unittest.TestCase):
    """Test allow_missing() behavior."""
    def test_allow_some(self):
        differences = [xExtra('xxx'), xMissing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_missing():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [xExtra('xxx')])

    def test_allow_all(self):
        with allow_missing():
            raise DataError('example error', [xMissing('xxx'), xMissing('yyy')])

    def test_diffs_keyword(self):
        in_diffs = {
            'foo': xMissing('xxx'),
            'bar': xMissing('yyy'),
            'baz': xExtra('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x.value in ('yyy', 'zzz')

            with allow_missing(diffs=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'foo': xMissing('xxx'), 'baz': xExtra('zzz')})

    def test_keys_keyword(self):
        in_diffs = {
            'foo': xMissing('xxx'),
            'bar': xMissing('yyy'),
            'baz': xExtra('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x in ('foo', 'baz')

            with allow_missing(keys=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'bar': xMissing('yyy'), 'baz': xExtra('zzz')})

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_missing():
                pass  # No exception raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_missing', str(exc))


class TestAllowExtra(unittest.TestCase):
    """Test allow_extra() behavior."""
    def test_allow_some(self):
        differences = [xExtra('xxx'), xMissing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_extra():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [xMissing('yyy')])

    def test_allow_all(self):
        with allow_extra():
            raise DataError('example error', [xExtra('xxx'), xExtra('yyy')])

    def test_diffs_keyword(self):
        in_diffs = {
            'foo': xExtra('xxx'),
            'bar': xExtra('yyy'),
            'baz': xMissing('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x.value in ('yyy', 'zzz')

            with allow_extra(diffs=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'foo': xExtra('xxx'), 'baz': xMissing('zzz')})

    def test_keys_keyword(self):
        in_diffs = {
            'foo': xExtra('xxx'),
            'bar': xExtra('yyy'),
            'baz': xMissing('zzz'),
        }
        with self.assertRaises(DataError) as cm:
            def additional_helper(x):
                return x in ('foo', 'baz')

            with allow_extra(keys=additional_helper):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, {'bar': xExtra('yyy'), 'baz': xMissing('zzz')})

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
            'aaa': xDeviation(-1, 10),
            'bbb': xDeviation(+3, 10),  # <- Not in allowed range.
        }
        with self.assertRaises(DataError) as cm:
            with allow_deviation(2):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        #result_string = str(cm.exception)
        #self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'bbb': xDeviation(+3, 10)}, result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': xDeviation(-1, 10),  # <- Not in allowed range.
            'bbb': xDeviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            with allow_deviation(0, 3):  # <- Allows from 0 to 3.
                raise DataError('example error', differences)

        #result_string = str(cm.exception)
        #self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': xDeviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            xDeviation(+2.9, 10),  # <- Not allowed.
            xDeviation(+3.0, 10),
            xDeviation(+3.0, 5),
            xDeviation(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(3, 3):  # <- Allows +3 only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            xDeviation(+2.9, 10),
            xDeviation(+3.1, 10),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_keys_keyword(self):
        with self.assertRaises(DataError) as cm:
            differences = {
                'aaa': xDeviation(-1, 10),
                'bbb': xDeviation(+2, 10),
                'ccc': xDeviation(+2, 10),
                'ddd': xDeviation(+3, 10),
            }
            fn = lambda key: key in ('aaa', 'bbb', 'ddd')
            with allow_deviation(2, keys=fn):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        actual = cm.exception.differences
        expected = {
            'ccc': xDeviation(+2, 10),  # <- Keyword value not allowed.
            'ddd': xDeviation(+3, 10),  # <- Not in allowed range.
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
            raise DataError('example error', [xDeviation(None, 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation(0, None)])

        # Test empty string.
        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation('', 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [xDeviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [xDeviation(0, float('nan'))])

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
            xDeviation(-1, 10),
            xDeviation(+3, 10),  # <- Not in allowed range.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.2):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([xDeviation(+3, 10)], result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': xDeviation(-1, 10),  # <- Not in allowed range.
            'bbb': xDeviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': xDeviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            xDeviation(+2.9, 10, label='aaa'),  # <- Not allowed.
            xDeviation(+3.0, 10, label='bbb'),
            xDeviation(+6.0, 20, label='ccc'),
            xDeviation(+3.1, 10, label='ddd'),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.3, 0.3):  # <- Allows +30% only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            xDeviation(+2.9, 10, label='aaa'),
            xDeviation(+3.1, 10, label='ddd'),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = {
            'aaa': xDeviation(-1, 10),
            'bbb': xDeviation(+2, 10),
            'ccc': xDeviation(+2, 10),
            'ddd': xDeviation(+3, 10),
        }
        with self.assertRaises(DataError) as cm:
            fn = lambda x: x in ('aaa', 'bbb', 'ddd')
            with allow_percent_deviation(0.2, keys=fn):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_set = cm.exception.differences
        expected_set = {
            'ccc': xDeviation(+2, 10),  # <- Key value not 'aaa'.
            'ddd': xDeviation(+3, 10),  # <- Not in allowed range.
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
            raise DataError('example error', [xDeviation(None, 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation(0, None)])

        # Test empty string.
        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation('', 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [xDeviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [xDeviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [xDeviation(0, float('nan'))])


class TestAllowLimit(unittest.TestCase):
    """Test allow_limit() behavior."""
    def test_exceeds_limit(self):
        differences = [xExtra('xxx'), xMissing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_limit(1):  # <- Allows only 1 but there are 2!
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(differences, rejected)

    def test_matches_limit(self):
        with allow_limit(2):  # <- Allows 2 and there are only 2.
            raise DataError('example error', [xMissing('xxx'), xMissing('yyy')])

    def test_under_limit(self):
        with allow_limit(3):  # <- Allows 3 and there are only 2.
            raise DataError('example error', [xMissing('xxx'), xMissing('yyy')])

    def test_kwds_exceeds_limit(self):
        differences = [xExtra('xxx'), xMissing('yyy'), xExtra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, xExtra)
            with allow_limit(1, diffs=is_extra):  # <- Limit of 1 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(differences, rejected)

    def test_kwds_matches_limit(self):
        differences = [xExtra('xxx'), xMissing('yyy'), xExtra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, xExtra)
            with allow_limit(2, diffs=is_extra):  # <- Limit of 2 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual([xMissing('yyy')], rejected)

    def test_kwds_under_limit(self):
        differences = [xExtra('xxx'), xMissing('yyy'), xExtra('zzz')]

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, xExtra)
            with allow_limit(4, diffs=is_extra):  # <- Limit of 4 and is_extra().
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual([xMissing('yyy')], rejected)

    def test_dict_of_diffs_exceeds(self):
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}

        with self.assertRaises(DataError) as cm:
            with allow_limit(1):  # <- Allows only 1 but there are 2!
                raise DataError('example error', differences)

        rejected = cm.exception.differences
        self.assertEqual(differences, rejected)

    def test_dict_of_diffs_kwds_func_under_limit(self):
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}

        with self.assertRaises(DataError) as cm:
            is_extra = lambda x: isinstance(x, xExtra)
            with allow_limit(2, diffs=is_extra):
                raise DataError('example error', differences)

        rejected = cm.exception.differences
        self.assertEqual({'bar': xMissing('yyy')}, rejected)


class TestAllowOnly(unittest.TestCase):
    """Test allow_only() behavior."""
    def test_some_allowed(self):
        differences = [xExtra('xxx'), xMissing('yyy')]
        allowed = [xExtra('xxx')]

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [xMissing('yyy')]
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

    def test_single_diff_without_container(self):
        differences = [xExtra('xxx'), xMissing('yyy')]
        allowed = xExtra('xxx')  # <- Single diff, not in list.

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [xMissing('yyy')]
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

    def test_all_allowed(self):
        diffs = [xExtra('xxx'), xMissing('yyy')]
        allowed = [xExtra('xxx'), xMissing('yyy')]
        with allow_only(allowed):
            raise DataError('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        differences = [xExtra('xxx'), xExtra('xxx'), xExtra('xxx')]

        # Only allow one of them.
        with self.assertRaises(DataError) as cm:
            allowed = [xExtra('xxx')]
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [xExtra('xxx'), xExtra('xxx')]  # Expect two remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Only allow two of them.
        with self.assertRaises(DataError) as cm:
            allowed = [xExtra('xxx'), xExtra('xxx')]
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = [xExtra('xxx')]  # Expect one remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Allow all three.
        allowed = [xExtra('xxx'), xExtra('xxx'), xExtra('xxx')]
        with allow_only(allowed):
            raise DataError('example error', differences)

    def test_mapping_some_allowed(self):
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}
        allowed = {'foo': xExtra('xxx')}

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        expected = {'bar': xMissing('yyy')}
        actual = cm.exception.differences
        self.assertEqual(expected, actual)

    def test_mapping_none_allowed(self):
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}
        allowed = {}

        with self.assertRaises(DataError) as cm:
            with allow_only(allowed):
                raise DataError('example error', differences)

        actual = cm.exception.differences
        self.assertEqual(differences, actual)

    def test_mapping_all_allowed(self):
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}
        allowed = differences

        with allow_only(allowed):  # <- Catches all differences, no error!
            raise DataError('example error', differences)

    def test_mapping_mismatched_types(self):
        # Dict of diffs vs list of allowed.
        differences = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}
        allowed = [xExtra('xxx'), xMissing('yyy')]

        regex = ("expects non-mapping differences but found 'dict' of "
                 "differences")
        with self.assertRaisesRegex(ValueError, regex):
            with allow_only(allowed):
                raise DataError('example error', differences)

        # List of diffs vs dict of allowed.
        differences = [xExtra('xxx'), xMissing('yyy')]
        allowed = {'foo': xExtra('xxx'), 'bar': xMissing('yyy')}

        regex = ("expects mapping of differences but found 'list' of "
                 "differences")
        with self.assertRaisesRegex(ValueError, regex):
            with allow_only(allowed):
                raise DataError('example error', differences)
