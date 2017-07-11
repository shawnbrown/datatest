
.. meta::
    :description: Test driven data-wrangling can provide much-needed
                  structure to guide the workflow of data preparation,
                  itself.
    :keywords: test driven, data-wrangling


##########################
Test Driven Data-Wrangling
##########################

In the practice of data science, data preparation is a huge part of
the job. Practitioners often spend 50 to 80 percent of their time
wrangling data [1]_ [2]_ [3]_ [4]_.  This critically important phase
is time-consuming, unglamorous, and often poorly structured.

The :mod:`datatest` package was created to support test driven
data-wrangling and provide a disciplined approach to an otherwise
messy process.

A datatest suite can facilitate quick edit-test cycles to help guide
the selection, cleaning, integration, and formatting of data. Data tests
can also help to automate check-lists, measure progress, and promote
best practices.


************************
Structuring a Test Suite
************************

.. epigraph::

    *"Unix was not designed to stop you from doing stupid things,
    because that would also stop you from doing clever things."*
    ---Doug Gwyn [5]_

The structure of a datatest suite defines a data preparation workflow.
The first tests should address essential prerequisites and the following
tests should focus on specific requirements.

Typically, data tests should be defined in the following order:

 1. load data sources (asserts that expected source data is present)
 2. check for expected column names
 3. validate format of values (data type or other regex)
 4. assert set-membership requirements
 5. assert sums, counts, or cross-column values

.. note::

    Datatest's built-in test runner executes tests ordered
    by file name and then by line number within each file.
    You can control the order that tests are run by arranging
    the order they appear in the test file itself.


*************************
Data Preparation Workflow
*************************

Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make small changes to the data
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
datatest package itself.  Users can work with with the tools they find
the most productive (Excel, `pandas <http://pandas.pydata.org/>`_, R,
sed, etc.).


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

.. [3] Online poll of data mining practitioners: `See image <../_static/data_prep_poll.png>`_,
       *Data preparation (Oct 2003)*.
       Retrieved from http://www.kdnuggets.com/polls/2003/data_preparation.htm
       [While this poll is quite old, the situation has not changed
       drastically.]

.. [4] "As much as 80% of KDD is about preparing data, and the remaining 20%
        is about mining." *Data Mining for Design and Manufacturing* (p. 44)

.. [5] Doug Gwyn, Computer scientist for the U.S. Army Research Laboratory,
       as quoted in Michael Fitzgerald's *Introducing Regular Expressions*
       (p. 103)
