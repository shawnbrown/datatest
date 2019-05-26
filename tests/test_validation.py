"""Tests for validation and comparison functions."""
import textwrap
from . import _unittest as unittest
from datatest.differences import (
    BaseDifference,
    Missing,
    Extra,
    Invalid,
    Deviation,
)
from datatest._query.query import Query
from datatest._utils import IterItems

from datatest.validation import ValidationError
from datatest.validation import validate
from datatest.validation import valid


# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    def __init__(self, *args):
        self._args = args

    @property
    def args(self):
        return self._args


class TestValidationError(unittest.TestCase):
    def test_single_diff(self):
        single_diff = MinimalDifference('A')
        err = ValidationError(single_diff)
        self.assertEqual(err.differences, [single_diff])

    def test_list_of_diffs(self):
        diff_list = [MinimalDifference('A'), MinimalDifference('B')]

        err = ValidationError(diff_list)
        self.assertEqual(err.differences, diff_list)

    def test_iter_of_diffs(self):
        diff_list = [MinimalDifference('A'), MinimalDifference('B')]
        diff_iter = iter(diff_list)

        err = ValidationError(diff_iter)
        self.assertEqual(err.differences, diff_list, 'iterable should be converted to list')

    def test_dict_of_diffs(self):
        diff_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}

        err = ValidationError(diff_dict)
        self.assertEqual(err.differences, diff_dict)

    def test_dict_of_lists(self):
        diff_dict = {'a': [MinimalDifference('A')], 'b': [MinimalDifference('B')]}

        err = ValidationError(diff_dict)
        self.assertEqual(err.differences, diff_dict)

    def test_iteritems_of_diffs(self):
        diff_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}
        diff_items = ((k, v) for k, v in diff_dict.items())

        err = ValidationError(diff_items)
        self.assertEqual(err.differences, diff_dict)

    def test_dict_of_iters(self):
        dict_of_lists = {'a': [MinimalDifference('A')], 'b': [MinimalDifference('B')]}
        dict_of_iters = dict((k, iter(v)) for k, v in dict_of_lists.items())

        err = ValidationError(dict_of_iters)
        self.assertEqual(err.differences, dict_of_lists)

    def test_iteritems_of_iters(self):
        dict_of_lists = {'a': [MinimalDifference('A')], 'b': [MinimalDifference('B')]}
        iteritems_of_iters = ((k, iter(v)) for k, v in dict_of_lists.items())

        err = ValidationError(iteritems_of_iters)
        self.assertEqual(err.differences, dict_of_lists)

    def test_bad_args(self):
        with self.assertRaises(TypeError, msg='must be iterable'):
            bad_arg = object()
            ValidationError(bad_arg, 'invalid data')

    def test_str_method(self):
        # Assert basic format and trailing comma.
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        expected = """
            invalid data (1 difference): [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert without description.
        err = ValidationError([MinimalDifference('A')])  # <- No description!
        expected = """
            1 difference: [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert "no cacheing"--objects that inhereit from some
        # Exceptions can cache their str--but ValidationError should
        # not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        updated = textwrap.dedent("""
            changed (1 difference): [
                MinimalDifference('B'),
            ]
        """).strip()
        self.assertEqual(str(err), updated)

        # Assert dict format and trailing comma.
        err = ValidationError({'x': MinimalDifference('A'),
                               'y': MinimalDifference('B')},
                              'invalid data')
        regex = textwrap.dedent(r"""
            invalid data \(2 differences\): \{
                '[xy]': MinimalDifference\('[AB]'\),
                '[xy]': MinimalDifference\('[AB]'\),
            \}
        """).strip()
        self.assertRegex(str(err), regex)  # <- Using regex because dict order
                                           #    can not be assumed for Python
                                           #    versions 3.5 and earlier.

    def test_str_sorting(self):
        """Check that string shows differences sorted by arguments."""
        self.maxDiff = None

        # Check sorting of non-mapping container.
        err = ValidationError([MinimalDifference('Z', 'Z'),
                               MinimalDifference('Z'),
                               MinimalDifference(1, 'C'),
                               MinimalDifference('B', 'C'),
                               MinimalDifference('A'),
                               MinimalDifference(1.5),
                               MinimalDifference(True),
                               MinimalDifference(0),
                               MinimalDifference(None)])
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                MinimalDifference(1.5),
                MinimalDifference('A'),
                MinimalDifference('B', 'C'),
                MinimalDifference('Z'),
                MinimalDifference('Z', 'Z'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Make sure that all differences are being sorted (not just
        # those being displayed).
        err._should_truncate = lambda lines, chars: lines > 4
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                ...
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Check sorting of non-mapping container.
        err = ValidationError(
            {
                ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
                ('A', 'C'): MinimalDifference('A'),
                'A': [MinimalDifference('C'), MinimalDifference(1)],
                2: [MinimalDifference('B'), MinimalDifference('A')],
                1: MinimalDifference('A'),
                (None, 4): MinimalDifference('A'),
            },
            'description string'
        )
        expected = """
            description string (6 differences): {
                1: MinimalDifference('A'),
                2: [MinimalDifference('A'), MinimalDifference('B')],
                'A': [MinimalDifference(1), MinimalDifference('C')],
                (None, 4): MinimalDifference('A'),
                ('A', 'C'): MinimalDifference('A'),
                ('C', 3): [MinimalDifference(1, 2), MinimalDifference('Z', 3)],
            }
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

    def test_str_no_sorting(self):
        """Check that string does not sort when _sorted_str is False."""
        self.maxDiff = None

        # Check no sorting of non-mapping container.
        err = ValidationError([MinimalDifference('Z', 'Z'),
                               MinimalDifference('Z'),
                               MinimalDifference(1, 'C'),
                               MinimalDifference('B', 'C'),
                               MinimalDifference('A'),
                               MinimalDifference(1.5),
                               MinimalDifference(True),
                               MinimalDifference(0),
                               MinimalDifference(None)])

        err._sorted_str = False  # <- Turn-off sorting!

        expected = """
            9 differences: [
                MinimalDifference('Z', 'Z'),
                MinimalDifference('Z'),
                MinimalDifference(1, 'C'),
                MinimalDifference('B', 'C'),
                MinimalDifference('A'),
                MinimalDifference(1.5),
                MinimalDifference(True),
                MinimalDifference(0),
                MinimalDifference(None),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Check sorted dict keys but unsorted value containers.
        err = ValidationError(
            {
                ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
                ('A', 'C'): MinimalDifference('A'),
                'A': [MinimalDifference('C'), MinimalDifference(1)],
                2: [MinimalDifference('B'), MinimalDifference('A')],
                1: MinimalDifference('A'),
                (None, 4): MinimalDifference('A'),
            },
            'description string'
        )

        err._sorted_str = False  # <- Turn-off sorting!

        expected = """
            description string (6 differences): {
                1: MinimalDifference('A'),
                2: [MinimalDifference('B'), MinimalDifference('A')],
                'A': [MinimalDifference('C'), MinimalDifference(1)],
                (None, 4): MinimalDifference('A'),
                ('A', 'C'): MinimalDifference('A'),
                ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
            }
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

    def test_str_truncation(self):
        # Assert optional truncation behavior.
        err = ValidationError([MinimalDifference('A'),
                               MinimalDifference('B'),
                               MinimalDifference('C'),],
                              'invalid data')
        self.assertIsNone(err._should_truncate)
        self.assertIsNone(err._truncation_notice)
        no_truncation = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                MinimalDifference('B'),
                MinimalDifference('C'),
            ]
        """
        no_truncation = textwrap.dedent(no_truncation).strip()
        self.assertEqual(str(err), no_truncation)

        # Truncate without notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = None
        truncation_witout_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...
        """
        truncation_witout_notice = textwrap.dedent(truncation_witout_notice).strip()
        self.assertEqual(str(err), truncation_witout_notice)

        # Truncate and use truncation notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = 'Message truncated.'
        truncation_plus_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...

            Message truncated.
        """
        truncation_plus_notice = textwrap.dedent(truncation_plus_notice).strip()
        self.assertEqual(str(err), truncation_plus_notice)

    def test_repr(self):
        err = ValidationError([MinimalDifference('A')])  # <- No description.
        expected = "ValidationError([MinimalDifference('A')])"
        self.assertEqual(repr(err), expected)

        err = ValidationError([MinimalDifference('A')], 'description string')
        expected = "ValidationError([MinimalDifference('A')], 'description string')"
        self.assertEqual(repr(err), expected)

        # Objects that inhereit from some Exceptions can cache their
        # repr--but ValidationError should not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        self.assertNotEqual(repr(err), expected, 'exception should not cache repr')

        updated = "ValidationError([MinimalDifference('B')], 'changed')"
        self.assertEqual(repr(err), updated)

    def test_module_property(self):
        """Module property should be 'datatest' so that testing
        frameworks display the error as 'datatest.ValidationError'.

        By default, instances would be displayed as
        'datatest.validation.ValidationError' but this awkwardly
        long and the submodule name--'validation'--is not needed
        because the class is imported into datatest's root namespace.
        """
        import datatest
        msg = "should be in datatest's root namespace"
        self.assertIs(ValidationError, datatest.ValidationError)

        msg = "should be set to 'datatest' to shorten display name"
        self.assertEqual('datatest', ValidationError.__module__)

    def test_args(self):
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        self.assertEqual(err.args, ([MinimalDifference('A')], 'invalid data'))

        err = ValidationError([MinimalDifference('A')])
        self.assertEqual(err.args, ([MinimalDifference('A')], None))


class TestValidationIntegration(unittest.TestCase):
    def test_valid(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertTrue(valid(a, a))

        self.assertFalse(valid(a, b))

    def test_validate(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertIsNone(validate(a, a))

        with self.assertRaises(ValidationError):
            validate(a, b)


class TestValidate(unittest.TestCase):
    """An integration test to check behavior of validate() function."""
    def test_required_vs_data_passing(self):
        """Single requirement to BaseElement or non-mapping
        container of data.
        """
        data = ('abc', 1)  # A single base element.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

        data = [('abc', 1), ('abc', 2)]  # Non-mapping container of base elements.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

    def test_required_vs_data_failing(self):
        """Apply single requirement to BaseElement or non-mapping
        container of data.
        """
        with self.assertRaises(ValidationError) as cm:
            data = ('abc', 1.0)  # A single base element.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0))])

        with self.assertRaises(ValidationError) as cm:
            data = [('abc', 1.0), ('xyz', 2)]  # Non-mapping container of base elements.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0)), Invalid(('xyz', 2))])

    def test_required_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2)}  # Mapping of base-elements.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

        data = {'a': [1, 2], 'b': [3, 4]}  # Mapping of containers.
        requirement = int
        self.assertIsNone(validate(data, requirement))

    def test_required_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2)}  # Mapping of base-elements.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': Invalid(('abc', 1.0)), 'b': Invalid(('xyz', 2))})

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [1, 2.0], 'b': [3.0, 4]}  # Mapping of containers.
            validate(data, int)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': [Invalid(2.0)], 'b': [Invalid(3.0)]})

    def test_mapping_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2.0)}  # Mapping of base-elements.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate(data, requirement))

        data = {'a': [('abc', 1), ('abc', 2)],
                'b': [('abc', 1.0), ('abc', 2.0)]}  # Mapping of containers.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate(data, requirement))

    def test_mapping_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2.0)}  # Mapping of base-elements.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': Invalid(('abc', 1.0), ('abc', int)),
            'b': Invalid(('xyz', 2.0), ('abc', float)),
        }
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [('abc', 1.0), ('abc', 2)],
                    'b': [('abc', 1.0), ('xyz', 2.0)]}  # Mapping of containers.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': [Invalid(('abc', 1.0))],
            'b': [Invalid(('xyz', 2.0))],
        }
        self.assertEqual(actual, expected)

    def test_predicate_method(self):
        data = {'A': 'aaa', 'B': [1, 2, 3], 'C': ('a', 1)}
        requirement = Query.from_object({'A': set(['aaa', 'bbb']), 'B': int, 'C': ('a', 1)})
        validate.predicate(data, requirement)

        with self.assertRaises(ValidationError) as cm:
            data = {'A': 'aaa', 'B': [1, 2, 3.5], 'C': ('b', 2)}
            requirement = Query.from_object({'A': set(['aaa', 'bbb']), 'B': int, 'C': ('a', 1)})
            validate.predicate(data, requirement)
        actual = cm.exception.differences
        expected = {
            'B': [Invalid(3.5)],
            'C': Invalid(('b', 2), expected=('a', 1)),
        }
        self.assertEqual(actual, expected)

    def test_approx_method(self):
        data = {'A': 5.00000001, 'B': 10.00000001}
        requirement = Query.from_object({'A': 5, 'B': 10})
        validate.approx(data, requirement)

        data = [5.00000001, 10.00000001]
        requirement = Query.from_object([5, 10])
        validate.approx(data, requirement)

        data = {'A': [5.00000001, 10.00000001], 'B': [5.00000001, 10.00000001]}
        requirement = Query.from_object({'A': [5, 10], 'B': [5, 10]})
        validate.approx(data, requirement)

        with self.assertRaises(ValidationError) as cm:
            data = {'A': 3, 'B': 10.00000001}
            requirement = {'A': 5, 'B': 10}
            validate.approx(data, requirement)
        actual = cm.exception.differences
        expected = {'A': Deviation(-2, 5)}
        self.assertEqual(actual, expected)

    def test_fuzzy_method(self):
        data = {'A': 'aaa', 'B': 'bbx'}
        requirement = Query.from_object({'A': 'aaa', 'B': 'bbb'})
        validate.fuzzy(data, requirement)

        with self.assertRaises(ValidationError) as cm:
            data = {'A': 'axx', 'B': 'bbx'}
            requirement = Query.from_object({'A': 'aaa', 'B': 'bbb'})
            validate.fuzzy(data, requirement)
        actual = cm.exception.differences
        expected = {'A': Invalid('axx', expected='aaa')}
        self.assertEqual(actual, expected)

    def test_interval_method(self):
        data = {'A': 5, 'B': 7, 'C': 9}
        validate.interval(data, 5, 10)

        data = [5, 7, 9]
        validate.interval(data, 5, 10)

        data = {'A': [7, 8, 9], 'B': [5, 6]}
        validate.interval(data, 5, 10)

        with self.assertRaises(ValidationError) as cm:
            data = {'A': 3, 'B': 6, 'C': [6, 7], 'D': [9, 10]}
            validate.interval(data, 5, 9)
        actual = cm.exception.differences
        expected = {'A': Deviation(-2, 5), 'D': [Deviation(+1, 9)]}
        self.assertEqual(actual, expected)

    def test_set_method(self):
        data = [1, 2, 3, 4]
        requirement = Query.from_object([1, 2, 3, 4])
        validate.set(data, requirement)

        with self.assertRaises(ValidationError) as cm:
            data = [1, 2, 3, 5]
            requirement = set([1, 2, 3, 4])
            validate.set(data, requirement)
        actual = cm.exception.differences
        expected = [Missing(4), Extra(5)]
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data ={'A': [1, 2, 3], 'B': [3]}
            requirement = {'A': iter([1, 2]), 'B': iter([3, 4])}
            validate.set(data, requirement)
        actual = cm.exception.differences
        expected = {'A': [Extra(3)], 'B': [Missing(4)]}
        self.assertEqual(actual, expected)

    def test_subset_method(self):
        data = [1, 2, 3, 4]
        subset = Query.from_object([1, 2, 3])
        validate.subset(data, subset)

        with self.assertRaises(ValidationError) as cm:
            data = [1, 2, 3]
            subset = set([1, 2, 3, 4])
            validate.subset(data, subset)
        actual = cm.exception.differences
        expected = [Missing(4)]
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data ={'A': [1, 2, 3], 'B': [3, 4, 5]}
            subset = {'A': iter([1, 2]), 'B': iter([2, 3])}
            validate.subset(data, subset)
        actual = cm.exception.differences
        expected = {'B': [Missing(2)]}
        self.assertEqual(actual, expected)

    def test_superset_method(self):
        data = [1, 2, 3]
        superset = Query.from_object([1, 2, 3, 4])
        validate.superset(data, superset)

        with self.assertRaises(ValidationError) as cm:
            data = {'A': [1, 2, 3], 'B': [3, 4, 5]}
            superset = {'A': set([1, 2, 3]), 'B': set([2, 3, 4])}
            validate.superset(data, superset)
        actual = cm.exception.differences
        expected = {'B': [Extra(5)]}
        self.assertEqual(actual, expected)

    def test_unique_method(self):
        validate.unique([1, 2, 3, 4])

        with self.assertRaises(ValidationError) as cm:
            validate.unique([1, 2, 3, 3])
        actual = cm.exception.differences
        expected = [Extra(3)]
        self.assertEqual(actual, expected)

    def test_order_method(self):
        data = ['A', 'B', 'C', 'C']
        requirement = iter(['A', 'B', 'C', 'C'])
        validate.order(data, requirement)

        data = ['A', 'B', 'C', 'D']
        requirement = Query.from_object(['A', 'B', 'C', 'D'])
        validate.order(data, requirement)

        with self.assertRaises(ValidationError) as cm:
            data = ['A', 'C', 'D', 'F']
            requirement = Query.from_object(iter(['A', 'B', 'C', 'D']))
            validate.order(data, requirement)
        actual = cm.exception.differences
        expected = [Missing((1, 'B')), Extra((3, 'F'))]
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data = {'x': ['A'], 'y': ['B', 'C', 'D']}
            requirement = Query.from_object({'x': ['A', 'B'], 'y': ['C', 'D']})
            validate.order(data, requirement)
        actual = cm.exception.differences
        expected = {'x': [Missing((1, 'B'))], 'y': [Extra((0, 'B'))]}
        self.assertEqual(actual, expected)
