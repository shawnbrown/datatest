
.. module:: datatest

.. meta::
    :description: How to assert set relations.
    :keywords: datatest, reference data


###################################
How to Assert Subsets and Supersets
###################################

To assert subset or superset relations, use a :py:class:`set`
*requirement* together with the :meth:`allowedMissing()
<datatest.DataTestCase.allowedMissing>` or :meth:`allowedExtra()
<datatest.DataTestCase.allowedExtra>` context managers:

.. code-block:: python

    import datatest


    class SetTestCase(datatest.DataTestCase):
        def assertSubset(self, data, requirement, msg=None):
            """Assert that set of *data* is a subset of *requirement*."""
            with self.allowedMissing():
                self.assertValid(data, set(requirement), msg)

        def assertSuperset(self, data, requirement, msg=None):
            """Assert that set of *data* is a superset of *requirement*."""
            with self.allowedExtra():
                self.assertValid(data, set(requirement), msg)

    ...

.. code-block:: python

    ...

    class TestSubset(SetTestCase):
        def test_subset(self):
            data = {'a', 'b'}
            requirement = {'a', 'b', 'c', 'd'}
            self.assertSubset(data, requirement)


    if __name__ == '__main__':
        datatest.main()
