
Test-Driven Data Processing
=============================

Data tests can provide much-needed structure to guide the workflow of
data processing, itself.  *Test-driven data processing* can automate
existing check-lists, help train new team members in the work required,
and quickly re-acclimate users who have been away from the project for
a time.


Data Processing Workflow
--------------------------

Using a quick edit-test cycle, users can:

 * focus on a failing test
 * make small changes to the data
 * re-run the suite to check that the test now passes
 * then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
`datatest` package itself.  Users can work with with the tools they
find the most productive (Excel, `pandas`, R, sed, etc.).


Structuring a Data Test Suite
-------------------------------

Unlike most software testing, `datatest` runs tests *in-order* (by
line number).  When testing software, this behavior is typically
undesirable but it's an important feature when testing data.

Data tests range from unit tests to integration tests

 * load data sources
 * check for expected column names
 * validate format of values (data type or other regex)
 * check for set-membership requirements
 * assert sums or validate across multiple fields


Step-by-Step Example
----------------------

!!! TODO !!!

