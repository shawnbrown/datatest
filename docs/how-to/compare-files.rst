
.. module:: datatest

.. meta::
    :description: How to assert data types.
    :keywords: reference data, compare files, datatest


########################
How to Compare Two Files
########################

To compare two data sources that have the same field names,
we can create a single query and call it twice (once for
each source). The pair of results can then be passed to
:meth:`assertValid() <datatest.DataTestCase.assertValid>`.

Below, we implement this with a helper-class ("ReferenceTestCase")
that has a single "assertReference()" method:

.. code-block:: python

    import datatest


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

    ...

Test-cases that inherit from this class can use "assertReference()":

.. code-block:: python

    ...

    class TestMyData(ReferenceTestCase):
        def test_select_syntax(self):
            self.assertReference({('A', 'B')}, B='foo')

        def test_query_syntax(self):
            query = datatest.DataQuery({'A': 'C'}).sum()
            self.assertReference(query)


    if __name__ == '__main__':
        datatest.main()
