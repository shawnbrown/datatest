
.. module:: datatest

.. meta::
    :description: How to Assert Date Formats.
    :keywords: datatest, date format, validate date


##########################
How to Assert Date Formats
##########################

To assert a particular date format, you can use a predicate
function. In the following example, we define a function that
checks for dates that match the YYYY-MM-DD format:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 18

            from datetime import datetime
            from datatest import validate


            def yyyy_mm_dd(value):
                """Return True if *value* is a YYYY-MM-DD formatted date."""
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return False
                return True


            def test_date_format():

                data = ['2018-02-14', '3/17/2018', '2018-04-01']

                validate(data, yyyy_mm_dd)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 20

            from datetime import datetime
            from datatest import DataTestCase


            def yyyy_mm_dd(value):
                """Return True if *value* is a YYYY-MM-DD formatted date."""
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return False
                return True


            class MyTest(DataTestCase):

                def test_data_types(self):

                    data = ['2018-02-14', '3/17/2018', '2018-04-01']

                    self.assertValid(data, yyyy_mm_dd)


The helper-function above uses C-style date codes (``%Y-%m-%d``) to
describe the desired format. See the official Python documentation
for other available `date format codes`_.


.. _`date format codes`: https://docs.python.org/library/datetime.html#strftime-and-strptime-behavior
