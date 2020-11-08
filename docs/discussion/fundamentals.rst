
.. currentmodule:: datatest

.. meta::
    :description: A discussion of data testing fundamentals.
    :keywords: data, testing, incremental, validation, data-wrangling


#########################
Data Testing Fundamentals
#########################

Unlike unit testing of software, it's oftentimes not possible to check
data properties as independent "units" in isolation. Later tests often
depend on the success of earlier ones. For example, it's not useful
to try to check the datatype of an "account_id" column if there's
no column of that name. And it might not be useful to sum the values
in an "accounts_payable" column when the associated account IDs
contain invalid datatypes.

Typically, data tests should be run sequentially where broader, general
features are tested first and specific details are tested later (after
their prerequisite tests have passed). This approach is called "top-down,
incremental testing". You can use the following list as a rough guide
of which features to check before others.


Order to Check Features
-----------------------

1. data is accessible (by loading a file or connecting to a data source
   via a fixture)
2. names of tables or worksheets (if applicable)
3. names of columns
4. categorical columns: controlled vocabulary, set membership, etc.
5. foreign-keys (if applicable)
6. well-formedness of text values: date formats, phone numbers, etc.
7. datatypes: int, float, datetime, etc.
8. constraints: uniqueness, minimum and maximum values, etc.
9. accuracy of quantitative columns: compare sums, counts, or averages
   against known-good values
10. internal consistency, cross-column comparisons, etc.


..
    updating for errors discovered later
    don't just fix the data error and move on
    instead, devise a test that fails, then fix
    the data

