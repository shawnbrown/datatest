
.. py:currentmodule:: datatest

.. meta::
    :description: How to run tests.
    :keywords: datatest, run, tests, unittest, pytest


################
How to Run Tests
################

======
Pytest
======

If you have a pytest style script named ``test_mydata.py``,
you can run it by typing the following at the command line:

.. code-block:: console

    pytest test_mydata.py

You invoke pytest just as you would in any other circumstance---see
pytest's standard |pytest-usage|_ for full details.


========
Unittest
========

If you have a unittest style script named ``test_mydata.py``,
you can run it by typing the following at the command line:

.. code-block:: console

    python -m datatest test_mydata.py

Datatest includes a unittest-style test runner that facilitates
incremental testing. It runs tests in declaration order (i.e.,
by line-number) and supports the :func:`@mandatory <mandatory>`
decorator.


..
  SUBSTITUTIONS:

.. |pytest-usage| replace:: Usage and Invocations
.. _pytest-usage: https://docs.pytest.org/en/latest/usage.html

