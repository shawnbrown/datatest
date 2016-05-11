
.. meta::
    :description: datatest: Testing tools for data preparation.
    :keywords: datatest, unittest, testing, data preparation, test-driven data preparation
    :title: Index

.. module:: datatest
    :synopsis: Testing tools for data preparation.
.. moduleauthor:: Shawn Brown <sbrown@ncecservices.com>
.. sectionauthor:: Shawn Brown <sbrown@ncecservices.com>


######################################################
:mod:`datatest` --- Testing tools for data preparation
######################################################

Datatest extends the standard library's `unittest
<http://docs.python.org/3/library/unittest.html>`_ package to provide testing
tools for asserting data correctness.

Datatest can help prepare messy data that needs to be cleaned,
integrated, formatted, and verified.  It can provide structure
for the tidying process, automate checklists, log discrepancies,
and measure progress.

To use datatest effectively, users should be familiar with Python's standard
`unittest <http://docs.python.org/library/unittest.html>`_ library and with
the data they want to test.  This said, testing data isn't the same as testing
software---please see :doc:`intro` for examples.  (If you're already familiar
with datatest, you might want to skip to the :ref:`list of assert methods
<assert-methods>`.)


********
Contents
********

.. toctree::
    :maxdepth: 2

    intro
    api
    custom

* :ref:`genindex`
* :ref:`search`
