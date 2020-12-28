# -*- coding: utf-8 -*-
from __future__ import absolute_import
import re
from . import _unittest as unittest
from datatest._compatibility.collections.abc import Iterable
from datatest._compatibility.collections.abc import Iterator
from datatest._utils import (
    exhaustible,
    nonstringiter,
    sortable,
)
from datatest import (
    Missing,
    Extra,
    Deviation,
    Invalid,
)
from datatest._vendor.predicate import Predicate
from datatest.requirements import (
    _build_description,

    # Abstract Requirement Classes
    BaseRequirement,
    ItemsRequirement,
    GroupRequirement,

    # Concrete Requirement Classes
    RequiredPredicate,
    RequiredRegex,
    RequiredApprox,
    RequiredFuzzy,
    RequiredInterval,
    RequiredSet,
    RequiredSubset,
    RequiredSuperset,
    RequiredUnique,
    RequiredOrder,
    RequiredSequence,
    RequiredMapping,

    get_requirement,
    adapts_mapping,
)
from datatest.differences import NOVALUE


# Remove for datatest version 0.9.8.
import warnings
warnings.filterwarnings('ignore', message='subset and superset warning')


class TestBuildDescription(unittest.TestCase):
    def test_docstring_messy(self):
        def func(x):
            """  \n  line one  \nline two"""  # <- Deliberately messy
            return False                      #    whitespace, do not
                                              #    change.
        description = _build_description(func)
        self.assertEqual(description, 'line one')

    def test_docstring_whitespace(self):
        def func(x):
            """    \n    """  # <- Docstring is entirely whitespace.
            return False

        description = _build_description(func)
        self.assertEqual(description, 'does not satisfy func()')

    def test_docstring_is_None(self):
        def func(x):
            return False
        description = _build_description(func)
        self.assertEqual(description, 'does not satisfy func()')

    def test_builtin_type(self):
        description = _build_description(float)
        msg = 'should be name in backticks'
        self.assertEqual(description, "does not satisfy `float`", msg=msg)

    def test_user_defined_type(self):
        """User-defined classes should use the name in quotes (not the
        docstring).
        """
        class MyClass(object):
            """A dummy class for testing."""
            def __call__(self, *args):
                """Always returns False."""
                return False

            def __repr__(self):
                return '**dummy class**'

        self.assertTrue(MyClass.__doc__, msg='make sure class has docstring')

        description = _build_description(MyClass)
        msg = 'like built-in types, user-defined classes should have name in backticks'
        self.assertEqual(description, "does not satisfy `MyClass`", msg=msg)

    def test_lambda_expression(self):
        description = _build_description(lambda x: False)
        msg = 'if object is in angle brackets, should not use backticks'
        self.assertEqual(description, "does not satisfy <lambda>", msg=msg)

    def test_no_docstring_no_name(self):
        """Non-type objects with no name and no docstring should use
        the object's repr().
        """
        description = _build_description('abc')
        self.assertEqual(description, "does not satisfy 'abc'")

        description = _build_description(123)
        self.assertEqual(description, "does not satisfy `123`")

        class MyClass(object):
            """A dummy class for testing."""
            def __call__(self, *args):
                """Always returns False."""
                return False

            def __repr__(self):
                return '**dummy class**'

        myinstance = MyClass()  # <- Instance of user-defined class.
        description = _build_description(myinstance)
        self.assertEqual(description, "does not satisfy `**dummy class**`")


#######################################################################
# New BaseRequirement and subclass tests.
#######################################################################

def evaluate_items(items):  # <- Test helper.
    """Eagerly evaluate items and return a sorted list of tuples."""
    evaluate = lambda v: list(v) if nonstringiter(v) and exhaustible(v) else v
    return sorted([(k, evaluate(v)) for k, v in items])


class TestBaseRequirement(unittest.TestCase):
    def setUp(self):
        class MinimalRequirement(BaseRequirement):
            def check_data(self, data):
                return [], ''

        self.requirement = MinimalRequirement()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            BaseRequirement()

    def test_verify_difference(self):
        self.assertIsNone(self.requirement._verify_difference(Missing(1)),
                          msg='no explicit return value')

        regex = (r"values returned from MinimalRequirement must be "
                 r"difference objects, got str: 'a string instance'")
        with self.assertRaisesRegex(TypeError, regex):
            self.requirement._verify_difference('a string instance')

    def test_wrap_difference_group(self):
        group = [Missing(1), Missing(2)]
        wrapped = self.requirement._wrap_difference_group(group)
        self.assertEqual(list(wrapped), group)

        group = [Missing(1), 'a string instance']
        wrapped = self.requirement._wrap_difference_group(group)
        with self.assertRaises(TypeError):
            list(wrapped)  # <- Evaluate generator.

    def test_wrap_difference_items(self):
        # Values as single differences.
        items = [('A', Missing(1)), ('B', Missing(2))]
        wrapped = self.requirement._wrap_difference_items(items)
        self.assertEqual(list(wrapped), items)

        items = [('A', Missing(1)), ('B', 'a string instance')]
        wrapped = self.requirement._wrap_difference_items(items)
        with self.assertRaises(TypeError):
            list(wrapped)  # <- Evaluate generator.

        # Values as groups of differences.
        items = [('A', [Missing(1), Missing(2)]),
                 ('B', [Missing(3), Missing(4)])]
        wrapped = self.requirement._wrap_difference_items(items)
        self.assertEqual([(k, list(v)) for k, v in wrapped], items)

        items = [('A', [Missing(1), Missing(2)]),
                 ('B', [Missing(3), 'a string instance'])]
        wrapped = self.requirement._wrap_difference_items(items)
        with self.assertRaises(TypeError):
            evaluate_items(wrapped)  # <- Evaluate generator.

    def test_normalize_iter_and_description(self):
        result = ([Missing(1)], 'error message')  # <- Iterable and description.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'error message')

    def test_normalize_iter(self):
        result = [Missing(1)]  # <- Iterable only, no description.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'does not satisfy MinimalRequirement', msg='gets default description')

    def test_normalize_tuple_of_diffs(self):
        """Should not mistake a 2-tuple of difference objects for a
        2-tuple containing an iterable of differences with a string
        description.
        """
        result = (Missing(1), Missing(2))  # <- A 2-tuple of diffs.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1), Missing(2)])
        self.assertEqual(desc, 'does not satisfy MinimalRequirement', msg='gets default description')

    def test_normalize_empty_iter(self):
        """Empty iterable result should be converted to None."""
        result = (iter([]), 'error message')  # <- Empty iterable and description.
        normalized = self.requirement._normalize(result)
        self.assertIsNone(normalized)

        result = iter([])  # <- Empty iterable
        normalized = self.requirement._normalize(result)
        self.assertIsNone(normalized)

    def test_normalize_bad_types(self):
        """Bad return types should trigger TypeError."""
        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = (Missing(1), 'error message')  # <- Non-iterable and description.
            self.requirement._normalize(result)

        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = None  # <- None only.
            self.requirement._normalize(result)

        with self.assertRaisesRegex(TypeError, 'should return .* an iterable and a string'):
            result = (None, 'error message')  # <- None and description
            self.requirement._normalize(result)


class TestItemsRequirement(unittest.TestCase):
    def setUp(self):
        class RequiredIntValues(ItemsRequirement):
            def check_items(self, items):
                for k, v in items:
                    if not isinstance(v, int):
                        yield k, Invalid(v)

        self.requirement = RequiredIntValues()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            ItemsRequirement()

    def test_check_items(self):
        self.assertIsNone(self.requirement([('A', 1), ('B', 2)]),
                          msg='should return None when data satisfies requirement')

        diff, desc = self.requirement([('A', 1), ('B', 2.0)])
        self.assertEqual(list(diff), [('B', Invalid(2.0))],
                         msg='should return items iterable for values that fail requirement')

    def test_check_data(self):
        diff, desc = self.requirement([('A', 1), ('B', 2.0)])
        self.assertEqual(list(diff), [('B', Invalid(2.0))])

        diff, desc = self.requirement({'A': 1, 'B': 2.0})
        self.assertEqual(list(diff), [('B', Invalid(2.0))])


class TestGroupRequirement(unittest.TestCase):
    def setUp(self):
        class RequiredThreePlus(GroupRequirement):
            def check_group(self, group):
                group = list(group)
                if len(group) < 3:
                    diffs = (Invalid(x) for x in group)
                    return diffs, 'requires 3 or more elements'
                return [], ''

        self.requirement = RequiredThreePlus()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            GroupRequirement()

    def test_check_group(self):
        requirement = self.requirement

        diff, desc = requirement.check_group([1, 2, 3])
        self.assertEqual(list(diff), [])
        self.assertEqual(desc, '')

        diff, desc = requirement.check_group([1, 2])
        self.assertEqual(list(diff), [Invalid(1), Invalid(2)])
        self.assertEqual(desc, 'requires 3 or more elements')

    def test_check_items(self):
        data = [('A', [1, 2, 3]), ('B', [4, 5, 6])]
        diff, desc = self.requirement.check_items(data)
        self.assertEqual(diff, [])
        self.assertEqual(desc, '')

        data = [('A', [1, 2, 3]), ('B', [4, 5])]
        diff, desc = self.requirement.check_items(data)
        diff = sorted((k, list(v)) for k, v in diff)
        self.assertEqual(diff, [('B', [Invalid(4), Invalid(5)])])
        self.assertEqual(desc, 'requires 3 or more elements')

    def test_check_items_autowrap(self):
        """Check autowrap behavior."""
        data = [('A', 1)]  # <- 1 is a base element, not a group of elements.

        # With autowrap=True, the 1 should get wrapped in a list and
        # treated as a group.
        diff, desc = self.requirement.check_items(data)  # <- autowrap=True is the default
        diff = sorted((k, v) for k, v in diff)
        self.assertEqual(diff, [('A', Invalid(1))])
        self.assertEqual(desc, 'requires 3 or more elements')

        # With autowrap=False, the 1 used as-is without changes.
        with self.assertRaises(TypeError):
            self.requirement.check_items(data, autowrap=False)

    def test_check_data(self):
        # Test mapping or key/value items.
        data = {'A': [1, 2, 3], 'B': [4, 5], 'C': 6}
        diff, desc = self.requirement.check_data(data)
        diff = sorted((k, list(v) if isinstance(v, Iterable) else v) for k, v in diff)
        self.assertEqual(diff, [('B', [Invalid(4), Invalid(5)]), ('C', Invalid(6))])
        self.assertEqual(desc, 'requires 3 or more elements')

        # Test group.
        data = [4, 5]
        diff, desc = self.requirement.check_data(data)
        self.assertEqual(list(diff), [Invalid(4), Invalid(5)])
        self.assertEqual(desc, 'requires 3 or more elements')

        # Test BaseElement.
        data = 4
        diff, desc = self.requirement.check_data(data)
        self.assertEqual(list(diff), [Invalid(4)])
        self.assertEqual(desc, 'requires 3 or more elements')


class TestRequiredPredicate2(unittest.TestCase):
    def setUp(self):
        def isdigit(x):
            return x.isdigit()
        self.requirement = RequiredPredicate(isdigit)

    def test_all_true(self):
        data = iter(['10', '20', '30'])
        result = self.requirement(data)
        self.assertIsNone(result)  # Predicate is true for all, returns None.

    def test_some_false(self):
        """When the predicate returns False, values should be returned as
        Invalid() differences.
        """
        data = ['10', '20', 'XX']
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Invalid('XX')])
        self.assertEqual(desc, 'does not satisfy isdigit()')

    def test_show_expected(self):
        data = ['XX', 'YY']
        requirement = RequiredPredicate('YY', show_expected=True)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('XX', expected='YY')])
        self.assertEqual(desc, "does not satisfy 'YY'")

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Invalid('XX'), Invalid('XX'), Invalid('XX')])
        self.assertEqual(desc, 'does not satisfy isdigit()')

    def test_empty_iterable(self):
        result = self.requirement([])
        self.assertIsNone(result)

    def test_some_false_deviations(self):
        """When the predicate returns False, numeric differences should
        be Deviation() objects not Invalid() objects.
        """
        data = [10, 10, 12]
        requirement = RequiredPredicate(10)

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2, 10)])
        self.assertEqual(desc, 'does not satisfy `10`')

    def test_novalue_token(self):
        data = [123, 'abc']
        requirement = RequiredPredicate(NOVALUE)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Extra(+123), Extra('abc')])
        #self.assertEqual(desc, 'does not satisfy requirement')

        data = [10, NOVALUE]
        requirement = RequiredPredicate(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(10)])
        self.assertEqual(desc, 'does not satisfy `10`')

        data = ['abc', NOVALUE]
        requirement = RequiredPredicate('abc')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing('abc')])
        self.assertEqual(desc, "does not satisfy 'abc'")

    def test_predicate_error(self):
        """Errors should not be counted as False or otherwise hidden."""
        data = ['10', '20', 'XX', 40]  # <- Predicate assumes string, int has no isdigit().
        diff, desc  = self.requirement(data)
        with self.assertRaisesRegex(AttributeError, "no attribute 'isdigit'"):
            list(diff)

    def test_returned_difference(self):
        """When a predicate returns a difference object, it should
        used in place of the default Invalid difference.
        """
        def counts_to_three(x):
            if 1 <= x <= 3:
                return True
            if x == 4:
                return Invalid('4 shalt thou not count')
            return Invalid('{0} is right out'.format(x))

        requirement = RequiredPredicate(counts_to_three)

        data = [1, 2, 3, 4, 5]
        diff, desc = requirement(data)
        expected = [
            Invalid('4 shalt thou not count'),
            Invalid('5 is right out'),
        ]
        self.assertEqual(list(diff), expected)
        self.assertEqual(desc, 'does not satisfy counts_to_three()')

    def test_items(self):
        def iseven(x):
            return x % 2 == 0
        requirement = RequiredPredicate(iseven)

        data = {'A': [2, 4, 5], 'B': 6, 'C': 7}
        diff, desc = requirement(data)
        expected = [
            ('A', [Invalid(5)]),
            ('C', Invalid(7)),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredRegex(unittest.TestCase):
    def test_all_true(self):
        data = iter(['abx', 'aby', 'abz'])
        requirement = RequiredRegex(r'^a\w\w$')
        result = requirement(data)
        self.assertIsNone(result)  # True for all elements, returns None.

    def test_some_false(self):
        """When the regex predicate returns False, values should be
        returned as Invalid() differences.
        """
        data = ['abx', 'aby', 'Axy']

        requirement = RequiredRegex(r'^a\w\w$')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('Axy')])

        # Test regular expression flags.
        requirement = RequiredRegex(r'^a\w\w$', flags=re.IGNORECASE)
        result = requirement(data)
        self.assertIsNone(result)  # True for all elements, returns None.

    def test_tuple_comparison(self):
        """Should work on string elements within tuples."""
        data = [(1, 'abx'), (2, 'abcx'), (1, 'xy')]

        requirement = RequiredRegex((1, r'^a\w\w$'))
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid((2, 'abcx')), Invalid((1, 'xy'))])

    def test_show_expected(self):
        data = ['abx', 'aby', 'xy']

        requirement = RequiredRegex(r'^a\w\w$', show_expected=True)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('xy', expected=r'^a\w\w$')])

    def test_empty_iterable(self):
        requirement = RequiredRegex(r'^a\w\w$')
        result = requirement([])
        self.assertIsNone(result)

    def test_nonstring_value(self):
        """When the RequiredRegex is given non-string values, the normal
        predicate differences should be returned (e.g., Deviation, for
        numeric comparisons).
        """
        data = [10, 10, 12]
        requirement = RequiredRegex(10)

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2, 10)])

    def test_novalue_token(self):
        data = [123, 'abc']
        requirement = RequiredRegex(NOVALUE)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Extra(123), Extra('abc')])

        data = [10, NOVALUE]
        requirement = RequiredRegex(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(10)])

        data = ['abc', NOVALUE]
        requirement = RequiredRegex(r'^a\w\w$')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(r'^a\w\w$')])

    def test_items(self):
        requirement = RequiredRegex(r'^a\w\w$')

        data = {'A': ['abx', 'abx', 'xxx'], 'B': 'abc', 'C': 'yyyy'}
        diff, desc = requirement(data)
        expected = [
            ('A', [Invalid('xxx')]),
            ('C', Invalid('yyyy')),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredApprox(unittest.TestCase):
    def test_passing_default(self):
        requirement = RequiredApprox(10)

        data = [10.00000001, 10.00000002, 10.00000003]
        result = requirement(data)
        self.assertIsNone(result)  # True for all, returns None.

    def test_some_false(self):
        """Numeric differences beyond the approximate range should
        create Deviation differences.
        """
        requirement = RequiredApprox(10)

        # Using check_group() method internally.
        data = [10.00000001, 10.00000002, 9.5]
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

        # Using check_group() method with single item.
        data = 9.5
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

        # Using check_items() method internally.
        data = {'A': 10.00000001, 'B': 9.5, 'C': [9.5, 10.00000001]}
        diff, desc = requirement(data)
        expected = [
            ('B', Deviation(-0.5, 10)),
            ('C', [Deviation(-0.5, 10)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_tuple_comparison(self):
        """Should work on numeric elements within tuples."""
        data = [(0.50390625, 'abc'), (0.4921875, 'abc'), (0.5, 'xyz')]

        requirement = RequiredApprox((0.5, 'abc'), places=2)
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid((0.4921875, 'abc')), Invalid((0.5, 'xyz'))])
        self.assertEqual(desc, 'not equal within 2 decimal places')

    def test_specified_places(self):
        requirement = RequiredApprox(0.5, places=2)

        data = [0.50390625, 0.49609375, 0.4921875]

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.0078125, 0.5)])
        self.assertEqual(desc, 'not equal within 2 decimal places')

    def test_specified_delta(self):
        requirement = RequiredApprox(10, delta=3)

        data = [10, 7, 13, 13.0625]
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+3.0625, 10)])
        self.assertEqual(desc, 'not equal within delta of 3')

    def test_nonnumeric_data(self):
        """Non-numeric differences should create Invalid() differences."""
        requirement = RequiredApprox(10)

        data = [10.00000001, 10.00000002, 'abc']

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('abc')])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_show_expected(self):
        requirement = RequiredApprox(10, show_expected=True)

        data = [10.00000001, 10.00000002, 'abc']

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('abc', expected=10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        requirement = RequiredApprox(10)

        data = [10.00000001, 9.5, 9.5]  # <- Multiple 9.5's.

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10), Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_empty_iterable(self):
        requirement = RequiredApprox(10)
        result = requirement([])
        self.assertIsNone(result)

    def test_nonnumeric_baseelement(self):
        """Non-numeric base elements should have normal predicate behavior."""
        requirement = RequiredApprox('abc')

        self.assertIsNone(requirement('abc'))

        diff, desc = requirement('xxx')
        self.assertEqual(list(diff), [Invalid('xxx')])

    def test_novalue_token(self):
        data = [10.00000001, NOVALUE]
        requirement = RequiredApprox(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')


class TestRequiredFuzzy(unittest.TestCase):
    def test_all_true(self):
        data = iter(['abx', 'aby', 'abz'])
        requirement = RequiredFuzzy('abc')
        result = requirement(data)
        self.assertIsNone(result)  # True for all elements, returns None.

    def test_some_false(self):
        """When the fuzzy predicate returns False, values should be
        returned as Invalid() differences.
        """
        data = ['abx', 'aby', 'xyz']

        requirement = RequiredFuzzy('abc')
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid('xyz')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_cutoff(self):
        data = ['aaaaa', 'aaaax', 'aaaxx', 'xxxxx']

        requirement = RequiredFuzzy('aaaaa', cutoff=0.6)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('xxxxx')])
        self.assertEqual(desc, "does not satisfy 'aaaaa', fuzzy matching at ratio 0.6 or greater")

        requirement = RequiredFuzzy('aaaaa', cutoff=0.8)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('aaaxx'), Invalid('xxxxx')])
        self.assertEqual(desc, "does not satisfy 'aaaaa', fuzzy matching at ratio 0.8 or greater")

    def test_tuple_comparison(self):
        """Should work on string elements within tuples."""
        data = [(1, 'abx'), (2, 'abx'), (1, 'xyz')]

        requirement = RequiredFuzzy((1, 'abc'))
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid((2, 'abx')), Invalid((1, 'xyz'))])
        self.assertEqual(desc, "does not satisfy `(1, 'abc')`, fuzzy matching at ratio 0.6 or greater")

    def test_show_expected(self):
        data = ['abx', 'aby', 'xyz']

        requirement = RequiredFuzzy('abc', show_expected=True)
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid('xyz', expected='abc')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_empty_iterable(self):
        requirement = RequiredFuzzy('abc')
        result = requirement([])
        self.assertIsNone(result)

    def test_nonstring_value(self):
        """When the RequiredFuzzy is given non-string values, the normal
        predicate differences should be returned (e.g., Deviation, for
        numeric comparisons).
        """
        data = [10, 10, 12]
        requirement = RequiredFuzzy(10)

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2, 10)])
        self.assertEqual(desc, 'does not satisfy `10`, fuzzy matching at ratio 0.6 or greater')

    def test_novalue_token(self):
        data = [123, 'abc']
        requirement = RequiredFuzzy(NOVALUE)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Extra(123), Extra('abc')])

        data = [10, NOVALUE]
        requirement = RequiredFuzzy(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(10)])
        self.assertEqual(desc, 'does not satisfy `10`, fuzzy matching at ratio 0.6 or greater')

        data = ['abc', NOVALUE]
        requirement = RequiredFuzzy('abc')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing('abc')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_items(self):
        requirement = RequiredFuzzy('abc')

        data = {'A': ['abx', 'abx', 'xxx'], 'B': 'abc', 'C': 'yyy'}
        diff, desc = requirement(data)
        expected = [
            ('A', [Invalid('xxx')]),
            ('C', Invalid('yyy')),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredInterval(unittest.TestCase):
    def test_all_valid(self):
        requirement = RequiredInterval(2, 8)
        result = requirement([2, 4, 6, 8])
        self.assertIsNone(result)  # All elements are valid, returns None.

    def test_differences(self):
        """If an element are less than the lower bound, the lower bound
        should be used as the expected value. If an element is greater
        than the upper bound, the upper bound should be used as the
        expected value.
        """
        requirement = RequiredInterval(2, 8)

        diff, desc = requirement([0, 2, 4, 6, 8, 10])
        self.assertEqual(list(diff), [Deviation(-2, 2), Deviation(+2, 8)])
        self.assertEqual(desc, r"elements `x` do not satisfy `2 <= x <= 8`")

        diff, desc = requirement([2, 4, 6, float('nan'), 8])
        self.assertEqual(list(diff), [Invalid(float('nan'))])
        self.assertEqual(desc, r"elements `x` do not satisfy `2 <= x <= 8`")

    def test_degenrate_interval(self):
        """Should accept degenerate intervals. If lower and upper
        bounds are auto-calculated from a collection of values,
        there are two cases where they could be equal--resulting
        in a "degenerate" interval: (1) all of the values are equal,
        (2) the collection only contains a single value.
        """
        requirement = RequiredInterval(6, 6)

        result = requirement([6, 6, 6])
        self.assertIsNone(result)

        diff, desc = requirement([4, 6, 8])
        self.assertEqual(list(diff), [Deviation(-2, 6), Deviation(+2, 6)])
        self.assertEqual(desc, r"elements `x` do not satisfy `6 <= x <= 6`")

    def test_left_bound(self):
        requirement = RequiredInterval(4)

        diff, desc = requirement([2, 4, 6])
        self.assertEqual(list(diff), [Deviation(-2, 4)])
        self.assertEqual(desc, 'does not satisfy minimum expected value of 4')

        diff, desc = requirement([4, float('nan'), 6])
        self.assertEqual(list(diff), [Invalid(float('nan'))])
        self.assertEqual(desc, 'does not satisfy minimum expected value of 4')

    def test_right_bound(self):
        requirement = RequiredInterval(max=4)

        diff, desc = requirement([2, 4, 6])
        self.assertEqual(list(diff), [Deviation(+2, 4)])
        self.assertEqual(desc, 'does not satisfy maximum expected value of 4')

        diff, desc = requirement([2, float('nan'), 4])
        self.assertEqual(list(diff), [Invalid(float('nan'))])
        self.assertEqual(desc, 'does not satisfy maximum expected value of 4')

    def test_bad_args(self):
        with self.assertRaises(ValueError, msg='lower must not be greater than upper'):
            requirement = RequiredInterval(6, 5)

        if not sortable([6, 'a']):
            with self.assertRaises(TypeError, msg='unsortable args should raise error'):
                requirement = RequiredInterval(6, 'a')

        with self.assertRaises(ValueError, msg='must not accept NaN'):
            requirement = RequiredInterval(5, float('nan'))

        with self.assertRaises(ValueError, msg='must not accept NaN'):
            requirement = RequiredInterval(float('nan'), 6)

    def test_non_numeric(self):
        """Should work for any sortable types."""
        requirement = RequiredInterval('b', 'e')
        result = requirement(['b', 'c', 'd', 'e'])
        self.assertIsNone(result)  # All elements are valid, returns None.

    def test_non_numeric_failure(self):
        """Should return Invalid() differences."""
        requirement = RequiredInterval('b', 'e')
        diff, desc = requirement(['a', 'b', 'c', 'd', 'e', 'f'])

        self.assertEqual(list(diff), [Invalid('a'), Invalid('f')])
        self.assertEqual(desc, r"elements `x` do not satisfy `'b' <= x <= 'e'`")

    def test_non_numeric_show_expected(self):
        """Should return Invalid() differences."""
        requirement = RequiredInterval('b', 'e', show_expected=True)
        diff, desc = requirement(['a', 'b', 'c', 'd', 'e', 'f'])

        self.assertEqual(list(diff), [Invalid('a', expected='b'), Invalid('f', expected='e')])
        self.assertEqual(desc, r"elements `x` do not satisfy `'b' <= x <= 'e'`")

    def test_empty_iterable(self):
        requirement = RequiredInterval(2, 8)
        result = requirement([])
        self.assertIsNone(result)  # No elements means no invalid elements!

    def test_mixed_types(self):
        requirement = RequiredInterval(2, 6)
        diff, desc = requirement([2, 4, 'a', 6, 8])
        self.assertEqual(list(diff), [Invalid('a'), Deviation(+2, 6)])
        self.assertEqual(desc, r"elements `x` do not satisfy `2 <= x <= 6`")

    def test_items(self):
        requirement = RequiredInterval(2, 6)
        data = {
            'A': [4, 6, 8],
            'B': 5,
            'C': 10,
            'D': 'a',
            'E': [5, 'b'],
        }
        diff, desc = requirement(data)
        expected = [
            ('A', [Deviation(+2, 6)]),
            ('C', Deviation(+4, 6)),
            ('D', Invalid('a')),
            ('E', [Invalid('b')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredSet2(unittest.TestCase):
    def setUp(self):
        self.requirement = RequiredSet(set([1, 2, 3]))

    def test_no_difference(self):
        data = iter([1, 2, 3])
        result = self.requirement(data)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter([1, 2])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(3)])

    def test_extra(self):
        data = iter([1, 2, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])

    def test_repeat_values(self):
        """Repeat values should not result in duplicate differences."""
        data = iter([1, 2, 3, 4, 4, 4])  # <- Multiple 4's.
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])  # <- One difference.

    def test_missing_and_extra(self):
        data = iter([1, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(2), Extra(4)])

    def test_empty_iterable(self):
        requirement = RequiredSet(set([1]))
        differences, description = requirement([])
        self.assertEqual(list(differences), [Missing(1)])


class TestRequiredSuperset(unittest.TestCase):
    def test_element_group(self):
        data = [1, 2, 3]
        requirement = RequiredSuperset(set([1, 2]))
        self.assertIsNone(requirement(data))

        data = [1, 2]
        requirement = RequiredSuperset(set([1, 2, 3, 4]))
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(3), Missing(4)])
        self.assertRegex(desc, 'must contain all')

    def test_data_mapping(self):
        requirement = RequiredSuperset(set([1, 2, 3]))

        data = {'a': [1, 2, 3], 'b': [1, 2, 3], 'c': [1, 2, 3]}
        self.assertIsNone(requirement(data))

        data = {'a': [1, 2], 'b': [1, 2, 3], 'c': [1, 2, 3, 4]}
        diff, desc = requirement(data)
        expected = [
            ('a', [Missing(3)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'must contain all')

    def test_single_element_handling(self):
        requirement = RequiredSuperset(set([1, 2]))

        diff, desc = requirement(1)
        self.assertEqual(list(diff), [Missing(2)])

        diff, desc = requirement((3, 4))  # <- Tuple is single element.
        diff = sorted(diff, key=lambda x: x.args)
        self.assertEqual(diff, [Missing(1), Missing(2)])


class TestRequiredSubset(unittest.TestCase):
    def test_element_group(self):
        data = [1, 2]
        requirement = RequiredSubset(set([1, 2, 3]))
        self.assertIsNone(requirement(data))

        data = [1, 2, 3, 4]
        requirement = RequiredSubset(set([1, 2]))
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Extra(3), Extra(4)])
        self.assertRegex(desc, 'may only contain')

    def test_data_mapping(self):
        requirement = RequiredSubset(set([1, 2, 3]))

        data = {'a': [1, 2, 3], 'b': [1, 2], 'c': [1]}
        self.assertIsNone(requirement(data))

        data = {'a': [1, 2], 'b': [1, 2, 3], 'c': [1, 2, 3, 4]}
        diff, desc = requirement(data)
        expected = [
            ('c', [Extra(4)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'may only contain')

    def test_single_element_handling(self):
        requirement = RequiredSubset(set([1, 2]))

        diff, desc = requirement(3)
        self.assertEqual(list(diff), [Extra(3)])

        diff, desc = requirement((3, 4))  # <- Tuple is single element.
        diff = sorted(diff, key=lambda x: x.args)
        self.assertEqual(diff, [Extra((3, 4))])


class TestRequiredUnique(unittest.TestCase):
    def setUp(self):
        self.requirement = RequiredUnique()

    def test_element_group(self):
        data = [1, 2, 3]
        self.assertIsNone(self.requirement(data))  # No duplicates.

        data = [1, 2, 2, 3, 3, 3]
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Extra(2), Extra(3), Extra(3)])
        self.assertRegex(desc, 'should be unique')

    def test_mapping_of_element_groups(self):
        data = {'a': [1, 2, 3], 'b': [1, 2, 3], 'c': [1, 2, 3]}
        self.assertIsNone(self.requirement(data))  # No duplicates.

        data = {'a': [1], 'b': [2, 2], 'c': [3, 3, 3]}
        diff, desc = self.requirement(data)
        expected = [
            ('b', [Extra(2)]),
            ('c', [Extra(3), Extra(3)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'should be unique')

    def test_single_element_handling(self):
        """RequiredUnique can not operate directly on base elements."""
        with self.assertRaises(ValueError):
            self.requirement((1, 2))

        with self.assertRaises(ValueError):
            self.requirement({'a': (1, 2)})


class TestRequiredOrder2(unittest.TestCase):
    def test_no_difference(self):
        data = ['aaa', 'bbb', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        self.assertIsNone(required(data))  # No difference, returns None.

    def test_some_missing(self):
        data = ['bbb', 'ddd']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((1, 'ccc')),
            Missing((2, 'eee')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_missing(self):
        data = []  # <- Empty!
        required = RequiredOrder(['aaa', 'bbb'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((0, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Extra((3, 'ddd')),
            Extra((4, 'eee')),
            Extra((5, 'fff')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_extra(self):
        data = ['aaa', 'bbb']
        required = RequiredOrder([])  # <- Empty!
        differences, _ = required(data)
        expected = [
            Extra((0, 'aaa')),
            Extra((1, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_one_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc', 'yyy', 'zzz']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((3, 'ddd')),
            Extra((3, 'yyy')),
            Missing((4, 'eee')),
            Extra((4, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra_different_lengths(self):
        data = ['aaa', 'xxx', 'eee']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((2, 'ccc')),
            Missing((2, 'ddd')),
        ]
        self.assertEqual(list(differences), expected)

        data = ['aaa', 'xxx', 'yyy', 'zzz', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Extra((2, 'yyy')),
            Extra((3, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_numeric_matching(self):
        """When checking element order, numeric differences should NOT
        be converted into Deviation objects.
        """
        data = [1, 100, 4, 200, 300]
        required = RequiredOrder([1, 2, 3, 4, 5])
        differences, _ = required(data)
        expected = [
            Missing((1, 2)),
            Extra((1, 100)),
            Missing((2, 3)),
            Missing((3, 5)),
            Extra((3, 200)),
            Extra((4, 300)),
        ]
        self.assertEqual(list(differences), expected)

    def test_unhashable_objects(self):
        """Should try to compare sequences of unhashable types."""
        data = [{'a': 1}, {'b': 2}, {'c': 3}]
        required = RequiredOrder([{'a': 1}, {'b': 2}, {'c': 3}])
        result = required(data)
        self.assertIsNone(result)  # No difference, returns None.

        data = [{'a': 1}, {'x': 0}, {'d': 4}, {'y': 5}, {'g': 7}]
        required = RequiredOrder([{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}])
        differences, _ = required(data)
        expected = [
            Missing((1, {'b': 2})),
            Extra((1, {'x': 0})),
            Missing((2, {'c': 3})),
            Missing((3, {'f': 6})),
            Extra((3, {'y': 5})),
            Extra((4, {'g': 7})),
        ]
        self.assertEqual(list(differences), expected)


class TestRequiredSequence(unittest.TestCase):
    def test_passing(self):
        requirement = RequiredSequence(['a', 'b', 'c', 'd'])
        self.assertIsNone(requirement(['a', 'b', 'c', 'd']))

        requirement = RequiredSequence(['a', 2, set(['c'])])
        self.assertIsNone(requirement(['a', 2, 'c']))

    def test_some_differences(self):
        requirement = RequiredSequence(['a', 2, set(['c']), 'd', 'e'])
        diff, desc = requirement(['a', 1, 'x', 'd', 'e'])
        expected =  [
            Deviation(-1, 2),
            Invalid('x', expected=set(['c'])),
        ]
        self.assertEqual(list(diff), expected)
        self.assertEqual(desc, 'does not match required sequence')

    def test_mismatched_length(self):
        requirement = RequiredSequence(['a', 'b', 'c', 'd'])
        diff, desc = requirement(['a', 'b'])
        expected =  [Missing('c'), Missing('d')]
        self.assertEqual(list(diff), expected)
        self.assertEqual(desc, 'does not match required sequence')

        requirement = RequiredSequence(['a', 'b'])
        diff, desc = requirement(['a', 'b', 'c', 'd'])
        expected =  [Extra('c'), Extra('d')]
        self.assertEqual(list(diff), expected)
        self.assertEqual(desc, 'does not match required sequence')

    def test_requirement_factory(self):
        def factory(val):
            val_or_repr = set([val, repr(val)])
            return RequiredPredicate(val_or_repr)

        requirement = RequiredSequence([1.0, 2], factory=factory)

        self.assertIsNone(requirement([1.0, 2]))
        self.assertIsNone(requirement(['1.0', '2']))

        diff, desc = requirement(['1', 3])
        expected = [
            Invalid('1', expected=set([1.0, '1.0'])),
            Invalid(3, expected=set([2, '2'])),
        ]
        self.assertEqual(list(diff), expected)


class TestRequiredMapping(unittest.TestCase):
    def test_instantiation(self):
        # Should pass without error.
        some_dict = {'a': 'abc'}
        requirement = RequiredMapping(some_dict)
        requirement = RequiredMapping(some_dict.items())

        with self.assertRaises(ValueError):
            requirement = RequiredMapping('abc')

    def test_bad_data_type(self):
        requirement = RequiredMapping({'a': 'abc'})
        with self.assertRaises(ValueError):
            requirement('abc')

    def test_equality_of_single_elements(self):
        requirement = RequiredMapping({'a': 'j', 'b': 'k', 'c': 9})
        diff, desc = requirement({'a': 'x', 'b': 10, 'c': 10})
        expected = {'a': Invalid('x', 'j'), 'b': Invalid(10, 'k'), 'c': Deviation(+1, 9)}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test that tuples are also treated as single-elements.
        requirement = RequiredMapping({'a': (1, 'j'), 'b': (9, 9)})
        diff, desc = requirement({'a': (1, 'x'), 'b': (9, 10)})
        expected = {'a': Invalid((1, 'x'), expected=(1, 'j')),
                    'b': Invalid((9, 10), expected=(9, 9))}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test custom difference handling.
        def func1(x):
            return True if x == 'foo' else Invalid('bar')

        def func2(x):
            return True if x == 'foo' else Invalid('baz')

        requirement = RequiredMapping({'a': func1, 'b': func2})
        diff, desc = requirement({'a': 'qux', 'b': 'quux'})
        expected = {'a': Invalid('bar'), 'b': Invalid('baz')}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_equality_of_multiple_elements(self):
        requirement = RequiredMapping({'a': 'j', 'b': 9})
        diff, desc = requirement({'a': ['x', 'j'], 'b': [10, 9]})
        expected = [
            ('a', [Invalid('x')]),
            ('b', [Deviation(+1, 9)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test groups of tuple elements.
        requirement = RequiredMapping({'a': (1, 'j'), 'b': (9, 9)})
        diff, desc = requirement({'a': [(1, 'j'), (1, 'x')], 'b': [(9, 9), (9, 10)]})
        expected = [
            ('a', [Invalid((1, 'x'))]),
            ('b', [Invalid((9, 10))]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_set_membership_differences(self):
        requirement = RequiredMapping({'a': set(['x', 'y']), 'b': set(['x', 'y'])})
        diff, desc = requirement({'a': ['x', 'x'], 'b': ['x', 'y', 'z']})
        expected = [
            ('a', [Missing('y')]),
            ('b', [Extra('z')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

        requirement = RequiredMapping({'a': set(['x', 'y'])})
        diff, desc = requirement({'a': 'x'})
        expected = [
            ('a', Missing('y')),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

    def test_mismatched_keys(self):
        # Required keys missing from data.
        requirement = RequiredMapping({
            'a': 'j',
            'b': 9,
            'c': 'x',
            'd': set(['y']),
        })
        diff, desc = requirement({'a': 'j'})
        expected = [
            ('b', Missing(9)),
            ('c', Missing('x')),
            ('d', [Missing('y')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Extra keys unexpectedly found in data.
        requirement = RequiredMapping({'a': 'j'})
        diff, desc = requirement({
            'a': 'j',
            'b': 9,
            'c': [10, 11],
            'd': 'x',
            'e': set(['y']),
        })
        expected = [
            ('b', Extra(9)),
            ('c', [Extra(10), Extra(11)]),
            ('d', Extra('x')),
            ('e', [Extra('y')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_empty_vs_nonempty_values(self):
        empty = dict()
        nonempty = {'a': set(['x'])}
        required_empty = RequiredMapping(empty)
        required_nonempty = RequiredMapping(nonempty)

        self.assertIsNone(required_empty(empty))

        diff, desc = required_empty(nonempty)
        expected = [
            ('a', [Extra('x')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)

        diff, desc = required_nonempty(empty)
        expected = [
            ('a', [Missing('x')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)

    def test_custom_requirements(self):
        class MyRequirement(GroupRequirement):
            def check_group(self, group):
                return [Invalid('foo')], 'my message'

        requirement = RequiredMapping({'a': MyRequirement()})
        diff, desc = requirement({'a': 1})  # <- Single-element value.
        expected = [
            ('a', Invalid('foo')),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'my message')

        requirement = RequiredMapping({'a': MyRequirement()})
        diff, desc = requirement({'a': [1, 2, 3]})  # <- List of values.
        expected = [
            ('a', [Invalid('foo')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'my message')

    def test_abstract_factory(self):
        """Test *abstract_factory* argument and method."""
        def custom_factory(value):
            if isinstance(value, str):
                return RequiredSet(value)  # <- Treat str as set of characters.
            return RequiredPredicate(value)

        req_dict = {
            'A': 'xy',   # <- Passed to RequiredSet
            'B': 'xyz',  # <- Passed to RequiredSet
            'C': 123,    # <- Passed to RequiredPredicate
        }
        requirement = RequiredMapping(req_dict, factory=custom_factory)

        data = {'A': ['x', 'y', 'y'], 'B': ['x', 'y'], 'C': [123, 123]}
        diff, desc = requirement(data)
        expected = [
            ('B', [Missing('z')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

    def test_integration(self):
        requirement = RequiredMapping({
            'a': 'x',
            'b': 'y',
            'c': 1,
            'd': 2,
            'e': ('abc', int),
            'f': ('def', float),
            'g': set(['a']),
            'h': set(['d', 'e', 'f']),
            'i': [1],
            'j': [4, 5, 6],
        })

        # No differences.
        data = {
            'a': 'x',
            'b': ['y', 'y'],
            'c': 1,
            'd': iter([2, 2]),
            'e': ('abc', 1),
            'f': [('def', 1.0), ('def', 2.0)],
            'g': 'a',
            'h': ['d', 'e', 'f'],
            'i': 1,
            'j': [4, 5, 6],
        }
        self.assertIsNone(requirement(data))

        # Variety of differences.
        data = {
            'a': 'y',
            'b': ['x', 'y'],
            'c': 2,
            'd': [1, 2],
            'e': ('abc', 1.0),
            'f': [('def', 2)],
            'g': 'b',
            'h': ['e', 'f', 'g'],
            'i': 2,
            'j': [5, 6, 7],
        }
        diff, desc = requirement(data)

        expected = {
            'a': Invalid('y', expected='x'),
            'b': [Invalid('x')],
            'c': Deviation(+1, 1),
            'd': [Deviation(-1, 2)],
            'e': Invalid(('abc', 1.0), expected=('abc', int)),
            'f': [Invalid(('def', 2))],
            'g': [Missing('a'), Extra('b')],
            'h': [Missing('d'), Extra('g')],
            'i': [Missing((0, 1)), Extra((0, 2))],
            'j': [Missing((0, 4)), Extra((2, 7))],
        }
        self.assertEqual(dict(evaluate_items(diff)), expected)

    def test_description_message(self):
        # Test same message (set membership message).
        requirement = RequiredMapping({'a': set(['x']), 'b': set(['y'])})
        _, desc = requirement({'a': ['x', 'y'], 'b': ['y', 'z']})
        self.assertEqual(desc, 'does not satisfy set membership')

        # Test different messages--uses default instead.
        requirement = RequiredMapping({'a': set(['x']), 'b': 'y'})
        _, desc = requirement({'a': ['x', 'y'], 'b': ['y', 'z']})
        self.assertEqual(desc, 'does not satisfy mapping requirements')


class TestGetRequirement(unittest.TestCase):
    def test_set(self):
        requirement = get_requirement(set(['foo', 'bar', 'baz']))
        self.assertIsInstance(requirement, RequiredSet)

    def test_sequence(self):
        requirement = get_requirement(['foo', 'bar', 'baz'])
        self.assertIsInstance(requirement, RequiredSequence)

    def test_predicate(self):
        requirement = get_requirement(123)
        self.assertIsInstance(requirement, RequiredPredicate)

        requirement = get_requirement('foo')
        self.assertIsInstance(requirement, RequiredPredicate)

        requirement = get_requirement(('foo', 'bar', 'baz'))
        self.assertIsInstance(requirement, RequiredPredicate)

    def test_mapping(self):
        requirement = get_requirement({'foo': 1, 'bar': 2, 'baz': 3})
        self.assertIsInstance(requirement, RequiredMapping)

    def test_existing_requirement(self):
        existing_requirement = RequiredPredicate('foo')
        requirement = get_requirement(existing_requirement)
        self.assertIs(requirement, existing_requirement)


class TestAdaptsMappingDecorator(unittest.TestCase):
    def setUp(self):
        @adapts_mapping
        class RequiredDefaultNew(RequiredPredicate):
            """Example requirement that doesn't defines its own
            __new__() method (uses object.__new__ by default).
            """

        @adapts_mapping
        class RequiredOtherNew(RequiredPredicate):
            """Example requirement that defines its own __new__()
            method and includes some non-standard custom behavior.
            """
            def __new__(cls, obj):
                if isinstance(obj, int):
                    return RequiredSet(set(str(obj)))  # <- Different type!!!
                return super(RequiredOtherNew, cls).__new__(cls)

        self.RequiredDefaultNew = RequiredDefaultNew
        self.RequiredOtherNew = RequiredOtherNew

    def test_default_new_nonmapping(self):
        requirement = self.RequiredDefaultNew(set(['a', 'b']))
        self.assertIsNone(requirement(['a', 'b']))

    def test_default_new_mapping(self):
        requirement = self.RequiredDefaultNew({
            'A': set(['a', 'b']),
            'B': set(['a', 'b', 'c']),
        })
        self.assertIsNone(requirement({'A': ['a', 'b'], 'B': ['a', 'b', 'c']}))

    def test_other_new_nonmapping(self):
        requirement = self.RequiredOtherNew('foo')
        self.assertIsNone(requirement(['foo', 'foo']))

    def test_other_new_mapping(self):
        requirement = self.RequiredOtherNew({'A': 'foo', 'B': 'bar'})
        self.assertIsNone(requirement({'A': 'foo', 'B': ['bar', 'bar']}))

    def test_nested_mappings(self):
        """Nested mappings should not recurse."""
        requirement = self.RequiredOtherNew({'A': {'foo': 123}, 'B': {'bar': 456}})
        self.assertIsNone(requirement({'A': {'foo': 123}, 'B': [{'bar': 456}, {'bar': 456}]}))

    def test_nonstandard_new_nonmapping(self):
        # In this test, the int type triggers non-standard behavior
        # from __new__().
        requirement = self.RequiredOtherNew(12)
        self.assertIsNone(requirement(['1', '2']))

    def test_nonstandard_new_mapping(self):
        # In this test, the int types trigger non-standard behavior
        # from __new__().
        requirement = self.RequiredOtherNew({'A': 34, 'B': 56})
        self.assertIsNone(requirement({'A': ['3', '4'], 'B': ['5', '6']}))

    def test_bad_type(self):
        """Should raise error if not a subclass of GroupRequirement."""
        with self.assertRaises(TypeError):
            @adapts_mapping
            class BadType(object):  # <- Not a GroupRequirement!
                pass

    def test_no_additional_arguments(self):
        """Decorator should allow classes with no additional arguments."""
        @adapts_mapping
        class NoArgs(RequiredPredicate):
            """Example requirement that defines its own __new__()
            method and includes some non-standard custom behavior.
            """
            def __new__(cls):  # <- No additional arguments!
                return super(NoArgs, cls).__new__(cls)

            def __init__(self):
                super(NoArgs, self).__init__(True)

        requirement = NoArgs()
        self.assertIsNone(requirement('foo'))  # <- Pass without error.
