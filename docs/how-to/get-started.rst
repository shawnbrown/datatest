
.. currentmodule:: datatest

.. meta::
    :description: How to get started.
    :keywords: datatest, example, getting started


###############################
How to Get Started With Testing
###############################

Once you have reviewed the tutorials and have a basic understanding
of datatest, you should be ready to start testing your own data.


=========================================
1. Create a File and Add Some Sample Code
=========================================

A simple way to get started is to create a **.py** file in the same folder
as the data you want to test. It's a good idea to follow established testing
conventions and make sure your filename starts with "**test\_**".

Then, copy one of following the **pytest** or **unittest** code samples
to use as a template for writing your own tests:

.. raw:: html

   <details>
   <summary><a>Pytest Samples</a></summary>

.. include:: ../intro/automated-testing.rst
    :start-after: start-inclusion-marker-pytestsamples
    :end-before: end-inclusion-marker-pytestsamples

.. raw:: html

   </details>


.. raw:: html

   <details>
   <summary><a>Unittest Samples</a></summary>

.. include:: ../intro/automated-testing.rst
    :start-after: start-inclusion-marker-unittestsamples
    :end-before: end-inclusion-marker-unittestsamples

.. raw:: html

   </details>


==========================================
2. Adapt the Sample Code to Suit Your Data
==========================================

After copying the sample code into your own file, begin adapting
it to suit your data:

1. Change the fixture to use your data (instead of "example.csv").
2. Update the set in ``test_column_names()`` to require the names your
   data should contain (instead of "A", "B", and "C").
3. Rename ``test_a()`` and change it to check values in one of the
   columns in your data.
4. Add more tests appropriate for your own data requirements.


===================================
3. Refactor Your Tests as They Grow
===================================

As your tests grow, look to structure them into related groups. Start
by creating separate classes to contain groups of related test cases.
And as you develop more and more classes, create separate modules to
hold groups of related classes. If you are using ``pytest``, move your
fixtures into a ``conftest.py`` file.
