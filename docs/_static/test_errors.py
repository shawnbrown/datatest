#!/usr/bin/env python
import re
import datatest


class TestExample(datatest.DataTestCase):
    def test_membership_in_set(self):
        data = ['x', 'x2', 'y', 'y', 'z', 'z']
        required_elements = {'x', 'y', 'z'}
        self.assertValid(data, required_elements)

    def test_function_returns_true(self):
        data = ['X', 'X', 'Y', 'y']
        def uppercase(x):
            return x.isupper()
        self.assertValid(data, uppercase)

    def test_regex_matches(self):
        data = ['foo', 'foo', 'foo', 'bar', 'bar', 'xx']
        three_letters = re.compile('^\w\w\w$')
        self.assertValid(data, three_letters)

    def test_equality(self):
        data = ['x', 'x', 'Y']
        other_value = 'x'
        self.assertValid(data, other_value)

    def test_order(self):
        data = ['x', 'X', 'y', 'y', 'z', 'z']
        my_sequence = ['x', 'x', 'y', 'y', 'z', 'z']
        self.assertValid(data, my_sequence)

    def test_mapping1(self):
        data = {
            'x': 'foo',
            'y': 'BAZ',
        }
        required_values = {
            'x': 'foo',
            'y': 'bar',
        }
        self.assertValid(data, required_values)

    def test_mapping2(self):
        data = {
            'x': 11,
            'y': 13,
        }
        required_values = {
            'x': 10,
            'y': 15,
        }
        self.assertValid(data, required_values)

    def test_mapping3(self):
        data = {
            'x': 10,
            'y': 15,
            'z': 3000,
        }
        required_values = {
            'x': 10,
            'y': 15,
            'z': 20,
        }
        self.assertValid(data, required_values)


if __name__ == '__main__':
    datatest.main()
