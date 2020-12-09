
.. currentmodule:: datatest

.. meta::
    :description: datatest API for unittest-style testing
    :keywords: datatest, unittest, data-wrangling


################
Unittest Support
################

Datatest can be used for unittest-style testing. For a quick
introduction, see:

* :ref:`Introduction <unittest-intro-docs>`
* :ref:`Basic Examples <unittest-samples-docs>`


.. _datatestcase-docs:

************
DataTestCase
************

.. autoclass:: DataTestCase

    The assertion methods wrap :func:`validate` and its methods:

    .. code-block:: python
        :emphasize-lines: 7

        from datatest import DataTestCase

        class MyTest(DataTestCase):
            def test_mydata(self):
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

    .. automethod:: assertValid

    .. automethod:: assertValidPredicate

    .. automethod:: assertValidRegex

    .. automethod:: assertValidApprox

    .. automethod:: assertValidFuzzy

    .. automethod:: assertValidInterval

    .. automethod:: assertValidSet

    .. automethod:: assertValidSubset

    .. automethod:: assertValidSuperset

    .. automethod:: assertValidUnique

    .. automethod:: assertValidOrder

    The acceptance methods wrap :func:`accepted` and its methods:

    .. code-block:: python
        :emphasize-lines: 7

        from datatest import DataTestCase

        class MyTest(DataTestCase):
            def test_mydata(self):
                data = ...
                requirement = ...
                with self.accepted(Missing):
                    self.assertValid(data, requirement)

    .. automethod:: accepted

    .. automethod:: acceptedKeys

    .. automethod:: acceptedArgs

    .. method:: acceptedTolerance(tolerance, /, msg=None)
                acceptedTolerance(lower, upper, msg=None)

        Wrapper for :meth:`accepted.tolerance`.

    .. method:: acceptedPercent(tolerance, /, msg=None)
                acceptedPercent(lower, upper, msg=None)

        Wrapper for :meth:`accepted.percent`.

    .. automethod:: acceptedFuzzy

    .. automethod:: acceptedCount


.. _unittest-style-invocation:

**********************
Command-Line Interface
**********************

The datatest module can be used from the command line just like
unittest. To run the program with `test discovery
<http://docs.python.org/library/unittest.html#test-discovery>`_
use the following command::

    python -m datatest

Run tests from specific modules, classes, or individual methods with::

    python -m datatest test_module1 test_module2
    python -m datatest test_module.TestClass
    python -m datatest test_module.TestClass.test_method

The syntax and command-line options (``-f``, ``-v``, etc.) are the
same as unittest---see unittest's `command-line documentation
<http://docs.python.org/library/unittest.html#command-line-interface>`_
for full details.

.. note::

    Tests are ordered by **file name** and then by **line number**
    (within each file) when running datatest from the command-line.

..
    Unlike strict unit testing, data preparation tests are often
    dependant on one another---this strict order-by-line-number
    behavior lets users design test suites appropriately.
    For example, asserting the population of a city will always
    fail when the 'city' column is missing. So it's appropriate
    to validate column names *before* validating the contents of
    each column.


*******************
Test Runner Program
*******************

.. py:decorator:: mandatory

    A decorator to mark whole test cases or individual methods as
    mandatory.  If a mandatory test fails, DataTestRunner will stop
    immediately (this is similar to the ``--failfast`` command line
    argument behavior)::

        @datatest.mandatory
        class TestFileFormat(datatest.DataTestCase):
            def test_columns(self):
                ...

.. autodecorator:: skip(reason)


.. autodecorator:: skipIf


.. autodecorator:: skipUnless


.. autoclass:: DataTestRunner
    :members:
    :inherited-members:

.. autoclass:: DataTestProgram(module='__main__', defaultTest=None, argv=None, testRunner=datatest.DataTestRunner, testLoader=unittest.TestLoader, exit=True, verbosity=1, failfast=None, catchbreak=None, buffer=None, warnings=None)
    :members:
    :inherited-members:

|

.. autoclass:: main
   :members:
   :inherited-members:
