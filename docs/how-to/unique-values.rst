
.. module:: datatest

.. meta::
    :description: How to assert unique values.
    :keywords: datatest, unique, find duplicates


###########################
How to Assert Unique Values
###########################

To assert that values are unique, we can define a callable class
that generates :class:`Extra` differences when duplicates are
discovered.

You can copy the following class to use in your own tests:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 21

            from datatest import validate
            from datatest import Extra


            class IsUnique(object):
                """values should be unique"""
                def __init__(self):
                    self.values = set()

                def __call__(self, value):
                    if value in self.values:
                        return Extra(value)
                    self.values.add(value)
                    return True


            def test_is_unique():

                data = ['a', 'b', 'a', 'c']  # <- 'a' is not unique

                validate(data, IsUnique())

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 23

            from datatest import DataTestCase
            from datatest import Extra


            class IsUnique(object):
                """values should be unique"""
                def __init__(self):
                    self.values = set()

                def __call__(self, value):
                    if value in self.values:
                        return Extra(value)
                    self.values.add(value)
                    return True


            class MyTest(DataTestCase):

                def test_is_unique(self):

                    data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                    self.assertValid(data, IsUnique())


Quick-and-Dirty Approach
========================

For a simpler but more limited method, we can count the items
with :py:class:`collections.Counter` and then assert that the
counts are equal to ``1``:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from collections import Counter
            from datatest import validate


            def test_is_unique():

                data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                validate(Counter(data), 1)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from collections import Counter
            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_is_unique(self):

                    data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                    self.assertValid(Counter(data), 1)

    When using a :py:class:`Counter <collections.Counter>` in
    this way, tests are limited to lists and other non-tuple,
    non-mapping iterables.
