
.. meta::
    :description: datatest: Data testing tools for Python.
    :keywords: datatest, unittest, testing, test-driven data preparation

.. module:: datatest
    :synopsis: Data testing tools for Python.
.. moduleauthor:: Shawn Brown <sbrown@ncecservices.com>
.. sectionauthor:: Shawn Brown <sbrown@ncecservices.com>


#################################################
:mod:`datatest` --- Data testing tools for Python
#################################################

The :mod:`datatest` package provides data testing tools for Python.  It
contains classes for conveniently loading data, asserting validity, and
allowing for discrepancies when appropriate.  Datatest is based on Python's
`unittest <http://docs.python.org/3/library/unittest.html>`_ framework and is
compatible with standard unittest practices.

In the practice of data science, data preparation is a huge part of the job.
Practitioners often spend 50 to 80 percent of their time wrangling data.  This
critically important phase is time-consuming, unglamorous, and often poorly
structured.  :ref:`Test-driven data preparation <test-driven-data-preparation>`
can offer a disciplined approach to an otherwise messy process.

A :mod:`datatest` suite can facilitate quick edit-test cycles which help guide
the selection, cleaning, integration, and formatting of data.  Data tests can
also help to automate check-lists, measure progress, and promote best
practices.

(If you're already familiar with the package, you might want to
skip to the :ref:`list of assert methods <assert-methods>`.)


..
    SOURCES FOR TIME-SPENT-PREPARING-DATA CLAIM:

    "This has historically taken the largest part of the overall time in the
    data mining solution process, which in some cases can approach 80% of the
    time."
      -- "Dynamic Warehousing: Data Mining Made Easy", p. 19

    "As much as 80% of KDD is about preparing data, and the remaining 20% is
    about mining."
      -- "Data Mining for Design and Manufacturing", p. 44

    Online poll of data mining practitioners:
      http://www.kdnuggets.com/polls/2003/data_preparation.htm

    "Data scientists, according to interviews and expert estimates, spend from
    50 percent to 80 percent of their time mired in this more mundane labor of
    collecting and preparing unruly digital data..."
      -- Steve Lohraug in "For Big-Data Scientists, 'Janitor Work' Is Key
         Hurdle to Insights" http://www.nytimes.com/2014/08/18/technology/for-big-data-scientists-hurdle-to-insights-is-janitor-work.html


********
Contents
********

.. toctree::
   :maxdepth: 1

   overview
   contents
   custom

* :ref:`genindex`
* :ref:`search`
