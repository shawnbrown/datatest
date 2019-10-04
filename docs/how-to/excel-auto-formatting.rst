
.. currentmodule:: datatest

.. meta::
    :description: How to prevent Excel from converting values.
    :keywords: datatest, excel, date conversion, scientific notation, leading zeros


#######################################
How to Avoid Excel Automatic Formatting
#######################################

When MS Excel opens CSV files (and many other tabular formats),
its default behavior will reformat certain values as dates,
strip leading zeros, convert long numbers into scientific
notation, and more. There are many cases where these kinds
of changes actually corrupt your data.

It is possible to control Excel's formatting behavior using its
*Text Import Wizard*. But as long as other users can open and
re-save your CSV files, there may be no good way to guarantee that
someone else won't inadvertently corrupt your data with Excel's
default auto-format behavior. In a situation like this, you can
mitigate problems by avoiding values that Excel likes to auto-format.

Using the :class:`Predicate` object below, you can check that values
are "Excel safe" and receive a list of differences when values are
vulnerable to inadvertent auto-formatting:

.. code-block:: python

    import re
    from datatest import Predicate


    # Predicate to check that elements are not subject
    # to Excel auto-formatting.
    excel_safe = ~Predicate(re.compile(r'''^(
        # Date format character combinations.
        \d{1,2}-(?:\d{1,2}|\d{4})
        | (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ \-]\d{1,2}
        | [01]?[0-9]-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)

        # Twelve-hour clock conversion.
        | [01]?[0-9][ ]?(AM?|PM?)

        # Numeric conversions.
        | 0\d+\.?\d*        # Number with leading zeros.
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

    )$''', re.VERBOSE | re.IGNORECASE), name='excel_safe')


An Example
==========

CSV File
--------

As an example, the file :download:`excel_autoformat.csv
</_static/excel_autoformat.csv>` contains two values that would
get converted to dates if Excel's automatic formatting were
applied to them:

.. literalinclude:: /_static/excel_autoformat.csv
    :language: none
    :lineno-match:
    :lines: 15-19
    :emphasize-lines: 3


.. literalinclude:: /_static/excel_autoformat.csv
    :language: none
    :lineno-match:
    :lines: 47-51
    :emphasize-lines: 3

The values ``APR-10`` and ``DEC-20`` would get converted to April
10th and December 20th respectively.


Checking the File
-----------------

To check our file (:download:`excel_autoformat.csv
</_static/excel_autoformat.csv>`), we can use the
following tests:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 19,23

            import re
            import pytest
            from datatest import validate
            from datatest import working_directory
            from datatest import Select
            from datatest import Predicate


            excel_safe = ...  # Define Excel-safe Predicate.


            @pytest.fixture(scope='module')
            @working_directory(__file__)
            def mydata():
                return Select('excel_autoformat.csv')


            def test_column_a(mydata):
                validate(mydata('A'), excel_safe)


            def test_column_b(mydata):
                validate(mydata('B'), excel_safe)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 19,22

            import re
            from datatest import DataTestCase
            from datatest import working_directory
            from datatest import Select
            from datatest import Predicate


            excel_safe = ...  # Define Excel-safe Predicate.


            def setUpModule():
                global mydata
                with working_directory(__file__):
                    mydata = Select('excel_autoformat.csv')


            class TestMyData(DataTestCase):
                def test_column_a(self):
                    self.assertValid(mydata('A'), excel_safe)

                def test_column_b(self):
                    self.assertValid(mydata('B'), excel_safe)


The example above contains two tests. When running these tests,
``test_column_a()`` passes without error, but ``test_column_b()``
fails. This is because column **B** contains two values that are
not Excel-safe. The following error is reported:

.. code-block:: none

    ValidationError: does not satisfy excel_safe() (2 differences): [
        Invalid('APR-10'),
        Invalid('DEC-20'),
    ]


Fixing the Data
---------------

To address these issues, we need to edit **excel_autoformat.csv** and
change the values in column **B** so they are no longer subject to Excel's
auto-formatting behavior. There are a few ways to do this.

You can prefix values with an apostrophe (``'``) which causes Excel to
treat them as text (instead of as numbers or dates):

.. code-block:: none
    :lineno-start: 15
    :emphasize-lines: 3

    292,AOJ-35
    294,AOX-18
    295,'APR-10
    298,AQV-25
    314,ATF-21

.. code-block:: none
    :lineno-start: 47
    :emphasize-lines: 3

    874,CYL-23
    887,DBB-01
    895,'DEC-20
    906,DNZ-33
    981,DVH-50

Another approach would be to change the formatting for the entire
column. Below, the hyphens in column **B** have been replaced with
underscores (``_``):

.. code-block:: none
    :lineno-start: 15
    :emphasize-lines: 3

    292,AOJ_35
    294,AOX_18
    295,APR_10
    298,AQV_25
    314,ATF_21

.. code-block:: none
    :lineno-start: 47
    :emphasize-lines: 3

    874,CYL_23
    887,DBB_01
    895,DEC_20
    906,DNZ_33
    981,DVH_50

After making the needed changes and saving the file, the tests will
now pass without error.


.. caution::

    The ``excel_safe`` predicate implements a blacklist approach
    to detect values that Excel will automatically convert. It is
    not guaranteed to catch everything and future versions of Excel
    could introduce new behaviors. If you discover auto-formatted
    values that are not handled by this helper function (or if you
    have an idea regarding a workable whitelist approach), please
    `file an issue`_ and we will try to improve it.


.. _`file an issue`: https://github.com/shawnbrown/datatest/issues


..
    TODO - Other patterns that Excel changes:

    * 12:12 -> 12:12 (12:12:00 PM)
    * 25:32 -> 25:32:00 (1/1/1900 1:32:00 AM)
    * 1:1 -> 01:01:00 AM
    * 1:1:1 -> 01:01:01 AM
