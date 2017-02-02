
.. meta::
    :description: Test-driven data preparation can provide much-needed
                  structure to guide the workflow of data preparation,
                  itself.
    :keywords: test-driven data wrangling, data preperation, tidy data


****************
Data Preparation
****************

Data preparation is a signifigant and unglamorous part of data science.
The process is often poorly structured and regularly accounts for 50 to
80 percent of all project time [1]_ [2]_ [3]_ [4]_.

A test-driven approach to data wrangling can help by guiding
practitioners through the selection, cleaning, integration, and
formatting of data.  Structured data testing can automate check-lists,
measure progress, and promote best practices.


Test-Driven Data Wrangling
==========================

A :mod:`datatest` suite can facilitate quick edit-test cycles and
provide a disciplined approach to an otherwise messy process.

.. note::
    In the same way that software testing supplements other
    :abbr:`programming tools (e.g., IDEs, version control, debuggers)`,
    :mod:`datatest` supplements existing data wrangling processes---it
    doesn't replace them.

..  existing solutions
    prepare data
    but don't guide a user through the process
    make this data look like that data
    "where do I start"
    "what should I do next"
    each failing test is a sign-post that points to the next issue that need
    to be handled

    .. epigraph::
        Unix was not designed to stop you from doing stupid things, because
        that would also stop you from doing clever things. ---Doug Gwyn


Structuring a Test Suite
------------------------

The structure of a datatest suite defines a data preparation workflow.
The first tests should address essential prerequisites and the following
tests should focus on specific requirements.  Test cases and methods are
run *in order* (by line number).

Typically, data tests should be defined in the following order:

 1. load data sources (asserts that expected source data is present)
 2. check for expected column names
 3. validate format of values (data type or other regex)
 4. assert set-membership requirements
 5. assert sums, counts, or cross-column values

.. note::

    Datatest executes strictly ordered tests (ordered by package name
    then line number).


Data Preparation Workflow
-------------------------

Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make small changes to the data
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
datatest package itself.  Users can work with with the tools they find
the most productive (Excel, `pandas <http://pandas.pydata.org/>`_, R,
sed, etc.).


------------

.. rubric:: Footnotes

.. [1] "Data scientists, according to interviews and expert estimates, spend
        from 50 percent to 80 percent of their time mired in this more mundane
        labor of collecting and preparing unruly digital data..." Steve Lohraug
        in *For Big-Data Scientists, 'Janitor Work' Is Key Hurdle to Insights*.
        Retrieved from http://www.nytimes.com/2014/08/18/technology/for-big-data-scientists-hurdle-to-insights-is-janitor-work.html

.. [2] "This [data preparation step] has historically taken the largest part
        of the overall time in the data mining solution process, which in some
        cases can approach 80% of the time." *Dynamic Warehousing: Data Mining
        Made Easy* (p. 19)

.. [3] Online poll of data mining practitioners: `See image <_static/data_prep_poll.png>`_,
       *Data preparation (Oct 2003)*.
       Retrieved from http://www.kdnuggets.com/polls/2003/data_preparation.htm
       [While this poll is quite old, the situation has not changed
       drastically.]

.. [4] "As much as 80% of KDD is about preparing data, and the remaining 20%
        is about mining." *Data Mining for Design and Manufacturing* (p. 44)
