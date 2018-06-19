"""Example tests using pytest-style conventions."""

import re
from datatest import validate


def test_using_set():
    """Check for set membership."""
    data = ['A', 'B', 'A']

    requirement = {'A', 'B'}

    validate(data, requirement)


def test_using_function():
    """Check that function returns True."""
    data = [2, 4, 6, 8]

    def iseven(x):
        return x % 2 == 0

    validate(data, iseven)


def test_using_type():
    """Check that values are of the given type."""
    data = [0.0, 1.0, 2.0]

    validate(data, float)


def test_using_regex():
    """Check that values match the given pattern."""
    data = ['bake', 'cake', 'bake']

    regex = re.compile('[bc]ake')

    validate(data, regex)


def test_using_string():
    """Check that values equal the given string."""
    data = ['foo', 'foo', 'foo']

    validate(data, 'foo')


def test_using_tuple():
    """Check that tuples of values satisfy corresponding tuple of
    requirements.
    """
    data = [('A', 0.0), ('A', 1.0), ('A', 2.0)]

    requirement = ('A', float)

    validate(data, requirement)


def test_using_dict():
    """Check that values satisfy requirements of matching keys."""
    data = {
        'A': 100,
        'B': 200,
        'C': 300,
    }
    requirement = {
        'A': 100,
        'B': 200,
        'C': 300,
    }
    validate(data, requirement)


def test_using_list():
    """Check that the order of values match the required sequence."""
    data = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

    requirement = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

    validate(data, requirement)
