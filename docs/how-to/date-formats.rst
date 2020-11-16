
.. currentmodule:: datatest

.. meta::
    :description: How to validate date formats.
    :keywords: datatest, date format, validate, validation


############################
How to Validate Date Formats
############################

To validate date formats, we can define a helper function that uses
`strftime codes`_ to check for matching strings.

In the following example, we use the code ``%Y-%m-%d`` to check for
dates that match the pattern YYYY-MM-DD:

.. code-block:: python
    :emphasize-lines: 17

    from datetime import datetime
    from datatest import validate


    def strftime_format(format):
        def func(value):
            try:
                datetime.strptime(value, format)
            except ValueError:
                return False
            return True
        func.__doc__ = f'should use date format {format}'
        return func


    data = ['2020-02-14', '03-17-2021', '2021-04-01']
    validate(data, strftime_format('%Y-%m-%d'))


Date strings that don't match the required format are flagged as
:class:`Invalid`:

.. code-block:: none

    Traceback (most recent call last):
      File "example.py", line 17, in <module>
    datatest.ValidationError: should use date format '%Y-%m-%d' (1 difference): [
        Invalid('03-17-2021'),
    ]


Strftime Codes for Common Date Formats
======================================

You can use the following **format codes** with the function
defined earlier to validate many common date formats (e.g.,
``strftime_format('%d %B %Y')``):

========================  =====================  ========================
format codes              abbreviation           example
========================  =====================  ========================
``%Y-%m-%d``              YYYY-MM-DD             2021-03-17
``%m/%d/%Y``              MM/DD/YYYY             03/17/2021
``%d/%m/%Y``              DD/MM/YYYY             17/03/2021
``%d.%m.%Y``              DD.MM.YYYY             17.03.2021
``%d %B %Y``              DD/Mmmm/YYYY           17 March 2021
``%b %d, %Y``             Mmm DD, YYYY           Mar 17, 2021
``%a %b %d %H:%M:%S %Y``  Ddd Mmm DD H:M:S YYYY  Wed Mar 17 19:42:50 2021
========================  =====================  ========================

In Python's :py:mod:`datetime` module, see `strftime() and strptime() Format Codes`_
for all supported codes.

.. _`strftime codes`: https://docs.python.org/library/datetime.html#strftime-and-strptime-format-codes
.. _`strftime() and strptime() Format Codes`: https://docs.python.org/library/datetime.html#strftime-and-strptime-format-codes

