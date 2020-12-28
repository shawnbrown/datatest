"""Example of failing tests using unittest-style conventions."""

import re
import datatest


class ExampleTests(datatest.DataTestCase):
    def test_using_set(self):
        """Check for set membership."""
        data = ['A', 'B', 'C', 'D']

        requirement = {'A', 'B'}

        self.assertValid(data, requirement)

    def test_using_function(self):
        """Check that function returns True."""
        data = [2, 4, 6, 9]

        def is_even(x):
            return x % 2 == 0

        self.assertValid(data, is_even)

    def test_using_type(self):
        """Check that values are of the given type."""
        data = [0.0, 1.0, 2]

        self.assertValid(data, float)

    def test_using_regex(self):
        """Check that values match the given pattern."""
        data = ['bake', 'cake', 'fake']

        regex = re.compile('[bc]ake')

        self.assertValid(data, regex)

    def test_using_string(self):
        """Check that values equal the given string."""
        data = ['foo', 'foo', 'bar']

        self.assertValid(data, 'foo')

    def test_using_tuple(self):
        """Check that tuples of values satisfy corresponding tuple of
        requirements.
        """
        data = [('A', 1.0), ('A', 2), ('B', 3.0)]

        requirement = ('A', float)

        self.assertValid(data, requirement)

    def test_using_dict(self):
        """Check that values satisfy requirements of matching keys."""
        data = {
            'A': 100,
            'B': 200,
            'C': 299,
            'D': 405,
        }
        requirement = {
            'A': 100,
            'B': 200,
            'C': 300,
            'D': 400,
        }
        self.assertValid(data, requirement)

    def test_using_list(self):
        """Check that the order of values match the required sequence."""
        data = ['A', 'D', 'XXX', 'YYY', 'E', 'ZZZ', 'G']

        requirement = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

        self.assertValid(data, requirement)


if __name__ == '__main__':
    datatest.main()
