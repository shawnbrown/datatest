
.. meta::
    :description: datatest: Data testing tools for Python.
    :keywords: datatest, unittest, testing, test-driven data processing

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

In addition to quality control, a datatest suite can provide much-needed
structure to guide the work flow of data processing tasks.  :ref:`Test-driven
data processing <test-driven-data-processing>` can automate existing
check-lists, measure progress, promote best practices, and help acclimate new
team members.

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
