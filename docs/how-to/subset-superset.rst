
.. module:: datatest

.. meta::
    :description: How to assert subset and superset relations.
    :keywords: datatest, validate, subset, superset


#####################################
How to Validate Subsets and Supersets
#####################################

When given a :py:class:`set` requirement, the :func:`validate` function's
default behavior checks data elements for membership in the set. But if you
need to check for subset or superset relations you can use the following
approaches.


===============
With Allowances
===============

**Subset:** To require that a collection of data contains all of the
values from a given subset, you can use a :py:class:`set` requirement
together with an allowance for :class:`Extra` differences:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 11-12

            from datatest import validate
            from datatest import allowed


            def test_required_subset():

                data = ['A', 'B', 'C', 'D']

                my_required_subset = {'A', 'B', 'C'}

                with allowed.extra():
                    validate(data, my_required_subset)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 12-13

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_required_subset(self):

                    data = ['A', 'B', 'C', 'D']

                    my_required_subset = {'A', 'B', 'C'}

                    with self.allowedExtra():
                        self.assertValid(data, my_required_subset)


**Superset:** To require that a collection of data contains only values
from a given superset, you can use a :py:class:`set` requirement together
with an allowance for :class:`Missing` differences:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9-10

            ...

            def test_required_superset():

                data = ['A', 'B', 'C']

                my_required_superset = {'A', 'B', 'C', 'D'}

                with allowed.missing():
                    self.assertValid(data, my_required_superset)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 13-14

            ...

            class MyTest(DataTestCase):

                ...

                def test_required_superset(self):

                    data = ['A', 'B', 'C']

                    my_required_superset = {'A', 'B', 'C', 'D'}

                    with self.allowedMissing():
                        self.assertValid(data, my_required_superset)


==========================
With Requirement Functions
==========================

For most cases, the allowance-based approaches given above are
perfectly adequate. That said, it is always less efficient to
use an allowance than it is to not have differences in the first
place.

If a set contained thousands of unique differences, an allowance-based
approach would instantiate thousands of difference objects which are
then discarded by the allowance. It would be more efficient to skip
the creation of those differences that are going to be allowed anyway.

To implement this more efficient approach, you can use the following
``required_subset()`` and ``required_superset()`` functions in your
own tests:


.. code-block:: python

    from datatest import group_requirement
    from datatest import Missing
    from datatest import Extra


    def required_subset(subset):
        """Require that data contains all elements of *subset*."""
        if not isinstance(subset, set):
            raise TypeError('requirement must be set')

        @group_requirement
        def _required_subset(iterable):
            """must contain all elements of given subset"""
            missing = subset.copy()
            for element in iterable:
                if not missing:
                    break
                missing.discard(element)
            return (Missing(element) for element in missing)

        return _required_subset


    def required_superset(superset):
        """Require that data contains only elements of *superset*."""
        if not isinstance(superset, set):
            raise TypeError('requirement must be set')

        @group_requirement
        def _required_superset(iterable):
            """may contain only elements of given superset"""
            extras = set()
            for element in iterable:
                if element not in superset:
                    extras.add(element)
            return (Extra(element) for element in extras)

        return _required_superset


Example Usage
-------------

Use of the ``required_subset()`` and ``required_superset()`` requirements
are demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 10,19

            from datatest import validate
            from datatest import allowed

            ...

            def test_required_subset():

                data = ['A', 'B', 'C', 'D']

                subset = required_subset({'A', 'B', 'C'})

                validate(data, subset)


            def test_required_superset():

                data = ['A', 'B', 'C']

                superset = required_superset({'A', 'B', 'C', 'D'})

                validate(data, superset)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11,19

            from datatest import DataTestCase

            ...

            class MyTest(DataTestCase):

                def test_required_subset(self):

                    data = ['A', 'B', 'C', 'D']

                    subset = required_subset({'A', 'B', 'C'})

                    self.assertValid(data, subset)

                def test_required_superset():

                    data = ['A', 'B', 'C']

                    superset = required_superset({'A', 'B', 'C', 'D'})

                    self.assertValid(data, superset)
