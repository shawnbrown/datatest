
.. module:: datatest

.. meta::
    :description: How to Assert Column Names.
    :keywords: datatest, column names, columns, fieldnames


##########################
How to Assert Column Names
##########################


To check that a file contains the expected column names, we can use a
:class:`Selector` and validate its :attr:`fieldnames <Selector.fieldnames>`
using a required set:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 13-15

            import pytest
            from datatest import validate


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Selector('mydata.csv')


            def test_columns(mydata):

                required_columns = {'A', 'B', 'C'}

                validate(mydata.fieldnames, required_columns)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 15-17

            import pytest
            from datatest import validate


            def setUpModule():
                global mydata
                with working_directory(__file__):
                    mydata = Selector('mydata.csv')


            class TestMyData(DataTestCase):

                def test_columns(self):

                    required_columns = {'A', 'B', 'C'}

                    self.assertValid(mydata.fieldnames, required_columns)


The example above checks for column names in any order (sets are
unordered). If we want to make sure that column names appear in a
specific order, we can validate the fieldnames using a list:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 5

            ...

            def test_columns(mydata):

                required_columns = ['A', 'B', 'C']

                validate(mydata.fieldnames, required_columns)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7

            ...

            class TestMyData(DataTestCase):

                def test_columns(self):

                    required_columns = ['A', 'B', 'C']

                    self.assertValid(mydata.fieldnames, required_columns)


If we want to assert that a file contains a minimum set of
required columns (but may include additional columns), we can
use an allowance:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate, allowed

            ...

            def test_columns(mydata):

                required_columns = {'A', 'B', 'C'}

                with allowed.extra():
                    validate(mydata.fieldnames, required_columns)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 9

            ...

            class TestMyData(DataTestCase):

                def test_columns(self):

                    required_columns = {'A', 'B', 'C'}

                    with self.allowedExtra():
                        self.assertValid(mydata.fieldnames, required_columns)


If we don't care exactly what the column names are but we
want to check that they're upper-case, we can use a predicate
function:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 5-6

            ...

            def test_columns(mydata):

                def uppercase(value):
                    return value.isupper()

                validate(mydata.fieldnames, uppercase)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7-8

            ...

            class TestMyData(DataTestCase):

                def test_columns(self):

                    def uppercase(value):
                        return value.isupper()

                    self.assertValid(mydata.fieldnames, uppercase)

