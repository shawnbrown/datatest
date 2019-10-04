
.. currentmodule:: datatest

.. meta::
    :description: How to use a datatest.Select fixture.
    :keywords: datatest, select, fixture


################################
How to Use Select Class Fixtures
################################

The following examples demonstrate different ways to use
the :class:`datatest.Select` class as a fixture.


Inline Data
===========

In this example, the :class:`Select <datatest.Select>` reads data
from a list of records. The fixture is then queried to produce data
for validation.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8-18,22,28

            import pytest
            from datatest import (
                validate,
                Select,
            )


            @pytest.fixture(scope='module')
            def mydata():
                return Select([
                    ['A', 'B', 'C'],
                    ['x', 'foo', 20],
                    ['x', 'foo', 30],
                    ['y', 'foo', 10],
                    ['y', 'bar', 20],
                    ['z', 'bar', 10],
                    ['z', 'bar', 10],
                ])


            def test_total(mydata):
                total = mydata('C').sum()
                requirement = 100
                validate(total, requirement)


            def test_subtotals(mydata):
                subtotals = mydata({'A': 'C'}).sum()
                requirement = {'x': 50, 'y': 30, 'z': 20}
                validate(subtotals, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7-17,22,27

            from datatest import (
                DataTestCase,
                Select,
            )


            def setUpModule():
                global mydata
                mydata = Select([
                    ['A', 'B', 'C'],
                    ['x', 'foo', 20],
                    ['x', 'foo', 30],
                    ['y', 'foo', 10],
                    ['y', 'bar', 20],
                    ['z', 'bar', 10],
                    ['z', 'bar', 10],
                ])


            class MyTest(DataTestCase):
                def test_total(self):
                    total = mydata('C').sum()
                    requirement = 100
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata({'A': 'C'}).sum()
                    requirement = {'x': 50, 'y': 30, 'z': 20}
                    self.assertValid(subtotals, requirement)


External File
=============

In this example, the :class:`Select <datatest.Select>` reads data
from a CSV file (:download:`example.csv </_static/example.csv>`).


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 5,10-12

            import pytest
            from datatest import (
                validate,
                Select,
                working_directory,
            )


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Select('example.csv')


            def test_total(mydata):
                total = mydata('C').sum()
                requirement = 100
                validate(total, requirement)


            def test_subtotals(mydata):
                subtotals = mydata({'A': 'C'}).sum()
                requirement = {'x': 50, 'y': 30, 'z': 20}
                validate(subtotals, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 4,10-11

            from datatest import (
                DataTestCase,
                Select,
                working_directory,
            )


            def setUpModule():
                global mydata
                with working_directory(__file__):
                    mydata = Select('example.csv')


            class MyTest(DataTestCase):
                def test_total(self):
                    total = mydata('C').sum()
                    requirement = 100
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata({'A': 'C'}).sum()
                    requirement = {'x': 50, 'y': 30, 'z': 20}
                    self.assertValid(subtotals, requirement)


Reference Data
==============

A second fixture is used as a trusted source of reference data.
Instead of in-lining the *requirement* value, it is queried
from the reference data.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 15-22,27,33

            import pytest
            from datatest import (
                validate,
                Select,
                working_directory,
            )


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Select('example.csv')


            @pytest.fixture(scope='module')
            def refdata():
                return Select([
                    ['A', 'C'],
                    ['x', 50],
                    ['y', 30],
                    ['z', 20],
                ])


            def test_total(mydata, refdata):
                total = mydata('C').sum()
                requirement = refdata('C').sum()
                validate(total, requirement)


            def test_subtotals(mydata, refdata):
                subtotals = mydata({'A': 'C'}).sum()
                requirement = refdata({'A': 'C'}).sum()
                validate(subtotals, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10,15-20,26,31

            from datatest import (
                DataTestCase,
                Select,
                working_directory,
            )


            def setUpModule():
                global mydata
                global refdata

                with working_directory(__file__):
                    mydata = Select('example.csv')

                refdata = Select([
                    ['A', 'C'],
                    ['x', 50],
                    ['y', 30],
                    ['z', 20],
                ])


            class MyTest(DataTestCase):
                def test_total(self):
                    total = mydata('C').sum()
                    requirement = refdata('C').sum()
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata({'A': 'C'}).sum()
                    requirement = refdata({'A': 'C'}).sum()
                    self.assertValid(subtotals, requirement)


RepeatingContainer
==================

With a :class:`RepeatingContainer <datatest.RepeatingContainer>`,
you can run a query on multiple sources with a single statement.

This eliminates the query duplication seen in the previous example.
The results are unpacked into the *data* and *requirement*
arguments (using the asterisk notation ``*...``) directly in the
validation call.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6,26-28,32,36

            import pytest
            from datatest import (
                validate,
                Select,
                working_directory,
                RepeatingContainer,
            )


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Select('example.csv')


            @pytest.fixture(scope='module')
            def refdata():
                return Select([
                    ['A', 'C'],
                    ['x', 50],
                    ['y', 30],
                    ['z', 20],
                ])


            @pytest.fixture(scope='module')
            def compare(mydata, refdata):
                return RepeatingContainer([mydata, refdata])


            def test_total(compare):
                validate(*compare('C').sum())


            def test_subtotals(compare):
                validate(*compare({'A': 'C'}).sum())


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 5,12,24,29,32

            from datatest import (
                DataTestCase,
                Select,
                working_directory,
                RepeatingContainer,
            )


            def setUpModule():
                global mydata
                global refdata
                global compare

                with working_directory(__file__):
                    mydata = Select('example.csv')

                refdata = Select([
                    ['A', 'C'],
                    ['x', 50],
                    ['y', 30],
                    ['z', 20],
                ])

                compare = RepeatingContainer([mydata, refdata])


            class MyTest(DataTestCase):
                def test_total(self):
                    self.assertValid(*compare('C').sum())

                def test_subtotals(self):
                    self.assertValid(*compare({'A': 'C'}).sum())
