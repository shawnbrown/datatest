
.. module:: datatest

.. meta::
    :description: How to Assert Date Formats.
    :keywords: datatest, date format, validate date


##########################
How to Assert Date Formats
##########################

To assert a particular date format, you can use a predicate
function. In the following example, we define a function that
checks for the YYYY-MM-DD format:


.. code-block:: python

    from datetime import datetime
    import datatest


    def date_format(value):
        """Date should be in YYYY-MM-DD format."""
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return False
        return True


The helper-function above uses *C standard* date codes
(``%Y-%m-%d``) to describe the desired format. See the official
Python documentation for other available `date format codes`_.

Use of this helper function is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 7

            ...

            def test_date_format():

                data = ['2018-02-14', '3/17/2018', '2018-04-01']

                datatest.validate(data, date_format)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 9

            ...

            class MyTest(datatest.DataTestCase):

                def test_data_types(self):

                    data = ['2018-02-14', '3/17/2018', '2018-04-01']

                    self.assertValid(data, date_format)


.. _`date format codes`: https://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
