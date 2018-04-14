
.. module:: datatest

.. meta::
    :description: How to prevent Excel from converting values.
    :keywords: datatest, excel, date conversion, scientific notation, leading zeros


#######################################
How to Avoid Excel Automatic Formatting
#######################################

When MS Excel opens CSV files (and many other tabular formats),
its default behavior will reformat certain values as dates,
strip leading zeros, convert long numbers into scientific
notation, and more.

It is possible to control Excel's formatting behavior using its
*Text Import Wizard*. But as long as other users can open and
re-save your CSV files, there is no good way to guarantee that
someone else won't inadvertently corrupt your data with Excel's
default auto-format behavior.

In a situation like this, you can mitigate problems by avoiding
values that Excel likes to auto-format. Using the helper-function
below, you can assert that values are "Excel safe" and receive a
list of differences when values are vulnerable to inadvertent
auto-formatting:

.. code-block:: python

    import re


    def excel_safe(value):
        """Helper function to check if *value* can be opened in Excel
        without being reformatted as a date, converted to scientific
        notation, truncated, or otherwise changed.
        """
        if re.search(r'''^(
                # Date format character combinations.
                \d{1,2}-(?:\d{1,2}|\d{4})
                | (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ \-]\d{1,2}
                | [01]?[0-9]-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)

                # Numeric conversions.
                | 0\d+.?\d*         # Number with leading zeros.
                | \d*\.\d*0         # Decimal point with trailing zeros.
                | \d*\.             # Trailing decimal point.
                | \d.?\d*E[+-]?\d+  # Scientific notation.
                | \d{16,}           # Numbers of 16+ digits get approximated.

                # Whitespace normalization.
                | \s.*              # Leading whitespace.
                | .*\s              # Trailing whitespace.
                | .*\s\s.*          # Irregular whitespace (for Office 365).

                # Other conversions
                | =.+               # Spreadsheet formula.

        )$''', str(value), re.VERBOSE | re.IGNORECASE):
            return False
        return True


As an example, look at the sample of data below---on the middle row
in colunm "B", the value is ``APR-10``. Excel's default formatting
will convert this into a date (April 10th):

    ===  ======
    A    B
    ===  ======
    ...  ...
    294  AOX-18
    295  APR-10
    298  AQV-25
    ...  ...
    ===  ======


To check if columns contain values that will be auto-formatted, you
can use tests like the following:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 17,21

            import re
            import pytest
            from datatest import validate, working_directory, Selector


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Selector('test_excel_safe.csv')


            def excel_safe(value):
                ...  # The helper function described previously.


            def test_wellformed_a(mydata):
                validate(mydata('A'), excel_safe)


            def test_wellformed_b(mydata):
                validate(mydata('B'), excel_safe)

        You can download this example (:download:`test_excel_safe.zip
        </_static/test_excel_safe.zip>`), unzip the files, and run it
        with the following command:

        .. code-block:: none

            pytest test_excel_safe.py


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 17,20

            import re
            from datatest import DataTestCase, working_directory, Selector


            def setUpModule():
                global mydata
                with working_directory(__file__):
                    mydata = Selector('test_excel_safe.csv')


            def excel_safe(value):
                ...  # The helper function described previously.


            class TestMyData(DataTestCase):
                def test_wellformed_a(self):
                    self.assertValid(mydata('A'), excel_safe)

                def test_wellformed_b(self):
                    self.assertValid(mydata('B'), excel_safe)

        You can download this example (:download:`test_excel_safe_unit.zip
        </_static/test_excel_safe_unit.zip>`), unzip the files, and run
        it with the following command:

        .. code-block:: none

            python -m datatest test_excel_safe_unit.py


.. warning::

    If you discover auto-formatted vlues that are not handled by this
    helper function, please `file an issue`_ and we will try to improve
    it. ``excel_safe()`` makes a best effort to detect values that
    Excel will automatically convert but it is not guaranteed to catch
    everything.


.. _`file an issue`: https://github.com/shawnbrown/datatest/issues


..
    TODO - Other patterns that Excel changes:

    * 12:12 -> 12:12 (12:12:00 PM)
    * 25:32 -> 25:32:00 (1/1/1900 1:32:00 AM)
    * 1:1:1 -> ???
