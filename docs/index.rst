
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
In recent studies, experts estimate that 50 to 80 percent of time is spent
wrangling data.  This critically important phase is time-consuming,
unglamorous, and often poorly structured.

:ref:`Test-driven data preparation <test-driven-data-preparation>` can provide
much-needed structure to the process.  Automated data testing allows for quick
edit-test cycles which help guide the selection, cleaning, integration, and
formatting of data.  Data tests can also help to automate check-lists, measure
progress, and promote best practices.

(If you're already familiar with the package, you might want to
skip to the :ref:`list of assert methods <assert-methods>`.)

.. toctree::
   :maxdepth: 2

   getting_started
   data_processing
   datatestcase
   datasources
   reference_misc


Index
=====

* :ref:`genindex`
* :ref:`search`
