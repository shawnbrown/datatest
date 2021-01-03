
********************************************************
datatest: Test driven data-wrangling and data validation
********************************************************

..
    Project badges for quick reference:

|buildstatus| |devstatus| |license| |pyversions|


Datatest helps to speed up and formalize data-wrangling and data
validation tasks. It implements a system of validation methods,
difference classes, and acceptance managers. Datatest can help you:

* Clean and wrangle data faster and more accurately.
* Maintain a record of checks and decisions regarding important data sets.
* Distinguish between ideal criteria and acceptible deviation.
* Validate the input and output of data pipeline components.
* Measure progress of data preparation tasks.
* On-board new team members with an explicit and structured process.

Datatest can be used directly in your own projects or as part of a testing
framework like pytest_ or unittest_. It has no hard dependencies; it's
tested on Python 2.6, 2.7, 3.2 through 3.10, PyPy, and PyPy3; and is freely
available under the Apache License, version 2.

.. _pytest: https://pytest.org
.. _unittest: https://docs.python.org/library/unittest.html


:Documentation:
    | https://datatest.readthedocs.io/ (stable)
    | https://datatest.readthedocs.io/en/latest/ (latest)

:Official:
    | https://pypi.org/project/datatest/


Code Examples
=============

Validating a Dictionary of Lists
--------------------------------

.. code-block:: python

    from datatest import validate, accepted, Invalid


    data = {
        'A': [1, 2, 3, 4],
        'B': ['x', 'y', 'x', 'x'],
        'C': ['foo', 'bar', 'baz', 'EMPTY']
    }

    validate(data.keys(), {'A', 'B', 'C'})

    validate(data['A'], int)

    validate(data['B'], {'x', 'y'})

    with accepted(Invalid('EMPTY')):
        validate(data['C'], str.islower)


Validating a Pandas DataFrame
-----------------------------

.. code-block:: python

    import pandas as pd
    from datatest import register_accessors, accepted, Invalid


    register_accessors()
    df = pd.read_csv('data.csv')

    df.columns.validate({'A', 'B', 'C'})

    df['A'].validate(int)

    df['B'].validate({'x', 'y'})

    with accepted(Invalid('EMPTY')):
        df['C'].validate(str.islower)


Installation
============

.. start-inclusion-marker-install

The easiest way to install datatest is to use `pip <https://pip.pypa.io>`_:

.. code-block:: console

    pip install datatest

If you are upgrading from version 0.11.0 or newer, use the ``--upgrade``
option:

.. code-block:: console

    pip install --upgrade datatest


Upgrading From Version 0.9.6
----------------------------

If you have an existing codebase of older datatest scripts, you should
upgrade using the following steps:

* Install datatest 0.10.0 first:

  .. code-block:: console

      pip install --force-reinstall datatest==0.10.0

* Run your existing code and check for DeprecationWarnings.

* Update the parts of your code that use deprecated features.

* Once your code is running without DeprecationWarnings,
  install the latest version of datatest:

  .. code-block:: console

      pip install --upgrade datatest


Stuntman Mike
-------------

If you need bug-fixes or features that are not available
in the current stable release, you can "pip install" the
development version directly from GitHub:

.. code-block:: console

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

    https://pypi.org/project/datatest/#files

Unpack the file (replacing X.Y.Z with the appropriate version number)
and review the source code:

.. code-block:: console

    tar xvfz datatest-X.Y.Z.tar.gz

Change to the unpacked directory and run the tests:

.. code-block:: console

    cd datatest-X.Y.Z
    python setup.py test

Don't worry if some of the tests are skipped. Tests for optional data
sources (like pandas DataFrames or NumPy arrays) are skipped when the
related third-party packages are not installed.

If the source code and test results are satisfactory, install the
package:

.. code-block:: console

    python setup.py install

.. end-inclusion-marker-install


Supported Versions
==================

Tested on Python 2.6, 2.7, 3.2 through 3.10, PyPy, and PyPy3.
Datatest is pure Python and may also run on other implementations
as well (check using "setup.py test" before installing).


Backward Compatibility
======================

If you have existing tests that use API features which have
changed since 0.9.0, you can still run your old code by
adding the following import to the beginning of each file:

.. code-block:: python

    from datatest.__past__ import api09

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

Datatest has no hard, third-party dependencies. But if you want
to interface with pandas DataFrames, NumPy arrays, or other
optional data sources, you will need to install the relevant
packages (``pandas``, ``numpy``, etc.).


Development Repository
======================

The development repository for ``datatest`` is hosted on
`GitHub <https://github.com/shawnbrown/datatest>`_.


----------

Freely licensed under the Apache License, Version 2.0

Copyright 2014 - 2021 National Committee for an Effective Congress, et al.


..
  SUBSTITUTION DEFINITONS:

.. |buildstatus| image:: https://img.shields.io/travis/shawnbrown/datatest?logo=travis-ci&logoColor=white&style=flat-square
    :target: https://travis-ci.org/shawnbrown/datatest
    :alt: Current Build Status

.. |devstatus| image:: https://img.shields.io/pypi/status/datatest.svg?logo=pypi&logoColor=white&style=flat-square
    :target: https://pypi.org/project/datatest/
    :alt: Development Status

.. |license| image:: https://img.shields.io/badge/license-Apache 2-blue.svg?logo=open-source-initiative&logoColor=white&style=flat-square
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache 2.0 License

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/datatest.svg?logo=python&logoColor=white&style=flat-square
    :target: https://pypi.org/project/datatest/#supported-versions
    :alt: Supported Python Versions

.. |githubstars| image:: https://img.shields.io/github/stars/shawnbrown/datatest.svg?logo=github&logoColor=white&style=flat-square
    :target: https://github.com/shawnbrown/datatest/stargazers
    :alt: GitHub users who have starred this project

.. |pypiversion| image:: https://img.shields.io/pypi/v/datatest.svg?logo=pypi&logoColor=white&style=flat-square
    :target: https://pypi.org/project/datatest/
    :alt: Current PyPI Version

