
.. py:currentmodule:: datatest

.. meta::
    :description: How to run tests.
    :keywords: datatest, run, tests, unittest, pytest


################
How to Run Tests
################


.. tabs::

    .. group-tab:: Pytest

        If you have a pytest style script named ``test_mydata.py``,
        you can run it by typing the following at the command line:

        .. code-block:: none

            pytest test_mydata.py

        Datatest behaves as a pytest plugin and you run datatest
        validations the same way you would run any other pytest
        style tests---see pytest's standard |pytest-usage|_ for
        full details.

    .. group-tab:: Unittest

        If you have a unittest style script named ``test_mydata.py``,
        you can run it by typing the following at the command line:

        .. code-block:: none

            python -m datatest test_mydata.py

        Datatest includes a unittest style test-runner runs tests in
        line-number order (to support an incremental testing approach).
        See datatest's :ref:`unittest-style-invocation` for details.


..
  SUBSTITUTIONS:

.. |pytest-usage| replace:: Usage and Invocations
.. _pytest-usage: https://docs.pytest.org/en/latest/usage.html

