
.. py:currentmodule:: datatest

.. meta::
    :description: How to assert subset and superset relations.
    :keywords: datatest, validate, sets, subsets, supersets


############################################
How to Validate Sets, Subsets, and Supersets
############################################

To check for set membership, you can simply pass a :py:class:`set`
as the *requirement* argument.

.. tabs::

    .. group-tab:: Pytest

        The :func:`validate` function automatically checks data
        elements for membership in a required set:

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate


            def test_required_set():

                data = ['A', 'A', 'B', 'B', 'C', 'C']

                requirement = {'A', 'B', 'C'}  # <- a set

                validate(data, requirement)

        If the requirement is not a set, you can check for set membership
        explicitly with the :meth:`validate.set` method:

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate


            def test_required_set():

                data = ['A', 'A', 'B', 'B', 'C', 'C']

                requirement = ['A', 'B', 'C']  # <- not a set

                validate.set(data, requirement)

    .. group-tab:: Unittest

        The :meth:`assertValid() <DataTestCase.assertValid>` method
        automatically checks data elements for membership in a required
        set:

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_required_set(self):

                    data = ['A', 'A', 'B', 'B', 'C', 'C']

                    requirement = {'A', 'B', 'C'}  # <- a set

                    self.assertValid(data, requirement)

        If the requirement is not a set, you can check for set membership
        explicitly with the :meth:`assertValidSet() <DataTestCase.assertValidSet>`
        method:

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_required_set(self):

                    data = ['A', 'A', 'B', 'B', 'C', 'C']

                    requirement = ['A', 'B', 'C']  # <- not a set

                    self.assertValidSet(data, requirement)


=====================
Subsets and Supersets
=====================

To check for subset and superset relationships, use the following
methods:

.. tabs::

    .. group-tab:: Pytest

        * :meth:`validate.subset`
        * :meth:`validate.superset`

    .. group-tab:: Unittest

        * :meth:`assertValidSubset() <DataTestCase.assertValidSubset>`
        * :meth:`assertValidSuperset() <DataTestCase.assertValidSuperset>`

