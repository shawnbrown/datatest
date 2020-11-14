
.. currentmodule:: datatest

.. meta::
    :description: Examples showing how to use datatest together with
                  testing frameworks like pytest and unittest.
    :keywords: etl, elt, data, automated, testing, pytest, unittest, python


######################
Automated Data Testing
######################

In addition to being used directly in your own projects, you can also
use Datatest with a testing framework like pytest_ or unittest_.
Automated testing of data is a good solution when you need to validate
and manage:

* batch data before loading
* datasets for an important project
* datasets intended for publication
* status of a long-lived, critical data system
* comparisons between your data and some reference data
* data migration projects
* complex data-wrangling processes

.. _pytest: https://pytest.org
.. _unittest: https://docs.python.org/library/unittest.html


Data testing is a form of *acceptance testing*---akin to operational
acceptance testing. Using an incremental approach, we check that data
properties satisfy certain requirements. A test suite should include as
many tests as necessary to determine if a dataset is *fit for purpose*.


******
Pytest
******

With pytest, you can use datatest functions and classes just
as you would in any other context. And you can run pytest using
its normal, console interface (see :ref:`pytest:usage`).

To facilitate incremental testing, datatest implements a
"mandatory" marker to stop the session early when a mandatory
test fails:

.. code-block:: python
    :emphasize-lines: 1

    @pytest.mark.mandatory
    def test_columns():
        ...

You can also use the ``-x`` option to stop testing after the first
failure of any test:

.. code-block:: console

    pytest -x

If needed, you can use ``--ignore-mandatory`` to ignore "mandatory"
markers and continue testing even when a mandatory test fails:

.. code-block:: console

    pytest --ignore-mandatory


Pytest Samples
==============

.. start-inclusion-marker-pytestsamples

.. tabs::

    .. group-tab:: Pandas

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pytest
            import pandas as pd
            from datatest import (
                validate,
                accepted,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def df():
                return pd.read_csv('example.csv')


            @pytest.mark.mandatory
            def test_column_names(df):
                required_names = {'A', 'B', 'C'}
                validate(df.columns, required_names)


            def test_a(df):
                requirement = {'x', 'y', 'z'}
                validate(df['A'], requirement)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))

    .. group-tab:: Pandas (itegrated)

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pytest
            import pandas as pd
            from datatest import (
                register_accessors,
                accepted,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def df():
                return pd.read_csv('example.csv')


            @pytest.fixture(scope='session', autouse=True)
            def pandas_integration():
                register_accessors()


            @pytest.mark.mandatory
            def test_column_names(df):
                required_names = {'A', 'B', 'C'}
                df.columns.validate(required_names)


            def test_a(df):
                requirement = {'x', 'y', 'z'}
                df['A'].validate(requirement)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))

    .. group-tab:: Squint

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pytest
            import squint
            from datatest import (
                validate,
                accepted,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def select():
                return squint.Select('example.csv')


            @pytest.mark.mandatory
            def test_column_names(select):
                required_names = {'A', 'B', 'C'}
                validate(select.fieldnames, required_names)


            def test_a(select):
                requirement = {'x', 'y', 'z'}
                validate(select('A'), requirement)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))

    .. group-tab:: SQL

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pytest
            import sqlite3
            from datatest import (
                validate,
                accepted,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @pytest.fixture(scope='session')
            def connection():
                with working_directory(__file__):
                    conn = sqlite3.connect('example.sqlite3')
                yield conn
                conn.close()


            @pytest.fixture(scope='function')
            def cursor(connection):
                cur = connection.cursor()
                yield cur
                cur.close()


            @pytest.mark.mandatory
            def test_column_names(cursor):
                cursor.execute('SELECT * FROM mytable LIMIT 0;')
                column_names = [item[0] for item in cursor.description]
                required_names = {'A', 'B', 'C'}
                validate(column_names, required_names)


            def test_a(cursor):
                cursor.execute('SELECT A FROM mytable;')
                requirement = {'x', 'y', 'z'}
                validate(cursor, requirement)


            # ...add more tests here...


            if __name__ == '__main__':
                import sys
                sys.exit(pytest.main(sys.argv))

.. end-inclusion-marker-pytestsamples


********
Unittest
********

Datatest provides a handful of tools for integrating data validation
with a unittest test suite. While normal datatest functions work
fine, this integration provides an interface that is more consistent
with established unittest conventions (e.g., "mixedCase" methods,
decorators, and helper classes).

Datatest's :class:`DataTestCase` extends :class:`unittest.TestCase`
to provide unittest-style wrappers for validation and acceptance
(see :ref:`reference docs <datatestcase-docs>` for full details):

.. code-block:: python
    :emphasize-lines: 3,7,8

    from datatest import DataTestCase, Extra

    class TestMyData(DataTestCase):
        def test_one(self):
            data = ['A', 'B', 'C', 'D']
            requirement = {'A', 'B'}
            with self.accepted(Extra):
                self.assertValid(data, requirement)


Datatest includes a :func:`@mandatory <mandatory>` decorator to help
with incremental testing:

.. code-block:: python
    :emphasize-lines: 4

    from datatest import DataTestCase, mandatory, Extra

    class TestMyData(DataTestCase):
        @mandatory
        def test_one(self):
            data = ['A', 'B', 'C', 'D']
            requirement = {'A', 'B'}
            self.assertValid(data, requirement)


Datatest also provides a :func:`main` function and test runner that
runs tests in decleration order (by the line number on which each
test is defined). You can invoke datatest's runner using:

.. code-block:: console

    python -m datatest


In addition to using the :func:`@mandatory <mandatory>` decorator,
you can use the ``-f`` option to stop after any failing test:

.. code-block:: console

    python -m datatest -f


Unittest Samples
================

.. start-inclusion-marker-unittestsamples

.. tabs::

    .. group-tab:: Pandas

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pandas as pd
            from datatest import (
                DataTestCase,
                mandatory,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @working_directory(__file__)
            def setUpModule():
                global df
                df = pd.read_csv('example.csv')


            class TestMyData(DataTestCase):
                @mandatory
                def test_column_names(self):
                    required_names = {'A', 'B', 'C'}
                    self.assertValid(df.columns, required_names)

                def test_a(self):
                    requirement = {'x', 'y', 'z'}
                    self.assertValid(df['A'], requirement)

                # ...add more tests here...


            if __name__ == '__main__':
                from datatest import main
                main()

    .. group-tab:: Pandas (itegrated)

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import pandas as pd
            from datatest import (
                DataTestCase,
                mandatory,
                working_directory,
                register_accessors,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @working_directory(__file__)
            def setUpModule():
                global df
                df = pd.read_csv('example.csv')
                register_accessors()  # Register pandas accessors.


            class TestMyData(DataTestCase):
                @mandatory
                def test_column_names(self):
                    required_names = {'A', 'B', 'C'}
                    df.columns.validate(required_names)

                def test_a(self):
                    requirement = {'x', 'y', 'z'}
                    df['A'].validate(requirement)

                # ...add more tests here...


            if __name__ == '__main__':
                from datatest import main
                main()

    .. group-tab:: Squint

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import squint
            from datatest import (
                DataTestCase,
                mandatory,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @working_directory(__file__)
            def setUpModule():
                global select
                select = squint.Select('example.csv')


            class TestMyData(DataTestCase):
                @mandatory
                def test_column_names(self):
                    required_names = {'A', 'B', 'C'}
                    self.assertValid(select.fieldnames, required_names)

                def test_a(self):
                    requirement = {'x', 'y', 'z'}
                    self.assertValid(select('A'), requirement)

                # ...add more tests here...


            if __name__ == '__main__':
                from datatest import main
                main()

    .. group-tab:: SQL

        .. code-block:: python
            :linenos:

            #!/usr/bin/env python3
            import sqlite3
            from datatest import (
                DataTestCase,
                mandatory,
                working_directory,
                Missing,
                Extra,
                Invalid,
                Deviation,
            )


            @working_directory(__file__)
            def setUpModule():
                global connection
                connection = sqlite3.connect('example.sqlite3')


            def tearDownModule():
                connection.close()


            class MyTest(DataTestCase):
                def setUp(self):
                    self.cursor = connection.cursor()
                    self.addCleanup(lambda: self.cursor.close())

                @mandatory
                def test_column_names(cursor):
                    cursor.execute('SELECT * FROM mytable LIMIT 0;')
                    column_names = [item[0] for item in cursor.description]
                    required_names = {'A', 'B', 'C'}
                    self.assertValid(column_names, required_names)

                def test_a(cursor):
                    cursor.execute('SELECT A FROM mytable;')
                    requirement = {'x', 'y', 'z'}
                    self.assertValid(cursor, requirement)


            if __name__ == '__main__':
                from datatest import main
                main()

.. end-inclusion-marker-unittestsamples
