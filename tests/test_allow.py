# -*- coding: utf-8 -*-
import inspect
from . import _unittest as unittest
from datatest.utils import collections
from datatest.dataaccess import ItemsIter

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
from datatest.errors import DataError
from datatest.errors import Missing
from datatest.errors import Extra
from datatest.errors import Deviation


class TestAllowIter2(unittest.TestCase):
    def test_iterable_all_good(self):
        function = lambda iterable: list()  # <- empty list
        with allow_iter2(function):  # <- Should pass without error.
            raise ValidationErrors('example error', [Missing('x')])

        function = lambda iterable: iter([])  # <- empty iterator
        with allow_iter2(function):  # <- Should pass pass without error.
            raise ValidationErrors('example error', [Missing('x')])

    def test_iterable_some_bad(self):
        function = lambda iterable: [Missing('foo')]
        in_diffs = [Missing('foo'), Missing('bar')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_iter2(function):
                raise ValidationErrors('example error', in_diffs)

        errors = cm.exception.errors
        self.assertEqual(list(errors), [Missing('foo')])

    def test_mismatched_types(self):
        """When given a non-mapping container, a non-mapping container
        should be returned for any remaining errors. Likewise, when
        given a mapping, a mapping should be returned for any remaining
        errors. If the intput and output types are mismatched, a
        TypeError should be raised.
        """
        # List input and dict output.
        errors_list =  [Missing('foo'), Missing('bar')]
        function = lambda iterable: {'a': Missing('foo')}  # <- dict type
        with self.assertRaises(TypeError):
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_list)

        # Dict input and list output.
        errors_dict =  {'a': Missing('foo'), 'b': Missing('bar')}
        function = lambda iterable: [Missing('foo')]  # <- list type
        with self.assertRaises(TypeError):
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_dict)

        # Dict input and list-item output.
        errors_dict =  {'a': Missing('foo'), 'b': Missing('bar')}
        function = lambda iterable: [('a', Missing('foo'))]  # <- list of items
        with self.assertRaises(ValidationErrors) as cm:
            with allow_iter2(function):
                raise ValidationErrors('example error', errors_dict)

        errors = cm.exception.errors
        #self.assertIsInstance(errors, DictItems)
        self.assertEqual(dict(errors), {'a': Missing('foo')})


class TestAllowSpecified2(unittest.TestCase):
    def test_some_allowed(self):
        errors = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Missing('yyy')]
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

    def test_single_diff_without_container(self):
        errors = [Extra('xxx'), Missing('yyy')]
        allowed = Extra('xxx')  # <- Single diff, not in list.

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Missing('yyy')]
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

    def test_all_allowed(self):
        diffs = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx'), Missing('yyy')]
        with allow_specified2(allowed):
            raise ValidationErrors('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        errors = [Extra('xxx'), Extra('xxx'), Extra('xxx')]

        # Only allow one of them.
        with self.assertRaises(ValidationErrors) as cm:
            allowed = [Extra('xxx')]
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Extra('xxx'), Extra('xxx')]  # Expect two remaining.
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

        # Only allow two of them.
        with self.assertRaises(ValidationErrors) as cm:
            allowed = [Extra('xxx'), Extra('xxx')]
            with allow_specified2(allowed):
                raise ValidationErrors('example error', errors)

        expected = [Extra('xxx')]  # Expect one remaining.
        actual = list(cm.exception.errors)
        self.assertEqual(expected, actual)

        # Allow all three.
        allowed = [Extra('xxx'), Extra('xxx'), Extra('xxx')]
        with allow_specified2(allowed):
            raise ValidationErrors('example error', errors)

    def test_error_mapping_allowance_list(self):
        differences = {'foo': [Extra('xxx')], 'bar': [Extra('xxx'), Missing('yyy')]}
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        expected = {'bar': [Missing('yyy')]}
        actual = cm.exception.errors
        self.assertEqual(expected, actual)

    def test_mapping_some_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {'foo': Extra('xxx')}

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        expected = {'bar': Missing('yyy')}
        actual = cm.exception.errors
        self.assertEqual(expected, actual)

    def test_mapping_none_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {}

        with self.assertRaises(ValidationErrors) as cm:
            with allow_specified2(allowed):
                raise ValidationErrors('example error', differences)

        actual = cm.exception.errors
        self.assertEqual(differences, actual)

    def test_mapping_all_allowed(self):
        errors = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = errors

        with allow_specified2(allowed):  # <- Catches all differences, no error!
            raise ValidationErrors('example error', errors)

    def test_mapping_mismatched_types(self):
        error_list = [Extra('xxx'), Missing('yyy')]
        allowed_dict = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        regex = "'list' of errors cannot be matched.*requires non-mapping type"
        with self.assertRaisesRegex(ValueError, regex):
            with allow_specified2(allowed_dict):
                raise ValidationErrors('example error', error_list)

    def test_integration(self):
        """This is a bit of an integration test."""
        differences = {'foo': Extra('xxx'), 'bar': Missing('zzz')}
        allowed = [Extra('xxx'), Missing('yyy')]

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
        self.assertEqual(actual['bar'][0], Missing('zzz'))
        self.assertEqual(
            actual['bar'][1].args[0],
            "allowed errors not found: [Extra('xxx'), Missing('yyy')]"
        )


class TestAllowLimit2(unittest.TestCase):
    """Test allow_limit() behavior."""
    def test_exceeds_limit(self):
        errors = [Extra('xxx'), Missing('yyy')]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_limit2(1):  # <- Allows only 1 but there are 2!
                raise ValidationErrors('example error', errors)

        remaining = list(cm.exception.errors)
        self.assertEqual(remaining, errors)

    def test_matches_limit(self):
        errors = [Extra('xxx'), Missing('yyy')]
        with allow_limit2(2):  # <- Allows 2 and there are only 2.
            raise ValidationErrors('example error', errors)

    def test_under_limit(self):
        errors = [Extra('xxx'), Missing('yyy')]
        with allow_limit2(3):  # <- Allows 3 and there are only 2.
            raise ValidationErrors('example error', errors)

    def test_function_exceeds_limit(self):
        errors = [Extra('xxx'), Missing('yyy'), Extra('zzz')]
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit2(1, is_extra):  # <- Limit of 1 and is_extra().
                raise ValidationErrors('example error', errors)

        # Returned errors can be in different order.
        actual = list(cm.exception.errors)
        expected = [Missing('yyy'), Extra('xxx'), Extra('zzz')]
        self.assertEqual(actual, expected)

    def test_function_under_limit(self):
        errors = [Extra('xxx'), Missing('yyy'), Extra('zzz')]
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit2(4, is_extra):  # <- Limit of 4 and is_extra().
                raise ValidationErrors('example error', errors)

        actual = list(cm.exception.errors)
        self.assertEqual(actual, [Missing('yyy')])

    def test_dict_of_diffs_exceeds_and_match(self):
        errors = {
            'foo': [Extra('xxx'), Missing('yyy')],
            'bar': [Extra('zzz')],
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_limit2(1):  # <- Allows only 1 but there are 2!
                raise ValidationErrors('example error', errors)

        actual = cm.exception.errors
        expected = {'foo': [Extra('xxx'), Missing('yyy')]}
        self.assertEqual(dict(actual), expected)

    def test_dict_of_diffs_and_function(self):
        errors = {
            'foo': [Extra('xxx'), Missing('yyy')],
            'bar': [Extra('zzz')],
        }
        with self.assertRaises(ValidationErrors) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allow_limit2(1, is_extra):
                raise ValidationErrors('example error', errors)

        actual = cm.exception.errors
        expected = {'foo': [Missing('yyy')]}
        self.assertEqual(dict(actual), expected)


class TestAllowElement(unittest.TestCase):
    def test_list_of_errors(self):
        errors =  [Missing('X'), Missing('Y')]
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
        errors =  {'a': Missing('X'), 'b': Missing('Y')}  # <- Each value
        func1 = lambda x: True                            #    is a single
        func2 = lambda x: False                           #    error.

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
        errors =  {'a': [Missing('X'), Missing('Y')]}  # <- Value is a list
        func1 = lambda x: isinstance(x, DataError)     #    of errors.
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
        errors =  [Missing('X'), Missing('Y'), Extra('Z')]
        func1 = lambda x: isinstance(x, Missing)
        func2 = lambda x: x.args[0] == 'X'

        with self.assertRaises(ValidationErrors) as cm:
            with allow_any2(func1, func2):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra('Z')])

    def test_allow_all(self):
        errors =  [Missing('X'), Missing('Y'), Extra('Z')]
        func1 = lambda x: isinstance(x, Missing)
        func2 = lambda x: x.args[0] == 'X'

        with self.assertRaises(ValidationErrors) as cm:
            with allow_all2(func1, func2):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing('Y'), Extra('Z')])


class TestAllowMissing_and_AllowExtra(unittest.TestCase):
    def test_allow_missing(self):
        errors =  [Missing('X'), Missing('Y'), Extra('X')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_missing2():  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra('X')])

        with self.assertRaises(ValidationErrors) as cm:
            func = lambda x: x.args[0] == 'X'
            with allow_missing2(func):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing('Y'), Extra('X')])

    def test_allow_extra(self):
        errors =  [Extra('X'), Extra('Y'), Missing('X')]

        with self.assertRaises(ValidationErrors) as cm:
            with allow_extra2():  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Missing('X')])

        with self.assertRaises(ValidationErrors) as cm:
            func = lambda x: x.args[0] == 'X'
            with allow_extra2(func):  # <- Apply allowance!
                raise ValidationErrors('some message', errors)
        remaining_errors = cm.exception.errors
        self.assertEqual(list(remaining_errors), [Extra('Y'), Missing('X')])


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
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+3, 10),  # <- Not in allowed range.
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(2):  # <- Allows +/- 2.
                raise ValidationErrors('example error', differences)

        remaining_errors = cm.exception.errors
        self.assertEqual(remaining_errors, {'bbb': Deviation(+3, 10)})

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(0, 3):  # <- Allows from 0 to 3.
                raise ValidationErrors('example error', differences)

        result_diffs = cm.exception.errors
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation(+2.9, 10),  # <- Not allowed.
            Deviation(+3.0, 10),
            Deviation(+3.0, 5),
            Deviation(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_deviation2(3, 3):  # <- Allows +3 only.
                raise ValidationErrors('example error', differences)

        result_diffs = list(cm.exception.errors)
        expected_diffs = [
            Deviation(+2.9, 10),
            Deviation(+3.1, 10),
        ]
        self.assertEqual(expected_diffs, result_diffs)

    def test_getkey_decorator(self):
        with self.assertRaises(ValidationErrors) as cm:
            differences = {
                'aaa': Deviation(-1, 10),
                'bbb': Deviation(+2, 10),
                'ccc': Deviation(+2, 10),
                'ddd': Deviation(+3, 10),
            }
            @getkey
            def fn(key):
                return key in ('aaa', 'bbb', 'ddd')
            with allow_deviation2(2, fn):  # <- Allows +/- 2.
                raise ValidationErrors('example error', differences)

        actual = cm.exception.errors
        expected = {
            'ccc': Deviation(+2, 10),  # <- Keyword value not allowed.
            'ddd': Deviation(+3, 10),  # <- Not in allowed range.
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
            raise ValidationErrors('example error', [Deviation(None, 0)])

        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation('', 0)])

        with allow_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_deviation2(0):
                raise ValidationErrors('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_deviation2(0):
                raise ValidationErrors('example error', [Deviation(0, float('nan'))])

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
            Deviation(-1, 10),
            Deviation(+3, 10),  # <- Not in allowed range.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.2):  # <- Allows +/- 20%.
                raise ValidationErrors('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = list(cm.exception.errors)
        self.assertEqual([Deviation(+3, 10)], result_diffs)

    def test_lowerupper_syntax(self):
        differences = {
            'aaa': Deviation(-1, 10),  # <- Not in allowed range.
            'bbb': Deviation(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise ValidationErrors('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example error'))

        result_diffs = cm.exception.errors
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_single_value_allowance(self):
        from decimal import Decimal
        differences = [
            Deviation(+2.9, 10),  # <- Not allowed.
            Deviation(+3.0, 10),
            Deviation(+6.0, 20),
            Deviation(+3.1, 10),  # <- Not allowed.
        ]
        with self.assertRaises(ValidationErrors) as cm:
            with allow_percent_deviation2(0.3, 0.3):  # <- Allows +30% only.
                raise ValidationErrors('example error', differences)

        result_diffs = list(cm.exception.errors)
        expected_diffs = [
            Deviation(+2.9, 10),
            Deviation(+3.1, 10),
        ]
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+2, 10),
            'ccc': Deviation(+2, 10),
            'ddd': Deviation(+3, 10),
        }
        with self.assertRaises(ValidationErrors) as cm:
            fn = lambda x: x in ('aaa', 'bbb', 'ddd')
            fn = getkey(fn)
            with allow_percent_deviation2(0.2, fn):  # <- Allows +/- 20%.
                raise ValidationErrors('example error', differences)

        result_set = cm.exception.errors
        expected_set = {
            'ccc': Deviation(+2, 10),  # <- Key value not 'aaa'.
            'ddd': Deviation(+3, 10),  # <- Not in allowed range.
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
            raise ValidationErrors('example error', [Deviation(None, 0)])

        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation('', 0)])

        with allow_percent_deviation2(0):  # <- Pass without failure.
            raise ValidationErrors('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_percent_deviation2(0):
                raise ValidationErrors('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(ValidationErrors):  # <- NaN values should not be caught!
            with allow_percent_deviation2(0):
                raise ValidationErrors('example error', [Deviation(0, float('nan'))])


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
