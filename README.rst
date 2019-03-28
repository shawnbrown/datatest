
********************************************************
datatest: Test driven data-wrangling and data validation
********************************************************

..
    Project badges for quick reference:

|buildstatus| |devstatus| |license| |pyversions|


.. start-inclusion-marker-description

Datatest provides testing tools for data validation and analysis.
It supports both pytest_ and unittest_ style testing.

You can use datatest for validation, test driven data-wrangling,
auditing, logging discrepancies, and checklists for measuring
progress. It encourages a structured approach for checking and
tidying data.

Datatest has no hard dependencies; supports Python 2.6, 2.7,
3.1 through 3.7, PyPy, and PyPy3; and is freely available under
the Apache License, version 2.

.. _pytest: https://pytest.org
.. _unittest: https://docs.python.org/library/unittest.html

.. end-inclusion-marker-description


:Documentation:
    | https://datatest.readthedocs.io/ (stable)
    | https://datatest.readthedocs.io/en/latest/ (latest)

:Official:
    | https://pypi.org/project/datatest/


Installation
============

.. start-inclusion-marker-install

The easiest way to install datatest is to use `pip <https://pip.pypa.io>`_::

  pip install datatest

To upgrade an existing installation, use the "``--upgrade``" option::

  pip install --upgrade datatest


Stuntman Mike
-------------

If you need bug-fixes or features that are not available
in the current stable release, you can "pip install" the
development version directly from GitHub::

  pip install --upgrade https://github.com/shawnbrown/datatest/archive/master.zip

All of the usual caveats for a development install should
apply---only use this version if you can risk some instability
or if you know exactly what you're doing. While care is taken
to never break the build, it can happen.


Safety-first Clyde
------------------

If you need to review and test packages before installing, you can
install datatest manually.

Download the latest **source** distribution from the Python Package
Index (PyPI):

  https://pypi.org/project/datatest/ (navigate to "Download files")

Unpack the file (replacing X.Y.Z with the appropriate version number)
and review the source code::

  tar xvfz datatest-X.Y.Z.tar.gz

Change to the unpacked directory and run the tests::

  cd datatest-X.Y.Z
  python setup.py test

Don't worry if some of the tests are skipped. Tests for optional data
sources (like pandas DataFrames or MS Excel files) are skipped when the
related third-party packages are not installed.

If the source code and test results are satisfactory, install the
package::

  python setup.py install

.. end-inclusion-marker-install


Supported Versions
==================

Tested on Python 2.6, 2.7, 3.1 through 3.7, PyPy, and PyPy3.
Datatest is pure Python and may also run on other implementations
as well (check using "setup.py test" before installing).


Backward Compatibility
======================

If you have existing tests that use API features which have
changed since 0.8.0, you can still run your old code by
adding the following import to the beginning of each file::

  from datatest.__past__ import api08

To maintain existing test code, this project makes a best-effort
attempt to provide backward compatibility support for older
features. The API will be improved in the future but only in
measured and sustainable ways.

All of the data used at the `National Committee for an Effective
Congress <http://www.ncec.org/about>`_ has been checked with
datatest for several years so there is, already, a large and
growing codebase that relies on current features and must be
maintained into the future.


Soft Dependencies
=================

There are no hard, third-party dependencies. But if you want to
interface with pandas DataFrames, MS Excel workbooks, or other
optional data sources, you will need to install the relevant
packages (``pandas``, ``xlrd``, etc.).


Older Pythons (3.1 and 2.6)
===========================

While datatest supports Python 3.1 and 2.6, some earlier builds
of these versions were bundled with an older version of SQLite
that is not compatible with datatest. The ``sqlite3`` package is
part of the Python Standard Library and some features of datatest
use it for internal data handling---though users never need to
use the package directly.

If you must use one of these older Python versions and you are
experiencing issues, it is recommended that you upgrade to the
latest patch release (currently Python 3.1.5 or Python 2.6.9).


Development Repository
======================

The development repository for ``datatest`` is hosted on
`GitHub <https://github.com/shawnbrown/datatest>`_.


----------

Freely licensed under the Apache License, Version 2.0

Copyright 2014 - 2019 National Committee for an Effective Congress, et al.


..
  SUBSTITUTION DEFINITONS:

.. |buildstatus| image:: https://travis-ci.org/shawnbrown/datatest.svg?branch=master
    :target: https://travis-ci.org/shawnbrown/datatest
    :alt: Current Build Status

.. |devstatus| image:: https://img.shields.io/pypi/status/datatest.svg
    :target: https://pypi.org/project/datatest/
    :alt: Development Status

.. |license| image:: https://img.shields.io/badge/license-Apache%202-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache 2.0 License

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/datatest.svg
    :target: https://pypi.org/project/datatest/#supported-versions
    :alt: Supported Python Versions

.. |githubstars| image:: https://img.shields.io/github/stars/shawnbrown/datatest.svg
    :target: https://github.com/shawnbrown/datatest/stargazers
    :alt: GitHub users who have starred this project

.. |pypiversion| image:: https://img.shields.io/pypi/v/datatest.svg
    :target: https://pypi.org/project/datatest/
    :alt: Current PyPI Version
