
.. module:: datatest

.. meta::
    :description: How to assert unique values.
    :keywords: datatest, unique, find duplicates


###########################
How to Check for Uniqueness
###########################

To checck that values are unique, we can define a group-requirement
that generates :class:`Extra` differences when duplicate values are
encountered.

You can copy the ``is_unique()`` function to use in your own tests:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 21

            from datatest import validate
            from datatest import group_requirement
            from datatest import Extra


            @group_requirement
            def is_unique(iterable):
                """values should be unique"""
                seen = set()
                for element in iterable:
                    if element in seen:
                        yield Extra(element)
                    else:
                        seen.add(element)


            def test_unique_data():

                data = ['a', 'b', 'a', 'c']  # <- 'a' is not unique

                validate(data, is_unique)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 23

            from datatest import DataTestCase
            from datatest import group_requirement
            from datatest import Extra


            @group_requirement
            def is_unique(iterable):
                """values should be unique"""
                seen = set()
                for element in iterable:
                    if element in seen:
                        yield Extra(element)
                    else:
                        seen.add(element)


            class MyTest(DataTestCase):

                def test_unique_data(self):

                    data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                    self.assertValid(data, is_unique)


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


            def test_unique_data():

                data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                validate(Counter(data), 1)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from collections import Counter
            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_unique_data(self):

                    data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                    self.assertValid(Counter(data), 1)

    When using a :py:class:`Counter <collections.Counter>` in
    this way, tests are limited to lists and other non-tuple,
    non-mapping iterables.
