
.. module:: datatest

.. meta::
    :description: How to compare data between two files.
    :keywords: compare files, datatest


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
            source_data = datatest.Selector('mydata.csv')
            source_reference = datatest.Selector('myreference.csv')


    class ReferenceTestCase(datatest.DataTestCase):
        def assertReference(self, select, **where):
            """
            assertReference(select, **where)
            assertReference(query)

            Asserts that the query results from the data under test
            match the query results from the reference data.
            """
            if isinstance(select, datatest.Query):
                query = select
            else:
                query = datatest.Query(select, **where)
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
            query = datatest.Query({'A': 'C'}).sum()
            self.assertReference(query)


    if __name__ == '__main__':
        datatest.main()
