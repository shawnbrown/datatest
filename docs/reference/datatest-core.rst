
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

    .. autoattribute:: invalid

    .. autoattribute:: expected


.. autoclass:: Deviation

    .. autoattribute:: deviation

    .. autoattribute:: expected


.. _acceptance-docs:

***********
Acceptances
***********

Acceptances are context managers that operate on a :class:`ValidationError`'s
collection of differences.

.. autoclassinstance:: accepted

    .. automethod:: keys

    .. automethod:: args

    .. method:: tolerance(tolerance, /, msg=None)
                tolerance(lower, upper, msg=None)

        Accepts numeric :class:`Deviations <datatest.Deviation>`
        within a given *tolerance* without triggering a test
        failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 45, 'B': 205}

            requirement = {'A': 50, 'B': 200}

            with accepted.tolerance(5):  # <- tolerance of ±5
                validate(data, requirement)  # raises dictionary
                                             # {'A': Deviation(-5, 50),
                                             #  'B': Deviation(+5, 200)}

        Specifying different *lower* and *upper* bounds:

        .. code-block:: python
            :emphasize-lines: 1

            with accepted.tolerance(-2, 7):  # <- tolerance from -2 to +7
                validate(..., ...)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. method:: percent(tolerance, /, msg=None)
                percent(lower, upper, msg=None)

        Accepts :class:`Deviations <datatest.Deviation>` with
        percentages of error within a given *tolerance* without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 47, 'B': 212}

            requirement = {'A': 50, 'B': 200}

            with accepted.percent(0.06):  # <- tolerance of ±6%
                validate(data, requirement)  # raises dictionary
                                             # {'A': Deviation(-3, 50),
                                             #  'B': Deviation(+12, 200)}

        Specifying different *lower* and *upper* bounds:

        .. code-block:: python
            :emphasize-lines: 1

            with accepted.percent(-0.02, 0.01):  # <- tolerance from -2% to +1%
                validate(..., ...)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. automethod:: fuzzy

    .. automethod:: count


Composability
=============

Acceptances can be combined to create new acceptances with modified
behavior.

The ``&`` operator can be used to create an *intersection* of
acceptance criteria. In the following example, :meth:`accepted.missing`
and :meth:`accepted.count` are combined into a single acceptance that
accepts up to five Missing differences:

.. code-block:: python
    :emphasize-lines: 3

    from datatest import validate, accepted

    with accepted.missing() & accepted.count(5):
        validate(..., ...)

The ``|`` operator can be used to create *union* of acceptance
criteria. In the following example, :meth:`accepted.deviation`
and :meth:`accepted.percent` are combined into a single acceptance
that accepts Deviations of ±10 as well as Deviations of ±5%:

.. code-block:: python
    :emphasize-lines: 3

    from datatest import validate, accepted

    with accepted.deviation(10) | accepted.percent(0.05):
        validate(..., ...)

And composed acceptances, themselves, can be composed to define
increasingly specific criteria:

.. code-block:: python
    :emphasize-lines: 7

    from datatest import validate, accepted

    five_missing = accepted.missing() & accepted.count(5)

    minor_deviations = accepted.deviation(10) | accepted.percent(0.05)

    with five_missing | minor_deviations:
        validate(..., ...)


Order of Operations
===================

Acceptance composition uses the following order of
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
|       | | :meth:`accepted.missing`,   |                            |
|       | | :meth:`accepted.extra`,     |                            |
|       | | :meth:`accepted.invalid`,   |                            |
|   4   | | :meth:`accepted.keys`,      | Element-wise acceptances   |
|       | | :meth:`accepted.args`,      |                            |
|       | | :meth:`accepted.deviation`, |                            |
|       | | :meth:`accepted.percent`    |                            |
+-------+-------------------------------+----------------------------+
|   5   | | :meth:`accepted.specific`   | Group-wise acceptances     |
+-------+-------------------------------+----------------------------+
|   6   | | :meth:`accepted.count`      | Whole-error acceptances    |
+-------+-------------------------------+----------------------------+


.. _predicate-docs:

**********
Predicates
**********

Datatest can use :class:`Predicate` objects for validation, certain
acceptances, and querying data.

.. autoclass:: Predicate
