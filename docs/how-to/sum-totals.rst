
.. module:: datatest

.. meta::
    :description: How to assert sum totals.
    :keywords: datatest, validate, sum, total


########################
How to Assert Sum Totals
########################

To check sum totals from a file, you would select data from a column,
sum the values, and then validate the result against a required number
or numbers.

The examples below will use the following data (:download:`example.csv
</_static/example.csv>`):

    ===  ===  ===
     A    B    C
    ===  ===  ===
     x   foo   20
     x   foo   30
     y   foo   10
     y   bar   20
     z   bar   10
     z   bar   10
    ===  ===  ===


Using a Datatest Selector
=========================

This example shows how to sum and validate totals from a CSV file
using datatest's :class:`Selector` class:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 15,22,31

            import pytest
            from datatest import validate
            from datatest import working_directory
            from datatest import Selector


            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def mydata():
                return Selector('example.csv')


            def test_total(mydata):

                summed = mydata('C').sum()

                validate(summed, 100)


            def test_subtotals(mydata):

                summed = mydata({'A': 'C'}).sum()

                requirement = {'x': 50, 'y': 30, 'z': 20}

                validate(summed, requirement)


            def test_filtered_subtotals(mydata):

                summed = mydata({'A': 'C'}, 'B'='foo').sum()

                requirement = {'x': 50, 'y': 10}

                validate(summed, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 16,22,30

            from datatest import DataTestCase
            from datatest import working_directory
            from datatest import Selector


            def setUpModule():
                global mydata
                with working_directory(__file__):
                    mydata = Selector('example.csv')


            class MyTest(DataTestCase):

                def test_total(self):

                    summed = mydata('C').sum()

                    self.assertValid(summed, 4)

                def test_subtotals(self):

                    summed = mydata({'A': 'C').sum()

                    requirement = {'A': 4, 'B': 3}

                    self.assertValid(summed, requirement)

                def test_filtered_subtotals(self):

                    summed = mydata({'A': 'C'}, 'B'='foo').sum()

                    requirement = {'x': 50, 'y': 10}

                    self.assertValid(summed, requirement)


For a more complete demonstration of  datatest's :class:`Selector`
support, see the :doc:`/tutorial/querying-data` tutorial.


Using a Pandas DataFrame
========================

This example shows how to sum and validate totals from a CSV file
using a Pandas ``DataFrame`` class:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 14,21,30

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='session')
            @dt.working_directory(__file__)
            def mydata():
                return pd.read_csv('example.csv')  # <- returns DataFrame


            def test_total(mydata):

                summed = mydata['C'].sum()

                dt.validate(summed, 100)


            def test_subtotals(mydata):

                summed = mydata[['A', 'C']].groupby('A').sum()

                requirement = {'x': 50, 'y': 30, 'z': 20}

                dt.validate(summed, requirement)


            def test_filtered_subtotals(mydata):

                summed = mydata[['A', 'C']][mydata['B'] == 'foo'].groupby('A').sum()

                requirement = {'x': 50, 'y': 10}

                dt.validate(summed, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 15,21,29

            import pandas as pd
            import datatest as dt


            def setUpModule():
                global mydata
                with dt.working_directory(__file__):
                    mydata = pd.read_csv('example.csv')  # <- returns DataFrame


            class MyTest(DataTestCase):

                def test_total(self):

                    summed = mydata['C'].sum()

                    self.assertValid(summed, 100)

                def test_subtotals(self):

                    summed = mydata[['A', 'C']].groupby('A').sum()

                    requirement = {'x': 50, 'y': 30, 'z': 20}

                    self.assertValid(summed, requirement)

                def test_filtered_subtotals(self):

                    summed = mydata[['A', 'C']][mydata['B'] == 'foo'].groupby('A').sum()

                    requirement = {'x': 50, 'y': 10}

                    self.assertValid(summed, requirement)

