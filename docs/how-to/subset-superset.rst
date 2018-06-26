
.. module:: datatest

.. meta::
    :description: How to assert subset and superset relations.
    :keywords: datatest, validate, subset, superset


###################################
How to Assert Subsets and Supersets
###################################

==============
A Single Check
==============

You can check for a **subset** relationship by using a
:py:class:`set` *requirement* and allowing :class:`Missing`
differences.

And you can check for a **superset** relationship by using
a :py:class:`set` *requirement* and allowing :class:`Extra`
differences.

See the following examples:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9,11,19,21

            from datatest import validate
            from datatest import allowed


            def test_subset():

                data = ['A', 'B', 'C']

                requirement = {'A', 'B', 'C', 'D'}  # <- Use set requirement.

                with allowed.missing():             # <- And allow Missing.
                    validate(data, requirement)


            def test_superset():

                data = ['A', 'B', 'C', 'D']

                requirement = {'A', 'B', 'C'}  # <- Use set requirement.

                with allowed.extra():          # <- And allow Extra.
                    validate(data, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10,12,19,21

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_subset(self):

                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B', 'C', 'D'}  # <- Use set requirement.

                    with self.allowedMissing():         # <- And allow Missing.
                        self.assertValid(data, requirement)

                def test_superset(self):

                    data = ['A', 'B', 'C', 'D']

                    requirement = {'A', 'B', 'C'}  # <- Use set requirement.

                    with self.allowedExtra():      # <- And allow Extra.
                        self.assertValid(data, requirement)


=========================
Reusable Helper Functions
=========================

If you need to assert subset and superset relationships many times,
you may want to wrap this behavior in a helper function or method:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 33,42

            from datatest import validate
            from datatest import allowed


            def validate_subset(data, requirement):
                """Pass without error if *data* is a subset of *requirement*."""
                if not isinstance(requirement, set):
                    requirement = set(requirement)

                __tracebackhide__ = True

                with allowed.missing():
                    validate(data, requirement)


            def validate_superset(data, requirement):
                """Pass without error if *data* is a superset of *requirement*."""
                if not isinstance(requirement, set):
                    requirement = set(requirement)

                __tracebackhide__ = True

                with allowed.extra():
                    validate(data, requirement)


            def test_subset():

                data = ['A', 'B', 'C']

                requirement = {'A', 'B', 'C', 'D'}

                validate_subset(data, requirement)


            def test_superset():

                data = ['A', 'B', 'C', 'D']

                requirement = {'A', 'B', 'C'}

                validate_superset(data, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 29,37

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def assertSubset(self, data, requirement):  # <- HELPER METHOD!
                    """Pass without error if *data* is a subset of *requirement*."""
                    if not isinstance(requirement, set):
                        requirement = set(requirement)

                    with self.allowedMissing():
                        self.assertValid(data, requirement)


                def assertSuperset(self, data, requirement):  # <- HELPER METHOD!
                    """Pass without error if *data* is a superset of *requirement*."""
                    if not isinstance(requirement, set):
                        requirement = set(requirement)

                    with self.allowedExtra():
                        self.assertValid(data, requirement)

                def test_subset(self):

                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B', 'C', 'D'}

                    self.assertSubset(data, requirement)

                def test_superset(self):

                    data = ['A', 'B', 'C', 'D']

                    requirement = {'A', 'B', 'C'}

                    self.assertSuperset(data, requirement)
