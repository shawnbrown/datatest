
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
            :emphasize-lines: 22

            from datatest import validate
            from datatest import Extra


            def make_is_unique():
                previously_seen = set()

                def is_unique(value):
                    """values should be unique"""
                    if value in previously_seen:
                        return Extra(value)
                    previously_seen.add(value)
                    return True

                return is_unique


            def test_is_unique():

                data = ['a', 'b', 'a', 'c']  # <- 'a' is not unique

                is_unique = make_is_unique()

                validate(data, is_unique)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 24

            from datatest import DataTestCase
            from datatest import Extra


            def make_is_unique():
                previously_seen = set()

                def is_unique(value):
                    """values should be unique"""
                    if value in previously_seen:
                        return Extra(value)
                    previously_seen.add(value)
                    return True

                return is_unique


            class MyTest(DataTestCase):

                def test_is_unique(self):

                    data = ['a', 'a', 'b', 'c']  # <- 'a' is not unique

                    is_unique = make_is_unique()

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
