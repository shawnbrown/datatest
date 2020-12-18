
.. currentmodule:: datatest

.. meta::
    :description: How to validate column names.
    :keywords: datatest, column names, columns, fieldnames


############################
How to Validate Column Names
############################

To validate the column names in a data source, simply pass the names
themselves as the *data* argument when calling :func:`validate`. You
control the method of validation with the *requirement* you provide.


===================
Column Requirements
===================


Exist in Any Order
==================

Using a :py:class:`set` requirement, we can check that column names
exist but allow them to appear in any order:

.. code-block:: python

    column_names = ...
    validate(column_names, {'A', 'B', 'C'})


A Subset/Superset of Required Columns
=====================================

Using :meth:`validate.subset`/:meth:`validate.superset`, we can check
that column names are a subset or superset of the required names:

.. code-block:: python

    column_names = ...
    validate.subset(column_names, {'A', 'B', 'C', 'D', 'E'})


Defined in a Specific Order
===========================

Using a :py:class:`list` requirement, we can check that column names
exist and that they appear in a specified order:

.. code-block:: python

    column_names = ...
    validate(column_names, ['A', 'B', 'C'])


Matches Custom Formats
======================

Sometimes we don't care exactly what the column names are but we want to
check that they conform to a specific format. To do this, we can define a
helper function that performs any arbitrary comparison we want. Below, we
check that column names are all written in uppercase letters:

.. code-block:: python

    def isupper(x):  # <- helper function
        return x.isupper()

    column_names = ...
    validate(column_names, isupper)

In addition to :meth:`isupper() <str.isupper>`, there are other
string methods that can be useful for validating specific formats:
:meth:`islower() <str.islower>`, :meth:`isalpha() <str.isalpha>`,
:meth:`isascii() <str.isascii>`, :meth:`isidentifier() <str.isidentifier>`,
etc.


A More Complex Example
----------------------

Below, we check that the column names start with two capital letters
and end with one or more digits. The examples below demonstrate different
ways of checking this format:

.. tabs::

    .. group-tab:: Regex Pattern

        We can use :meth:`validate.regex` to check that column names match
        a :ref:`regular expression <python:re-syntax>` pattern. The pattern
        matches strings that start with two capital letters (``^[A-Z]{2}``)
        and end with one or more digits (``\d+$``):

        .. code-block:: python

            column_names = ...
            msg = 'Must have two capital letters followed by digits.'
            validate.regex(column_names, r'^[A-Z]{2}\d+$', msg=msg)

    .. group-tab:: Helper Function

        This example performs the same validation as the Regex Pattern
        version, but uses :term:`slicing <python:slice>` and string methods
        to implement the same requirement:

        .. code-block:: python

            def two_letters_plus_digits(x):
                """Must have two capital letters followed by digits."""
                first_two_chars = x[:2]
                remaining_chars = x[2:]

                if not first_two_chars.isalpha():
                    return False
                if not first_two_chars.isupper():
                    return False
                return remaining_chars.isdigit()

            column_names = ...
            validate(column_names, two_letters_plus_digits)


===================================
Examples Using Various Data Sources
===================================


csv.reader()
============

.. code-block:: python
    :emphasize-lines: 7-8
    :linenos:

    import csv
    from datatest import validate

    with open('mydata.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)

        header_row = next(reader)
        validate(header_row, {'A', 'B', 'C'})


csv.DictReader()
================

.. code-block:: python
    :emphasize-lines: 7
    :linenos:

    import csv
    from datatest import validate

    with open('mydata.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        validate(reader.fieldnames, {'A', 'B', 'C'})


Pandas
======

.. code-block:: python
    :emphasize-lines: 5
    :linenos:

    import pandas as pd
    import datatest as dt

    df = pd.read_csv('mydata.csv')
    dt.validate(df.columns, {'A', 'B', 'C'})


Pandas (Integrated)
===================

.. code-block:: python
    :emphasize-lines: 4,7
    :linenos:

    import pandas as pd
    import datatest as dt

    dt.register_accessors()

    df = pd.read_csv('mydata.csv')
    df.columns.validate({'A', 'B', 'C'})


Squint
======

.. code-block:: python
    :emphasize-lines: 5
    :linenos:

    import squint
    from datatest import validate

    select = squint.Select('mydata.csv')
    validate(select.fieldnames, {'A', 'B', 'C'})


Database
========

If you're using a DBAPI2 compatible connection (see :pep:`249`), you
can get a table's column names using the :pep:`cursor.description
<249#description>` attribute:

.. code-block:: python
    :emphasize-lines: 7-9
    :linenos:

    import sqlite3
    from datatest import validate

    connection = sqlite3.connect('mydata.sqlite3')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM mytable LIMIT 0;')
    column_names = [item[0] for item in cursor.description]
    validate(column_names, {'A', 'B', 'C'})

Above, we select all columns (``SELECT *``) from our table but limit
the result to zero rows (``LIMIT 0``). Executing this query populates
``cursor.description`` even though no records are returned. We take
the column name from each item in description (``item[0]``) and perform
our validation.
