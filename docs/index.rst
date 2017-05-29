
.. meta::
    :description: Datatest provides validation tools for test-driven data wrangling.
    :keywords: datatest, data wrangling, unittest, data preparation
    :title: Index

.. module:: datatest
    :synopsis: Testing driven data wrangling.
.. moduleauthor:: Shawn Brown <sbrown@ncecservices.com>
.. sectionauthor:: Shawn Brown <sbrown@ncecservices.com>


#################################################
:mod:`datatest` --- Testing driven data wrangling
#################################################

Datatest provides validation tools for test-driven data wrangling.
It extends Python's `unittest
<http://docs.python.org/3/library/unittest.html>`_ package to provide
testing tools for asserting data correctness.

..
    It provides tools to quickly load, query, and validate data
    using both unittest- and pytest-style testing.

When a test fails, users are presented with a list of differences to
help identify data quality issues:

.. code-block:: none
    :emphasize-lines: 5-8

    Traceback (most recent call last):
      File "test_census_update.py", line 13, in test_population
        self.assertValid(population, census_total)
    datatest.error.DataError: different column sums:
     'Franklin': Deviation(-1, 71372),
     'Jackson': Deviation(+8, 160248),
     'Jefferson': Deviation(+1, 116229),
     'Washington': Deviation(-3, 17581)

If differences are considered acceptable, they can be allowed inside
a ``with`` statement:

.. code-block:: python
    :emphasize-lines: 1

    with self.allowedDeviation(8):  # Allows deviations of +/- 8.
        self.assertValid(population, census_total)

To understand the basics of datatest, please see :doc:`intro`.  To use
datatest effectively, users should be familiar with Python's standard
unittest library and with the data they want to test.


*************
Quick Install
*************

.. code-block:: none

    pip install datatest

For installation details, see https://pypi.python.org/pypi/datatest or
the README.rst file included with the source distribution.


********
Contents
********

.. toctree::
    :maxdepth: 2

    intro
    dataprep
    unittest_style
    data_handling

* :ref:`genindex`
