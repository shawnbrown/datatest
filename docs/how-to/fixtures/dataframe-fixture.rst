
.. currentmodule:: datatest

.. meta::
    :description: How to use a pandas.DataFrame fixture.
    :keywords: datatest, pandas, DataFrame, fixture


#############################
How to Use DataFrame Fixtures
#############################

The following examples demonstrate different ways to use
the ``pandas.DataFrame`` class as a fixture.


Inline Data
===========

In this example, the ``DataFrame`` reads data from a list of records.
The fixture is then queried to produce data for validation.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6-18,22,28

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='module')
            def mydata():
                return pd.DataFrame(
                    data=[
                        ['x', 'foo', 20],
                        ['x', 'foo', 30],
                        ['y', 'foo', 10],
                        ['y', 'bar', 20],
                        ['z', 'bar', 10],
                        ['z', 'bar', 10],
                    ],
                    columns=['A', 'B', 'C'],
                )


            def test_total(mydata):
                total = mydata['C'].sum()
                requirement = 100
                dt.validate(total, requirement)


            def test_subtotals(mydata):
                subtotals = mydata[['A', 'C']].groupby('A').sum()
                requirement = {'x': 50, 'y': 30, 'z': 20}
                dt.validate(subtotals, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7-17,22,27

            import pandas as pd
            import datatest as dt


            def setUpModule():
                global mydata
                mydata = pd.DataFrame(
                    data=[
                        ['x', 'foo', 20],
                        ['x', 'foo', 30],
                        ['y', 'foo', 10],
                        ['y', 'bar', 20],
                        ['z', 'bar', 10],
                        ['z', 'bar', 10],
                    ],
                    columns=['A', 'B', 'C'],
                )


            class MyTest(dt.DataTestCase):
                def test_total(self):
                    total = mydata['C'].sum()
                    requirement = 100
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata[['A', 'C']].groupby('A').sum()
                    requirement = {'x': 50, 'y': 30, 'z': 20}
                    self.assertValid(subtotals, requirement)


External File
=============

In this example, the ``DataFrame`` reads data from a CSV file
(:download:`example.csv </_static/example.csv>`).

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6-9

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='module')
            @dt.working_directory(__file__)
            def mydata():
                return pd.read_csv('example.csv')


            def test_total(mydata):
                total = mydata['C'].sum()
                requirement = 100
                dt.validate(total, requirement)


            def test_subtotals(mydata):
                subtotals = mydata[['A', 'C']].groupby('A').sum()
                requirement = {'x': 50, 'y': 30, 'z': 20}
                dt.validate(subtotals, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 5-8

            import pandas as pd
            import datatest as dt


            def setUpModule():
                global mydata
                with dt.working_directory(__file__):
                    mydata = pd.read_csv('example.csv')


            class MyTest(dt.DataTestCase):
                def test_total(self):
                    total = mydata['C'].sum()
                    requirement = 100
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata[['A', 'C']].groupby('A').sum()
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
            :emphasize-lines: 12-21,26,32

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='module')
            @dt.working_directory(__file__)
            def mydata():
                return pd.read_csv('example.csv')


            @pytest.fixture(scope='module')
            def refdata():
                return pd.DataFrame(
                    data=[
                        ['x', 50],
                        ['y', 30],
                        ['z', 20],
                    ],
                    columns=['A', 'C'],
                )


            def test_total(mydata, refdata):
                total = mydata['C'].sum()
                requirement = refdata['C'].sum()
                dt.validate(total, requirement)


            def test_subtotals(mydata, refdata):
                subtotals = mydata[['A', 'C']].groupby('A').sum()
                requirement = refdata[['A', 'C']].groupby('A').sum()
                dt.validate(subtotals, requirement)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7,12-19,25,30

            import pandas as pd
            import datatest as dt


            def setUpModule():
                global mydata
                global refdata

                with dt.working_directory(__file__):
                    mydata = pd.read_csv('example.csv')

                refdata = pd.DataFrame(
                    data=[
                        ['x', 50],
                        ['y', 30],
                        ['z', 20],
                    ],
                    columns=['A', 'C'],
                )


            class MyTest(dt.DataTestCase):
                def test_total(self):
                    total = mydata['C'].sum()
                    requirement = refdata['C'].sum()
                    self.assertValid(total, requirement)

                def test_subtotals(self):
                    subtotals = mydata[['A', 'C']].groupby('A').sum()
                    requirement = refdata[['A', 'C']].groupby('A').sum()
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
            :emphasize-lines: 24-26,30,34

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='module')
            @dt.working_directory(__file__)
            def mydata():
                return pd.read_csv('example.csv')


            @pytest.fixture(scope='module')
            def refdata():
                return pd.DataFrame(
                    data=[
                        ['x', 50],
                        ['y', 30],
                        ['z', 20],
                    ],
                    columns=['A', 'C'],
                )


            @pytest.fixture(scope='module')
            def compare(mydata, refdata):
                return dt.RepeatingContainer([mydata, refdata])


            def test_total(compare):
                dt.validate(*compare['C'].sum())


            def test_subtotals(compare):
                dt.validate(*compare[['A', 'C']].groupby('A').sum())


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 8,22,27,30

            import pandas as pd
            import datatest as dt


            def setUpModule():
                global mydata
                global refdata
                global compare

                with dt.working_directory(__file__):
                    mydata = pd.read_csv('example.csv')

                refdata = pd.DataFrame(
                    data=[
                        ['x', 50],
                        ['y', 30],
                        ['z', 20],
                    ],
                    columns=['A', 'C'],
                )

                compare = dt.RepeatingContainer([mydata, refdata])


            class MyTest(dt.DataTestCase):
                def test_total(self):
                    self.assertValid(*compare['C'].sum())

                def test_subtotals(self):
                    self.assertValid(*compare[['A', 'C']].groupby('A').sum())

