
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

.. autoclassinstance:: validate

    In addition to :class:`validate()`'s default behavior, the following
    methods can be used to specify additional validation behaviors.

    .. automethod:: predicate

    .. automethod:: approx

    .. automethod:: fuzzy

    .. automethod:: interval

    .. automethod:: set

    .. automethod:: subset

    .. automethod:: superset

    .. automethod:: unique

    .. automethod:: order

    .. note::

        Calling :class:`validate()` or its methods will either raise an
        exception or pass without error. To get an explicit True/False
        return value, use the :func:`valid` function instead.


.. autofunction:: valid


.. autoexception:: ValidationError

    .. autoattribute:: differences

    .. autoattribute:: description


.. _difference-docs:

***********
Differences
***********

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

Allowances are context managers that operate on a :class:`ValidationError`'s
collection of differences.

.. autoclass:: allowed

    .. automethod:: missing

    .. automethod:: extra

    .. automethod:: invalid

    .. automethod:: keys

    .. automethod:: args

    .. automethod:: fuzzy

    .. classmethod:: deviation(tolerance, /, msg=None)
                     deviation(lower, upper, msg=None)

        Allows numeric :class:`Deviations <datatest.Deviation>`
        within a given *tolerance* without triggering a test
        failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, allowed

            data = {'A': 45, 'B': 205}

            requirement = {'A': 50, 'B': 200}

            with allowed.deviation(5):  # <- tolerance of ±5
                validate(data, requirement)  # raises dictionary
                                             # {'A': Deviation(-5, 50),
                                             #  'B': Deviation(+5, 200)}

        Specifying different *lower* and *upper* bounds:

        .. code-block:: python
            :emphasize-lines: 1

            with allowed.deviation(-2, 7):  # <- tolerance from -2 to +7
                validate(..., ...)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.


    .. classmethod:: percent(tolerance, /, msg=None)
                     percent(lower, upper, msg=None)

        Allows :class:`Deviations <datatest.Deviation>` with
        percentages of error within a given *tolerance* without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, allowed

            data = {'A': 47, 'B': 212}

            requirement = {'A': 50, 'B': 200}

            with allowed.percent(0.06):  # <- tolerance of ±6%
                validate(data, requirement)  # raises dictionary
                                             # {'A': Deviation(-3, 50),
                                             #  'B': Deviation(+12, 200)}

        Specifying different *lower* and *upper* bounds:

        .. code-block:: python
            :emphasize-lines: 1

            with allowed.percent(-0.02, 0.01):  # <- tolerance from -2% to +1%
                validate(..., ...)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.


    .. automethod:: percent_deviation


    .. automethod:: specific


    .. automethod:: limit


Composability
=============

Allowances can be combined to create new allowances with modified
behavior.

The ``&`` operator can be used to create an *intersection* of
allowance criteria. In the following example, :meth:`allowed.missing`
and :meth:`allowed.limit` are combined into a single allowance that
accepts up to five Missing differences:

.. code-block:: python
    :emphasize-lines: 3

    from datatest import validate, allowed

    with allowed.missing() & allowed.limit(5):
        validate(..., ...)

The ``|`` operator can be used to create *union* of allowance
criteria. In the following example, :meth:`allowed.deviation`
and :meth:`allowed.percent` are combined into a single allowance
that accepts Deviations of ±10 as well as Deviations of ±5%:

.. code-block:: python
    :emphasize-lines: 3

    from datatest import validate, allowed

    with allowed.deviation(10) | allowed.percent(0.05):
        validate(..., ...)

And composed allowances, themselves, can be composed to define
increasingly specific criteria:

.. code-block:: python
    :emphasize-lines: 7

    from datatest import validate, allowed

    five_missing = allowed.missing() & allowed.limit(5)

    minor_deviations = allowed.deviation(10) | allowed.percent(0.05)

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
|       | | :meth:`allowed.missing`,    |                            |
|       | | :meth:`allowed.extra`,      |                            |
|       | | :meth:`allowed.invalid`,    |                            |
|   4   | | :meth:`allowed.keys`,       | Element-wise allowances    |
|       | | :meth:`allowed.args`,       |                            |
|       | | :meth:`allowed.deviation`,  |                            |
|       | | :meth:`allowed.percent`     |                            |
+-------+-------------------------------+----------------------------+
|   5   | | :meth:`allowed.specific`    | Group-wise allowances      |
+-------+-------------------------------+----------------------------+
|   6   | | :meth:`allowed.limit`       | Whole-error allowances     |
+-------+-------------------------------+----------------------------+


.. _predicate-docs:

**********
Predicates
**********

Datatest can use :class:`Predicate` objects for validation, certain
allowances, and querying data.

.. autoclass:: Predicate
