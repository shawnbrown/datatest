
***************************
Test-Driven Data Processing
***************************

Data tests can provide much-needed structure to guide the workflow of
data processing, itself.  *Test-driven data processing* can automate
existing check-lists, help train new team members in the work required,
and quickly re-acclimate users who have been away from the project for
a time.


Data Processing Workflow
========================

Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make small changes to the data
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
:mod:`datatest` package itself.  Users can work with with the tools
they find the most productive (Excel, `pandas <http://pandas.pydata.org/>`_,
R, sed, etc.).


Structuring a Data Test Suite
=============================

Unlike most software testing, datatest runs tests *in-order* (by
line number).  When testing software, this behavior is typically
undesirable but it's an important feature when testing data.

Data tests range from unit tests to integration tests

 1. load data sources
 2. check for expected column names
 3. validate format of values (data type or other regex)
 4. check for set-membership requirements
 5. assert sums or validate across multiple fields

