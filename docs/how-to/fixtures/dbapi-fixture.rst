
.. module:: datatest

.. meta::
    :description: How to use a database fixture.
    :keywords: datatest, database, fixture


#######################################
How to Use Database Connection Fixtures
#######################################

This example demonstrates using a database connection as a fixture.
While the :py:mod:`sqlite3` module is used here, this approach should
work with any :pep:`DBAPI2 <249>` compatible connection.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python

            import sqlite3
            import pytest
            from datatest import validate


            @pytest.fixture(scope='session')
            def connection():
                conn = sqlite3.connect(':memory:', isolation_level=None)
                conn.executescript('''
                    CREATE TABLE mydata(A, B, C);
                    INSERT INTO mydata VALUES('x', 'foo', 20);
                    INSERT INTO mydata VALUES('x', 'foo', 30);
                    INSERT INTO mydata VALUES('y', 'foo', 10);
                    INSERT INTO mydata VALUES('y', 'bar', 20);
                    INSERT INTO mydata VALUES('z', 'bar', 10);
                    INSERT INTO mydata VALUES('z', 'bar', 10);
                ''')
                yield conn
                conn.close()


            @pytest.fixture(scope='function')
            def cursor(connection):
                cur = connection.cursor()
                cur.execute('BEGIN TRANSACTION;')
                yield cur
                cur.execute('ROLLBACK TRANSACTION;')
                cur.close()


            def test_total(cursor):
                cursor.execute('SELECT SUM(C) FROM mydata;')
                requirement = 100
                validate(cursor, requirement)


            def test_subtotals(cursor):
                cursor.execute('SELECT A, SUM(C) FROM mydata GROUP BY A;')
                requirement = {'x': 50, 'y': 30, 'z': 20}
                validate(dict(cursor), requirement)


    .. group-tab:: Unittest

        .. code-block:: python

            import sqlite3
            from datatest import DataTestCase


            def setUpModule():
                global connection
                connection = sqlite3.connect(':memory:', isolation_level=None)
                connection.executescript('''
                    CREATE TABLE mydata(A, B, C);
                    INSERT INTO mydata VALUES('x', 'foo', 20);
                    INSERT INTO mydata VALUES('x', 'foo', 30);
                    INSERT INTO mydata VALUES('y', 'foo', 10);
                    INSERT INTO mydata VALUES('y', 'bar', 20);
                    INSERT INTO mydata VALUES('z', 'bar', 10);
                    INSERT INTO mydata VALUES('z', 'bar', 10);
                ''')


            def tearDownModule():
                connection.close()


            class MyTest(DataTestCase):
                def setUp(self):
                    self.cursor = connection.cursor()
                    self.cursor.execute('BEGIN TRANSACTION;')

                    def rollback(cur):
                        cur.execute('ROLLBACK TRANSACTION;')
                        cur.close()

                    self.addCleanup(rollback, self.cursor)

                def test_total(self):
                    self.cursor.execute('SELECT SUM(C) FROM mydata;')
                    requirement = 100
                    self.assertValid(self.cursor, requirement)

                def test_subtotals(self):
                    self.cursor.execute('SELECT A, SUM(C) FROM mydata GROUP BY A;')
                    requirement = {'x': 50, 'y': 30, 'z': 20}
                    self.assertValid(dict(self.cursor), requirement)

