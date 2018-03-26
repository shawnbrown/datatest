
.. module:: datatest

.. meta::
    :description: Datatest Core API Reference
    :keywords: datatest, API, reference


###########################
Datatest Core API Reference
###########################


**********
Validation
**********

.. autofunction:: validate

.. autofunction:: valid


********
Failures
********

.. autoexception:: ValidationError

    .. autoattribute:: differences

    .. autoattribute:: description


Base Difference
===============

.. autoclass:: BaseDifference

    .. autoattribute:: args


Concrete Differences
====================

.. autoclass:: Missing


.. autoclass:: Extra


.. autoclass:: Invalid

    .. autoinstanceattribute:: datatest.difference.Invalid.invalid
       :annotation:

    .. autoinstanceattribute:: datatest.difference.Invalid.expected
       :annotation:


.. autoclass:: Deviation

    .. autoinstanceattribute:: datatest.difference.Deviation.deviation
       :annotation:

    .. autoinstanceattribute:: datatest.difference.Deviation.expected
       :annotation:


.. _allowance-docs:

**********
Allowances
**********

.. autoclass:: allowed_missing


.. autoclass:: allowed_extra


.. autoclass:: allowed_invalid


.. autoclass:: allowed_keys


.. autoclass:: allowed_args


.. class:: allowed_deviation(tolerance, /, msg=None)
           allowed_deviation(lower, upper, msg=None)

    Allows numeric :class:`Deviations <datatest.Deviation>`
    within a given *tolerance* without triggering a test
    failure::

        data = {'A': 45, 'B': 205}

        requirement = {'A': 50, 'B': 200}

        with datatest.allowed_deviation(5):  # <- tolerance of ±5
            datatest.validate(data, requirement)  # raises dictionary
                                                  # {'A': Deviation(-5, 50),
                                                  #  'B': Deviation(+5, 200)}

    Specifying different *lower* and *upper* bounds::

        with datatest.allowed_deviation(-2, 7):  # <- tolerance from -2 to +7
            datatest.validate(..., ...)

    Deviations within the given range are suppressed while those
    outside the range will trigger a test failure.

    Empty values (None, empty string, etc.) are treated as zeros
    when performing comparisons.


.. class:: allowed_percent(tolerance, /, msg=None)
           allowed_percent(lower, upper, msg=None)

    Allows :class:`Deviations <datatest.Deviation>` with
    percentages of error within a given *tolerance* without
    triggering a test failure::

        data = {'A': 47, 'B': 212}

        requirement = {'A': 50, 'B': 200}

        with datatest.allowed_percent(0.06):  # <- tolerance of ±6%
            datatest.validate(data, requirement)  # raises dictionary
                                                  # {'A': Deviation(-3, 50),
                                                  #  'B': Deviation(+12, 200)}

    Specifying different *lower* and *upper* bounds::

        with datatest.allowed_percent(-0.02, 0.01):  # <- tolerance from -2% to +1%
            datatest.validate(..., ...)

    Deviations within the given range are suppressed while those
    outside the range will trigger a test failure.

    Empty values (None, empty string, etc.) are treated as zeros
    when performing comparisons.


.. class:: allowed_percent_deviation

    alias of :class:`allowed_percent`


.. autoclass:: allowed_specific


.. autoclass:: allowed_limit


Composability
=============

Allowances can be combined to create new allowances with modified
behavior.

The ``&`` operator can be used to create an *intersection* of
allowance criteria. In the following example, :class:`allowed_missing`
and :class:`allowed_limit` are combined into a single allowance that
accepts up to five Missing differences::

    with allowed_missing() & allowed_limit(5):
        validate(..., ...)

The ``|`` operator can be used to create *union* of allowance
criteria. In the following example, :class:`allowed_deviation`
and :class:`allowed_percent` are combined into a single allowance
that accepts Deviations of ±10 as well as Deviations of ±5%::

    with allowed_deviation(10) | allowed_percent(0.05):
        validate(..., ...)

And composed allowances, themselves, can be composed to define
increasingly specific criteria::

    five_missing = allowed_missing() & allowed_limit(5)

    minor_deviations = allowed_deviation(10) | allowed_percent(0.05)

    with five_missing | minor_deviations:
        validate(..., ...)


Order of Operations
===================

Allowance composition uses the following order of
operations---shown from highest precedence to lowest
precedence. Operations with the same precedence level
(appearing in the same cell) are evaluated from left
to right.

+-------+-------------------------------+----------------------------+
| Order | Operation                     | Description                |
+=======+===============================+============================+
|   1   | | ``()``                      | Parentheses                |
+-------+-------------------------------+----------------------------+
|   2   | | ``&``                       | Bitwise AND (intersection) |
+-------+-------------------------------+----------------------------+
|   3   | | ``|``                       | Bitwise OR (union)         |
+-------+-------------------------------+----------------------------+
|       | | :class:`allowed_missing`,   |                            |
|       | | :class:`allowed_extra`,     |                            |
|       | | :class:`allowed_invalid`,   |                            |
|   4   | | :class:`allowed_keys`,      | Element-wise allowances    |
|       | | :class:`allowed_args`,      |                            |
|       | | :class:`allowed_deviation`, |                            |
|       | | :class:`allowed_percent`    |                            |
+-------+-------------------------------+----------------------------+
|   5   | | :class:`allowed_specific`   | Group-wise allowances      |
+-------+-------------------------------+----------------------------+
|   6   | | :class:`allowed_limit`      | Whole-error allowances     |
+-------+-------------------------------+----------------------------+


.. _predicate-docs:

**********
Predicates
**********

Datatest uses "predicate objects" to define the criteria that values
are matched against. The specific behavior of a predicate depends on
its type:

    +----------------------+---------------------------------------------------+
    | Predicate type       | Checks that                                       |
    +======================+===================================================+
    | set                  | | value is a member of the set                    |
    +----------------------+---------------------------------------------------+
    | function             | | the result of ``function(value)`` tests as True |
    |                      | | and is not a "difference" object                |
    +----------------------+---------------------------------------------------+
    | type                 | | value is an instance of the type                |
    +----------------------+---------------------------------------------------+
    | re.compile(pattern)  | | value matches the regular expression pattern    |
    +----------------------+---------------------------------------------------+
    | str or non-container | | value is equal to the predicate                 |
    +----------------------+---------------------------------------------------+
    | tuple of             | | tuple of values satisfies corresponding tuple   |
    | predicates           | | of predicates---each according to their type    |
    +----------------------+---------------------------------------------------+
    | "``...``" (an        | | (used as a wildcard, matches any value)         |
    | ellipsis)            |                                                   |
    +----------------------+---------------------------------------------------+

Predicates can be used as arguments for asserting validity and
for some allowances. For some examples, see the following table:

    +---------------------------+----------------+---------+
    | Example Predicate         | Example Value  | Matches |
    +===========================+================+=========+
    | .. code-block:: python    | ``'A'``        | Yes     |
    |                           +----------------+---------+
    |     {'A', 'B'}            | ``'C'``        | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``4``          | Yes     |
    |                           +----------------+---------+
    |     def iseven(x):        | ``9``          | No      |
    |         return x % 2 == 0 |                |         |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``1.0``        | Yes     |
    |                           +----------------+---------+
    |     float                 | ``1``          | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'bake'``     | Yes     |
    |                           +----------------+---------+
    |     re.compile('[bc]ake') | ``'cake'``     | Yes     |
    |                           +----------------+---------+
    |                           | ``'fake'``     | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'foo'``      | Yes     |
    |                           +----------------+---------+
    |     'foo'                 | ``'bar'``      | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``('A', 'X')`` | Yes     |
    |                           +----------------+---------+
    |     ('A', ...)            | ``('A', 'Y')`` | Yes     |
    |                           +----------------+---------+
    | Uses ellipsis wildcard.   | ``('B', 'X')`` | No      |
    +---------------------------+----------------+---------+
