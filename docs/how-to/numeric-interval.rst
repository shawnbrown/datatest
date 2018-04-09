
.. module:: datatest

.. meta::
    :description: How to assert an interval.
    :keywords: datatest, reference data


#########################
How to Assert an Interval
#########################

.. code-block:: python

    import datatest


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

    ...

.. code-block:: python

    ...

    class TestInterval(IntervalTestCase):
        def test_interval(self):
            data = [5, 7, 4, 5, 9]
            self.assertInside(data, lower=5, upper=10)


    if __name__ == '__main__':
        datatest.main()
