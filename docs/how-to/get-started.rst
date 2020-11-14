
.. currentmodule:: datatest

.. meta::
    :description: How to get started.
    :keywords: datatest, example, getting started


###############################
How to Get Started With Testing
###############################

.. sidebar:: Example Data

    The samples here are written to test the following
    :download:`example.csv </_static/example.csv>`:

    ===  ===  ===
     A    B    C
    ===  ===  ===
     x   foo   20
     x   foo   30
     y   foo   10
     y   bar   20
     z   bar   10
     z   bar   10
    ===  ===  ===

Once you have reviewed the tutorials and have a basic understanding
of datatest, you should be ready to start testing your own data.


====================================
1. Copy One of the Following Samples
====================================

A simple way to get started is to create a **.py** file in the same folder
as the data you want to test. It's a good idea to follow established testing
conventions and make sure your filename starts with "**test\_**". Then, copy
one of the code samples from :doc:`/intro/automated-testing` into your file
and begin changing the tests to suit your own data.


======================================
2. Adapt Sample Code to Suit Your Data
======================================

After copying the sample code into your own file, you can begin to
adapt it to meet your own needs:

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
