
.. module:: datatest

.. meta::
    :description: How to work with reference data.
    :keywords: datatest, reference data


############
How-to Guide
############


************************
How to Assert Data Types
************************

.. code-block:: python

    class TypeTestCase(datatest.DataTestCase):
        def assertDataInstance(self, data, type, msg=None):
            """Assert that *data* elements are instances of *type*."""
            def check_type(x):
                return isinstance(x, type)
            msg = msg or 'must be instance of {0!r}'.format(type.__name__)
            self.assertValid(data, check_type, msg)

.. code-block:: python

    class TestTypes(TypeTestCase):
        def test_types(self):
            data = [-2, -1, 0, 1, 2]
            self.assertDataInstance(data, int)


******************************
How to Assert a Given Interval
******************************

.. code-block:: python

    class IntervalTestCase(datatest.DataTestCase):
        def assertInside(self, data, lower, upper, msg=None):
            """Assert that *data* elements fall inside given interval."""
            def interval(x):
                return lower <= x <= upper
            msg = msg or 'interval from {0!r} to {1!r}'.format(lower, upper)
            self.assertValid(data, interval, msg)

        def assertOutside(self, data, lower, upper, msg=None):
            """Assert that *data* elements fall outside given interval."""
            def not_interval(x):
                return not lower <= x <= upper
            msg = msg or 'interval from {0!r} to {1!r}'.format(lower, upper)
            self.assertValid(data, not_interval, msg)

.. code-block:: python

    class TestInterval(IntervalTestCase):
        def test_interval(self):
            data = [5, 7, 4, 5, 9]
            self.assertInside(data, lower=5, upper=10)


***************************
How to Assert an Inequality
***************************

.. code-block:: python

    class InequalityTestCase(datatest.DataTestCase):
        def assertDataGreater(self, data, requirement, msg=None):
            """Assert that *data* elements are greater than *requirement*."""
            def greater(x):
                return x > requirement
            msg = msg or 'must be greater than {0!r}'.format(requirement)
            self.assertValid(data, greater, msg)

        def assertDataLess(self, data, requirement, msg=None):
            """Assert that *data* elements are less than *requirement*."""
            def less(x):
                return x < requirement
            msg = msg or 'must be less than {0!r}'.format(requirement)
            self.assertValid(data, less, msg)

.. code-block:: python

    class TestGreaterThan(InequalityTestCase):
        def test_greater_than(self):
            data = [6, 7, 8, 9]
            self.assertDataGreater(data, 5)


**************************************
How to Check for Subsets and Supersets
**************************************

To assert subset or superset relations, use a :py:class:`set`
*requirement* together with the :meth:`allowedMissing()
<datatest.DataTestCase.allowedMissing>` or :meth:`allowedExtra()
<datatest.DataTestCase.allowedExtra>` context managers:

.. code-block:: python

    class MembershipTestCase(datatest.DataTestCase):
        def assertSubset(self, data, requirement, msg=None):
            """Assert that set of *data* is a subset of *requirement*."""
            with self.allowedMissing():
                self.assertValid(data, set(requirement), msg)

        def assertSuperset(self, data, requirement, msg=None):
            """Assert that set of *data* is a superset of *requirement*."""
            with self.allowedExtra():
                self.assertValid(data, set(requirement), msg)

.. code-block:: python

    class TestSubset(MembershipTestCase):
        def test_subset(self):
            data = {'a', 'b'}
            requirement = {'a', 'b', 'c', 'd'}
            self.assertSubset(data, requirement)


*************************
How to Use Reference Data
*************************

To compare two data sources that have the same field names,
we can create a single query and execute it twice (once for
each source). The pair of results can then be passed to
:meth:`assertValid() <datatest.DataTestCase.assertValid>`.

Below, we implement this with a helper-class ("ReferenceTestCase")
that has a single "assertReference()" method:

.. code-block:: python

    def setUpModule():
        global source_data, source_reference
        with datatest.working_directory(__file__):
            source_data = datatest.DataSource.from_csv('mydata.csv')
            source_reference = datatest.DataSource.from_csv('myreference.csv')


    class ReferenceTestCase(datatest.DataTestCase):
        def assertReference(self, select, **where):
            """
            assertReference(select, **where)
            assertReference(query)

            Asserts that the query results from the data under test
            match the query results from the reference data.
            """
            if isinstance(select, datatest.DataQuery):
                query = select
            else:
                query = datatest.DataQuery(select, **where)
            data = query(source_data)
            requirement = query(source_reference)
            self.assertValid(data, requirement)

Test-cases that inherit from this class can use "assertReference()":

.. code-block:: python

    class TestMyData(ReferenceTestCase):
        def test_select_syntax(self):
            self.assertReference({('one', 'two')}, two='x')

        def test_query_syntax(self):
            query = datatest.DataQuery({'one': ['three']}).sum()
            self.assertReference(query)
