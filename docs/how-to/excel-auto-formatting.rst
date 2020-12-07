
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
    :emphasize-lines: 44
    :linenos:

    import re
    from datatest import validate, Predicate


    # Predicate to check that elements are not subject
    # to Excel auto-formatting.
    excel_safe = ~Predicate(re.compile(r'''^(
        # Date format character combinations.
        \d{1,2}-(?:\d{1,2}|\d{4})
        | (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ \-]\d{1,2}
        | [01]?[0-9]-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)

        # Time conversions.
        | [01]?[0-9][ ]?(AM?|PM?)     # Twelve-hour clock.
        | \d?\d[ ]*:                  # HH (hours).
        | \d?\d[ ]*(:[ ]*\d\d?){1,2}  # HH:MM and HH:MM:SS

        # Numeric conversions.
        | 0\d+\.?\d*        # Number with leading zeros.
        | \d*\.\d*0         # Decimal point with trailing zeros.
        | \d*\.             # Trailing decimal point.
        | \d.?\d*E[+-]?\d+  # Scientific notation.
        | \d{16,}           # Numbers of 16+ digits get approximated.

        # Whitespace normalization.
        | \s.*              # Leading whitespace.
        | .*\s              # Trailing whitespace.
        | .*\s\s.*          # Irregular whitespace (new in Office 365).

        # Other conversions
        | =.+               # Spreadsheet formula.

    )$''', re.VERBOSE | re.IGNORECASE), name='excel_safe')


    data = [
        'AOX-18',
        'APR-23',
        'DBB-01',
        'DEC-20',
        'DNZ-33',
        'DVH-50',
    ]
    validate(data, excel_safe)

In the example above, we use ``excel_safe`` as our *requirement*.
The validation fails because our *data* contains two codes that
Excel would auto-convert into date types:

.. code-block:: none

    ValidationError: does not satisfy excel_safe() (2 differences): [
        Invalid('APR-23'),
        Invalid('DEC-20'),
    ]


Fixing the Data
---------------

To address the failure, we need to change the values in *data* so
they are no longer subject to Excel's auto-formatting behavior.
There are a few ways to do this.

We can prefix the failing values with apostrophes (``'APR-23``
and ``'DEC-20``). This causes Excel to treat them as text instead
of dates or numbers:

.. code-block:: python
    :emphasize-lines: 5,7
    :linenos:
    :lineno-start: 34

    ...

    data = [
        "AOX-18",
        "'APR-23",
        "DBB-01",
        "'DEC-20",
        "DNZ-33",
        "DVH-50",
    ]
    validate(data, excel_safe)


Another approach would be to change the formatting for the all of
the values. Below, the hyphens in *data* have been replaced with
underscores (``_``):

.. code-block:: python
    :emphasize-lines: 4-9
    :linenos:
    :lineno-start: 34

    ...

    data = [
        'AOX_18',
        'APR_23',
        'DBB_01',
        'DEC_20',
        'DNZ_33',
        'DVH_50',
    ]
    validate(data, excel_safe)


After making the needed changes, the validation will now pass without
error.


.. caution::

    The ``excel_safe`` predicate implements a blacklist approach
    to detect values that Excel will automatically convert. It is
    not guaranteed to catch everything and future versions of Excel
    could introduce new behaviors. If you discover auto-formatted
    values that are not handled by this helper function (or if you
    have an idea regarding a workable whitelist approach), please
    `file an issue`_ and we will try to improve it.


.. _`file an issue`: https://github.com/shawnbrown/datatest/issues
