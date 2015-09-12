
.. meta::
    :description: Test-driven data processing can provide much-needed
                  structure to guide the workflow of data processing,
                  itself.
    :keywords: test-driven data processing


.. _test-driven-data-processing:

***************************
Test-Driven Data Processing
***************************

The strucure of a :mod:`datatest` suite helps to guide the data
processing workflow.  It can also help supplement or replace check-lists
and progress reports.


Workflow
========

Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make small changes to the data
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
datatest package itself.  Users can work with with the tools they find
the most productive (Excel, `pandas <http://pandas.pydata.org/>`_, R,
sed, etc.).


Structuring a Data Test Suite
=============================

The structure of a datatest suite defines a data processing workflow.
The first cases should address essential prerequisites and the following
cases should focus on specific requirements.  Test cases and methods are
run *in order* (by line number).

Typically, data tests should be defined in the following order:

 1. load data sources (asserts that expected source data is present)
 2. check for expected column names
 3. validate format of values (data type or other regex)
 4. assert set-membership requirements
 5. assert sums, counts, or cross-column values

.. note::

    Datatest implements ordered tests but don't expect other tools to
    do so.  Ordered tests are useful when testing data but not so useful
    when testing software.  In fact, ordered testing of software can
    lead to problems if side-effects from one test affect the outcome of
    following tests.
