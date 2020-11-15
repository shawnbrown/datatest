
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


Are a Subset/Superset of Required Columns
=========================================

Using :meth:`validate.subset`/:meth:`validate.superset`, we can check
that column names are a subset or superset of the required names:

.. code-block:: python

    column_names = ...
    validate.subset(column_names, {'A', 'B', 'C'})


Are Defined in Specific Order
=============================

Using a :py:class:`list` requirement, we can check that column names
exist and that they appear in a specified order:

.. code-block:: python

    column_names = ...
    validate(column_names, ['A', 'B', 'C'])


Match a Specific Format
=======================

Sometimes we don't care exactly what the column names are but we want to
check that they conform to a specific format. To do this, we can define a
helper function that performs any arbitrary comparison we want. Below, we
check that column names are all written in uppercase letters:

.. code-block:: python

    def isupper(x):  # <- helper function
        return x.isupper()

    column_names = ...
    validate(column_names, isupper)

..
    In this case, our helper function calls the :py:meth:`isupper()
    <str.isupper>` method. Alternatively, we could perform this same
    check using :py:func:`operator.methodcaller`:

In this case, our helper function calls the ``isupper()`` method.
Alternatively, we could perform this same check using
:py:func:`operator.methodcaller`:

.. code-block:: python

    from operator import methodcaller

    column_names = ...
    validate(column_names, methodcaller('isupper'))


In addition to :meth:`isupper() <str.isupper>`, there are other
string methods that can be useful for validating specific formats:
:meth:`islower() <str.islower>`, :meth:`isalpha() <str.isalpha>`,
:meth:`isascii() <str.isascii>`, :meth:`isidentifier() <str.isidentifier>`,
etc.


===================================
Examples Using Various Data Sources
===================================


csv.reader()
============

.. code-block:: python
    :emphasize-lines: 7-8

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

    import csv
    from datatest import validate

    with open('mydata.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        validate(reader.fieldnames, {'A', 'B', 'C'})


Pandas
======

.. code-block:: python
    :emphasize-lines: 5

    import pandas as pd
    import datatest as dt

    df = pd.read_csv('mydata.csv')
    dt.validate(df.columns, {'A', 'B', 'C'})


Pandas (Integrated)
===================

.. code-block:: python
    :emphasize-lines: 4,7

    import pandas as pd
    import datatest as dt

    dt.register_accessors()

    df = pd.read_csv('mydata.csv')
    df.columns.validate({'A', 'B', 'C'})


Squint
======

.. code-block:: python
    :emphasize-lines: 5

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
