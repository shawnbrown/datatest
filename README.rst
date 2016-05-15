
********************************************
datatest: Testing tools for data preparation
********************************************

Datatest extends the Python standard library's unittest package to
provide testing tools for asserting data correctness.

* Documentation: <readthedocs-link-here>
* Official Releases: https://pypi.python.org/pypi/datatest
* Development: https://github.com/shawnbrown/datatest

Datatest can help prepare messy data that needs to be cleaned,
integrated, formatted, and verified. It can provide structure for the
tidying process, automate checklists, log discrepancies, and measure
progress.


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
install datatest manually:

Download the latest version from https://pypi.python.org/pypi/datatest

Unpack the file and review the source code (replacing X.Y.Z with the
appropriate version number)::

  tar xvfz datatest-X.Y.Z.tar.gz

Change to the unpacked directory and run the tests::

  cd datatest-X.Y.Z
  python setup.py test

Please Note: Tests for optional data sources (like pandas DataFrames or
MS Excel files) are skipped if the related third-party packages are not
installed.

If everything looks good, install the package::

  python setup.py install


Supported Versions
==================

Tested on Python versions 3.5, 3.4, 3.3, 3.2, 3.1, 2.7 and 2.6.
Datatest is pure Python and is likely to run on PyPy, Jython, and other
implementations without issues (check with "setup.py test" before
installing).


Future Plans
============

We're aiming to release a 1.0.0, stable API by the end of the year. But
before this happens, we want to get community feedback, add support for
more data sources, and improve py.test integration (including a py.test
plugin).

This said, all of the data used at the `National Committee for an
Effective Congress <http://ncec.org/about>`_ has been checked with test
suites built on datatest for more than a year. The API may adjust in
small ways but drastic changes are not anticipated.


Dependencies
============

There are no hard dependencies. But if you want to interface with pandas
DataFrames, MS Excel workbooks, or other optional data sources, you will
need to install the relevant third-party packages (``pandas``, ``xlrd``,
etc.).


------------

Freely licensed under the Apache License, Version 2.0

Copyright 2014 - 2016 NCEC Services, LLC and contributing authors
