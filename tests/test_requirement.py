# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest._requirement import Requirement


class TestRequirement(unittest.TestCase):
    def test_incomplete_subclass(self):
        """Instantiation should fail if abstract members are not defined."""
        class IncompleteSubclass(Requirement):
            pass

        with self.assertRaises(TypeError):
            requirement = IncompleteSubclass()

    def test_simple_subclass(self):
        """Test basic subclass behavior."""
        class RequiredValue(Requirement):
            def __init__(self, value):
                self.value = value

            @property
            def msg(self):
                return 'require {0!r}'.format(self.value)

            def filterfalse(self, iterable):
                return (x for x in iterable if x != self.value)

        requirement = RequiredValue('abc')

        result = requirement(['abc', 'def', 'ghi'])
        self.assertEqual(list(result), ['def', 'ghi'])

        result = requirement(['abc', 'abc', 'abc'])
        self.assertIsNone(result)
