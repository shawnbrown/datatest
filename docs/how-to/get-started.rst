
.. module:: datatest

.. meta::
    :description: How to get started.
    :keywords: datatest, example, getting started


##################
How to Get Started
##################

.. sidebar:: Example Data

    The samples here are written to test the following
    :download:`example.csv </_static/example.csv>`:

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

Once you have reviewed the tutorials and have a basic understanding
of datatest, you should be ready to start testing your own data.


====================================
1. Copy One of the Following Samples
====================================

A simple way to get started is to create a **.py** file in the same
folder as the data you want to test. Then, copy one of the following
code samples into your file and begin changing the tests to suit your
own data. It's a good idea to follow established testing conventions
and make sure your filename starts with "**test\_**".


Using a DataFrame Fixture
-------------------------

This sample demonstrates using a pandas ``DataFrame`` object and follows
common pandas conventions (e.g., importing pandas as ``pd``, etc.):

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :linenos:

            import pytest
            import pandas as pd
            import datatest as dt


            @pytest.fixture(scope='module')
            @dt.working_directory(__file__)
            def df():
                return pd.read_csv('example.csv')


            def test_column_names(df):
                required_names = {'A', 'B', 'C'}
                dt.validate(df.columns, required_names)


            def test_a(df):
                data = df['A'].values
                requirement = {'x', 'y', 'z'}
                dt.validate(data, requirement)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main([__file__]))

    .. group-tab:: Unittest

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt


            @dt.working_directory(__file__)
            def setUpModule():
                global df
                df = pd.read_csv('example.csv')


            class TestMyData(dt.DataTestCase):
                def test_column_names(self):
                    required_names = {'A', 'B', 'C'}
                    self.assertValid(df.columns, required_names)

                def test_a(self):
                    data = df['A'].values
                    requirement = {'x', 'y', 'z'}
                    self.assertValid(data, requirement)

                # ...add more tests here...


            if __name__ == '__main__':
                dt.main()


Using Datatest's Built-in Tools
-------------------------------

This sample uses datatest's built-in :class:`Selector <datatest.Selector>`
object for loading and querying data. This does not require any additional
dependencies

The ``Selector`` syntax tries to be friendly by returning data in the same
format in which it was selected---e.g., selecting ``{'A': ('B', 'C')}`` will
return a dictionary whose keys are made from column "A" and whose values
are two-tuples made from columns "B" and "C":

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :linenos:

            import pytest
            from datatest import (
                validate,
                allowed,
                Selector,
                working_directory,
            )


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def select():
                return Selector('example.csv')


            def test_column_names(select):
                required_names = {'A', 'B', 'C'}
                validate(select.fieldnames, required_names)


            def test_a(select):
                data = select('A')
                required_values = {'x', 'y', 'z'}
                validate(data, required_values)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))

    .. group-tab:: Unittest

        .. code-block:: python
            :linenos:

            from datatest import (
                DataTestCase,
                Selector,
                working_directory,
            )


            @working_directory(__file__)
            def setUpModule():
                global select
                select = Selector('example.csv')


            class TestMyData(DataTestCase):
                def test_column_names(self):
                    required_names = {'A', 'B', 'C'}
                    self.assertValid(select.fieldnames, required_names)

                def test_a(self):
                    data = select('A')
                    required_values = {'x', 'y', 'z'}
                    self.assertValid(data, required_values)

                # ...add more tests here...


            if __name__ == '__main__':
                from datatest import main
                main()


=================================
2. Adapt the Sample for Your Data
=================================

After copying the sample script into your own file, you can begin to
adapt it to meet your own needs:

1. Change the fixture to use your data (instead of "example.csv").
2. Update the set in ``test_column_names()`` to require the names your
   data should contain (instead of "A", "B", and "C").
3. Rename ``test_a()`` and change it to check values in one of the
   columns in your data.
4. Add more tests appropriate for your own data requirements.


===================================
3. Refactor Your Tests as They Grow
===================================

As your tests grow, look to structure them into related groups. Start
by creating separate classes to contain groups of related test cases.
And as you develop more and more classes, create separate modules to
hold groups of related classes. If you are using ``pytest``, move your
fixtures into a ``conftest.py`` file.
