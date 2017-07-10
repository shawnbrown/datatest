#!/usr/bin/env python
import re
import datatest


class TestExample(datatest.DataTestCase):
    def test_membership_in_set(self):
        data = ['x', 'x', 'y', 'y', 'z', 'z']
        requirement = {'x', 'y', 'z'}  # <- set
        self.assertValid(data, requirement)

    def test_function_returns_true(self):
        data = ['X', 'X', 'Y', 'Y']
        def requirement(x):  # <- callable (helper function)
            return x.isupper()
        self.assertValid(data, requirement)

    def test_regex_matches(self):
        data = ['foo', 'foo', 'foo', 'bar', 'bar', 'bar']
        requirement = re.compile('^\w\w\w$')  # <- regex object
        self.assertValid(data, requirement)

    def test_equality(self):
        data = ['x', 'x', 'x']
        requirement = 'x'  # <- other (not container, callable, or regex)
        self.assertValid(data, requirement)

    def test_order(self):
        data = ['x', 'x', 'y', 'y', 'z', 'z']
        requirement = ['x', 'x', 'y', 'y', 'z', 'z']  # <- sequence
        self.assertValid(data, requirement)

    def test_mapping(self):
        data = {'x': 'foo', 'y': 'bar'}
        requirement = {'x': 'foo', 'y': 'bar'}  # <- mapping
        self.assertValid(data, requirement)


if __name__ == '__main__':
    datatest.main()
