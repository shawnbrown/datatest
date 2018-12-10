
.. module:: datatest

.. meta::
    :description: How to validate column names.
    :keywords: datatest, column names, columns, fieldnames


############################
How to Validate Column Names
############################

To validate column names, we need pass the names as they appear and
the names we're expecting to the :func:`validate` function (or the
:meth:`assertValid() <DataTestCase.assertValid>` method if we're
writing unittest-style tests).


=============
Some Examples
=============

**Selector:** The columns names of a :class:`datatest.Selector` can be
accessed with the :attr:`fieldnames <Selector.fieldnames>` attribute.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 11

            from datatest import validate
            from datatest import Selector


            def test_columns():

                mydata = Selector('mydata.csv')

                required_columns = {'A', 'B', 'C'}

                validate(mydata.fieldnames, required_columns)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 13

            from datatest import DataTestCase
            from datatest import Selector


            class TestMyData(DataTestCase):

                def test_columns(self):

                    mydata = Selector('mydata.csv')

                    required_columns = {'A', 'B', 'C'}

                    self.assertValid(mydata.fieldnames, required_columns)


**DataFrame:** The columns names of a ``pandas.DataFrame`` can be
accessed with the ``columns`` attribute.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 11

            import pandas as pd
            import datatest as dt


            def test_columns():

                mydata = pd.read_csv('mydata.csv')  # <- Creates DataFrame.

                required_columns = {'A', 'B', 'C'}

                validate(mydata.columns, required_columns)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 13

            import pandas as pd
            import datatest as dt


            class TestMyData(dt.DataTestCase):

                def test_columns(self):

                    mydata = pd.read_csv('mydata.csv')  # <- Creates DataFrame.

                    required_columns = {'A', 'B', 'C'}

                    self.assertValid(mydata.columns, required_columns)


==============
Other Criteria
==============

The examples above check that the column names are members of a given
:py:class:`set`. But because sets are unordered, we are not validating
the order of these columns---only that they exist.

**Column Order:** If we want to validate the order the columns, we
can use a :py:class:`list` of ``required_columns`` (instead instead of
a set).

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate
            from datatest import Selector


            def test_columns():

                mydata = Selector('mydata.csv')

                required_columns = ['A', 'B', 'C']  # <- Checks order.

                validate(mydata.fieldnames, required_columns)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from datatest import DataTestCase
            from datatest import Selector


            class TestMyData(DataTestCase):

                def test_columns(self):

                    mydata = Selector('mydata.csv')

                    required_columns = ['A', 'B', 'C']  # <- Checks order.

                    self.assertValid(mydata.fieldnames, required_columns)


**Column Format:** If we don't care exactly what the column names are
but we want to check that they conform to a specific format, we can use
a predicate **function**:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9-11

            from datatest import validate
            from datatest import Selector


            def test_columns():

                mydata = Selector('mydata.csv')

                def required_format(value):
                    """must be upper case"""
                    return value.isupper()

                validate(mydata.fieldnames, required_format)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11-13

            from datatest import DataTestCase
            from datatest import Selector


            class TestMyData(DataTestCase):

                def test_columns(self):

                    mydata = Selector('mydata.csv')

                    def required_format(value):
                        """must be upper case"""
                        return value.isupper()

                    self.assertValid(mydata.fieldnames, required_format)
