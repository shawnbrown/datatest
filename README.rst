
*************************************
datatest: Test driven data wrangling
*************************************

.. image:: https://api.travis-ci.org/shawnbrown/datatest.png
    :target: https://travis-ci.org/shawnbrown/datatest

Datatest extends Python's unittest package to provide testing tools
for asserting data correctness.

* Documentation:
    - http://datatest.readthedocs.io/ (latest)
    - http://datatest.readthedocs.io/en/0.7.0.dev2/ (stable)
* Official Releases:
   - https://pypi.python.org/pypi/datatest
* Development:
   - https://github.com/shawnbrown/datatest

Datatest can help prepare messy data that needs to be cleaned,
integrated, formatted, and verified. It can provide structure for the
tidying process, automate checklists, log discrepancies, and measure
progress.

.. note::
    This is a pre-1.0.0 release that is under active development.
    I'm aiming to release a stable API by the end of the year. But
    before this happens, I want to get some feedback, add support
    for more data sources, and improve py.test integration
    (including a pytest plugin).


Installation
============

The easiest way to install datatest is to use pip::

  pip install datatest


Stuntman Mike
-------------

If you need bug-fixes or features that are not available in the
current official release, you can "pip install" the *unstable*
development version directly from GitHub::

  pip install --upgrade https://github.com/shawnbrown/datatest/archive/master.zip

All of the usual caveats of a bleeding-edge install should apply here.
Only use an unstable development version if you can risk some
instability or if you know exactly what you're doing. While care is
taken to never break the build, it can happen.


Safety-first Clyde
------------------

If you need to review and test packages before installing, you can
install datatest manually.

Download the latest **source** distribution from the Python Package
Index (PyPI):

  https://pypi.python.org/pypi/datatest

Unpack the file (replacing X.Y.Z with the appropriate version number)
and review the source code::

  tar xvfz datatest-X.Y.Z.tar.gz

Change to the unpacked directory and run the tests::

  cd datatest-X.Y.Z
  python setup.py test

Don't worry if some of the tests are skipped.  Tests for optional data
sources (like pandas DataFrames or MS Excel files) are skipped when the
related third-party packages are not installed.

If the source code and test results are satisfactory, install the
package::

  python setup.py install


Supported Versions
==================

Tested on Python 2.6, 2.7, and 3.1 through 3.5; PyPy and PyPy3.
Datatest is pure Python and is also likely to run on Jython, Stackless,
and other implementations without issue (check using "setup.py test"
before installing).


Backward Compatibility
======================

If you have existing tests that use features which have changed since
0.6.0.dev1, you can still run your old code by adding the following
import to the beginning of each file::

  from datatest.__past__ import api_dev1

To maintain existing test code, this project makes a best-effort
attempt to provide backward compatibility support for older features.
The API will be improved in the future but only in measured and
sustainable ways.

All of the data used at the `National Committee for an Effective
Congress <http://ncec.org/about>`_ has been checked with datatest for
more than a year so there is, already, a large and growing codebase
that relies on current features and must be maintained into the future.


Dependencies
============

There are no hard dependencies. But if you want to interface with pandas
DataFrames, MS Excel workbooks, or other optional data sources, you will
need to install the relevant third-party packages (``pandas``, ``xlrd``,
etc.).


------------

Freely licensed under the Apache License, Version 2.0

Copyright 2014 - 2016 NCEC Services, LLC and contributing authors
