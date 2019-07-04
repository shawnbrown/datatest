
.. module:: datatest

.. meta::
    :description: Datatest examples demonstrating use of pandas DataFrame objects.
    :keywords: datatest, pandas, DataFrame


###################
Testing With Pandas
###################

Datatest can validate :mod:`pandas` objects (:class:`DataFrame
<pandas.DataFrame>`, :class:`Series <pandas.Series>`, and
:class:`Index <pandas.Index>`) the same way it does with
built-in types.


=============
Some Examples
=============

This example uses a :class:`DataFrame <pandas.DataFrame>` to
load and inspect data from a CSV file (:download:`movies.csv
</_static/tutorial/movies.csv>`). The CSV file uses the
following format:

.. csv-table::
    :header: title, rating, year, runtime

    Almost Famous, R, 2000, 122
    American Pie, R, 1999, 95
    Back to the Future, PG, 1985, 116
    Blade Runner, R, 1982, 117
    ..., ..., ..., ...


.. tabs::

    .. group-tab:: Pytest

        The :download:`test_movies_df.py </_static/tutorial/test_movies_df.py>`
        script demonstrates pytest-style tests:

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :language: python
            :lineno-match:

    .. group-tab:: Unittest

        The :download:`test_movies_df_unit.py </_static/tutorial/test_movies_df_unit.py>`
        script demonstrates unittest-style tests:

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :language: python
            :lineno-match:


You can run these tests, use the following command:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none

            pytest test_movies_df.py

    .. group-tab:: Unittest

        .. code-block:: none

            python -m datatest test_movies_df_unit.py


========================
Step by Step Explanation
========================


1. Define a test fixture
------------------------

Define a test fixture that loads the CSV file into a
:class:`DataFrame <pandas.DataFrame>`:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: df
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: setUpModule
            :lineno-match:


2. Check column names
---------------------

Check that the data includes the expected column names:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: test_columns
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: TestMovies.test_columns
            :lineno-match:

This validation requires that the set of values in ``df.columns``
matches the required :py:class:`set`. The ``df.columns`` attribute is
an :class:`Index <pandas.Index>` object---datatest treats this the same
as any other sequence of values. 

This test is marked ``mandatory`` because it's a prerequisite that must
be satisfied before any of the other tests can pass. When a mandatory
test fails, the test suite stops immediately and no more tests are run.


3. Check 'title' values
-----------------------

Check that values in the **title** column begin with an upper-case letter:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: test_title
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: TestMovies.test_title
            :lineno-match:

This validation checks that each value in the ``df['title']`` matches
the regular expression ``^[A-Z]``.


4. Check 'rating' values
------------------------

Check that values in the **rating** column match one of the allowed codes:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: test_rating
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: TestMovies.test_rating
            :lineno-match:

This validation checks that the values in ``df['rating']`` are also
contained in the given set.


5. Check 'year' and 'runtime' types
-----------------------------------

Check that values in the **year** and **runtime** columns are integers:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: test_year
            :lineno-match:

        .. literalinclude:: /_static/tutorial/test_movies_df.py
            :pyobject: test_runtime
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: TestMovies.test_year
            :lineno-match:

        .. literalinclude:: /_static/tutorial/test_movies_df_unit.py
            :pyobject: TestMovies.test_runtime
            :lineno-match:


================
More Information
================

.. seealso::

    See the :doc:`../reference/pandas-integration` reference docs
    for more information and examples.

    See :ref:`pandas-accessor-docs` to learn about the alternate
    validation syntax provided by pandas **accessor extensions**.

