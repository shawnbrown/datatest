
.. module:: datatest


************
DataTestCase
************

This class inherits from
`unittest.TestCase <http://docs.python.org/library/unittest.html#unittest.TestCase>`_
and adds additional properties and methods to help with testing data.
In addition to the new functionality, the familiar ``TestCase`` methods
(like ``setUp``, ``assertEqual``, etc.) are still available.


.. autoclass:: datatest.DataTestCase

    .. autoattribute:: subjectData
    .. autoattribute:: referenceData

    .. _assert-methods:

    Column assertions operate on the column names (or header row) of a
    data source:

    +---------------------------------------------------+----------------------------------------------+
    | Method                                            | Checks that                                  |
    +===================================================+==============================================+
    | :meth:`assertColumnSet()                          | subject columns == reference columns         |
    | <datatest.DataTestCase.assertColumnSet>`          |                                              |
    +---------------------------------------------------+----------------------------------------------+
    | :meth:`assertColumnSubset()                       | subject columns <= reference columns         |
    | <datatest.DataTestCase.assertColumnSubset>`       |                                              |
    +---------------------------------------------------+----------------------------------------------+
    | :meth:`assertColumnSuperset()                     | subject columns >= reference columns         |
    | <datatest.DataTestCase.assertColumnSuperset>`     |                                              |
    +---------------------------------------------------+----------------------------------------------+

    .. automethod:: assertColumnSet
    .. automethod:: assertColumnSubset
    .. automethod:: assertColumnSuperset

    Value assertions operate on the values within a given column:

    +----------------------------------------------+----------------------------------------------------+
    | Method                                       | Checks that                                        |
    +==============================================+====================================================+
    | :meth:`assertValueSet(c)                     | subject vals == reference vals in column *c*       |
    | <datatest.DataTestCase.assertValueSet>`      |                                                    |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueSubset(c)                  | subject vals <= reference vals in column *c*       |
    | <datatest.DataTestCase.assertValueSubset>`   |                                                    |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueSuperset(c)                | subject vals <= reference vals in column *c*       |
    | <datatest.DataTestCase.assertValueSuperset>` |                                                    |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueSum(c, g)                  | sum of subject vals == sum of reference vals in    |
    | <datatest.DataTestCase.assertValueSum>`      | column *c* for each group of *g*                   |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueCount(c, g)                | count of subject rows == sum of reference vals in  |
    | <datatest.DataTestCase.assertValueCount>`    | column *c* for each group of *g*                   |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueRegex(c, r)                | *r*.search(val) for subject vals in column *c*     |
    | <datatest.DataTestCase.assertValueRegex>`    |                                                    |
    +----------------------------------------------+----------------------------------------------------+
    | :meth:`assertValueNotRegex(c, r)             | not *r*.search(val) for subject vals in column *c* |
    | <datatest.DataTestCase.assertValueNotRegex>` |                                                    |
    +----------------------------------------------+----------------------------------------------------+

    .. automethod:: assertValueSet
    .. automethod:: assertValueSubset
    .. automethod:: assertValueSuperset
    .. automethod:: assertValueSum
    .. automethod:: assertValueCount
    .. automethod:: assertValueRegex
    .. automethod:: assertValueNotRegex

    +-------------------------------------------------+------------------------------------------+
    | Accept method                                   | Accepts that                             |
    +=================================================+==========================================+
    | :meth:`acceptDifference(diff)                   | differences match those in *diff*        |
    | <datatest.DataTestCase.acceptDifference>`       |                                          |
    +-------------------------------------------------+------------------------------------------+
    | :meth:`acceptTolerance(tolerance)               | absolute values of numeric differences   |
    | <datatest.DataTestCase.acceptTolerance>`        | are equal to or less than *tolerance*    |
    +-------------------------------------------------+------------------------------------------+
    | :meth:`acceptPercentTolerance(tolerance)        | percentage values of numeric differences |
    | <datatest.DataTestCase.acceptPercentTolerance>` | are equal to or less than *tolerance*    |
    +-------------------------------------------------+------------------------------------------+

    .. automethod:: acceptDifference
    .. automethod:: acceptTolerance
    .. automethod:: acceptPercentTolerance


Optional Keyword Filters (using \*\*filter_by)
----------------------------------------------

All of the value assertion methods, above, support optional keyword
arguments to quickly filter the rows to be tested.

The following example asserts that the subject's ``postal_code`` values
match the reference's ``postal_code`` values but only for records where
the ``state`` equals ``'Ohio'`` and the ``city`` equals ``'Columbus'``::

    self.assertValueSet('postal_code', state='Ohio', city='Columbus')

The next example makes this same assertion but for records where the
``state`` equals ``'Indiana'`` *or* ``'Ohio'``::

    self.assertValueSet('postal_code', state=['Indiana', 'Ohio'])

