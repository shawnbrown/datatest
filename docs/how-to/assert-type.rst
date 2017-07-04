
.. module:: datatest

.. meta::
    :description: How to assert data types.
    :keywords: datatest, reference data


###################
How to Assert Types
###################

.. code-block:: python

    import datatest


    class TypeTestCase(datatest.DataTestCase):
        def assertValidType(self, data, type, msg=None):
            """Assert that *data* elements are instances of *type*."""
            def check_type(x):
                return isinstance(x, type)
            msg = msg or 'must be instance of {0!r}'.format(type.__name__)
            self.assertValid(data, check_type, msg)

    ...

.. code-block:: python

    ...

    class TestTypes(TypeTestCase):
        def test_types(self):
            data = [-2, -1, 0, 1, 2]
            self.assertValidType(data, int)


    if __name__ == '__main__':
        datatest.main()
