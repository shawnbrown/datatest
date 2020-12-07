
.. currentmodule:: datatest

.. meta::
    :description: How to validate date and time objects.
    :keywords: datatest, datetime, date, time, validation


#####################################
How to Validate Date and Time Objects
#####################################


Equality Validation
===================

You can compare :py:class:`date <datetime.date>` and :py:class:`datetime
<datetime.datetime>` objects just as you would any other quantitative value:

.. code-block:: python
    :emphasize-lines: 4,6
    :linenos:

    from datetime import date, datetime
    from datatest import validate

    validate(date(2020, 12, 25), date(2020, 12, 25))

    validate(datetime(2020, 12, 25, 9, 30), datetime(2020, 12, 25, 9, 30))


Compare mappings of date objects:

.. code-block:: python
    :emphasize-lines: 16
    :linenos:

    from datetime import date
    from datatest import validate

    data = {
        'A': date(2020, 12, 24),
        'B': date(2020, 12, 25),
        'C': date(2020, 12, 26),
    }

    requirement = {
        'A': date(2020, 12, 24),
        'B': date(2020, 12, 25),
        'C': date(2020, 12, 26),
    }

    validate(data, requirement)


Interval Validation
===================

We can use :meth:`validate.interval` to check that date and datetime
values are within a given range.


Check that dates fall within the month of December 2020:

.. code-block:: python
    :emphasize-lines: 11
    :linenos:

    from datetime import date
    from datatest import validate

    data = [
        date(2020, 12, 4),
        date(2020, 12, 11),
        date(2020, 12, 18),
        date(2020, 12, 25),
    ]

    validate.interval(data, min=date(2020, 12, 1), max=date(2020, 12, 31))


Check that dates are one week old or newer:

.. code-block:: python
    :emphasize-lines: 11
    :linenos:

    from datetime import date, timedelta
    from datatest import validate

    data = {
        'A': date(2020, 12, 24),
        'B': date(2020, 12, 25),
        'C': date(2020, 12, 26),
    }

    one_week_ago = date.today() - timedelta(days=7)
    validate.interval(data, min=one_week_ago, msg='one week old or newer')


Failures and Acceptances
========================

When validation fails, a Deviation is generated containing a
:py:class:`timedelta <datetime.timedelta>` that represents the
difference between two dates or times. You can accept time
differences with :meth:`accepted.tolerance`.


Failed Equality
---------------

.. tabs::

    .. group-tab:: Failure

        .. code-block:: python
            :linenos:

            from datetime import date
            from datatest import validate

            validate(date(2020, 12, 27), date(2020, 12, 25))


        .. code-block:: none
            :emphasize-lines: 5

            Traceback (most recent call last):
              File "example.py", line 4, in <module>
                validate(date(2020, 12, 27), date(2020, 12, 25))
            ValidationError: does not satisfy date(2020, 12, 25) (1 difference): [
                Deviation(timedelta(days=+2), date(2020, 12, 25)),
            ]

    .. group-tab:: Acceptance

        .. code-block:: python
            :emphasize-lines: 4
            :linenos:

            from datetime import date, timedelta
            from datatest import validate, accepted

            with accepted.tolerance(timedelta(days=2)):  # accepts ±2 days
                validate(date(2020, 12, 27), date(2020, 12, 25))


Failed Interval
---------------

.. tabs::

    .. group-tab:: Failure

        .. code-block:: python
            :linenos:

            from datetime import date
            from datatest import validate

            data = [
                date(2020, 11, 26),
                date(2020, 12, 11),
                date(2020, 12, 25),
                date(2021, 1, 4),
            ]

            validate.interval(data, min=date(2020, 12, 1), max=date(2020, 12, 31))


        .. code-block:: none
            :emphasize-lines: 6-7

            Traceback (most recent call last):
              File "example.py", line 11, in <module>
                validate.interval(data, min=date(2020, 12, 1), max=date(2020, 12, 31))
            datatest.ValidationError: elements `x` do not satisfy `date(2020, 12, 1, 0,
            0) <= x <= date(2020, 12, 31, 0, 0)` (2 differences): [
                Deviation(timedelta(days=-5), date(2020, 12, 1)),
                Deviation(timedelta(days=+4), date(2020, 12, 31)),
            ]

    .. group-tab:: Acceptance

        .. code-block:: python
            :emphasize-lines: 11
            :linenos:

            from datetime import date, timedelta
            from datatest import validate, accepted

            data = [
                date(2020, 11, 26),
                date(2020, 12, 11),
                date(2020, 12, 25),
                date(2021, 1, 4),
            ]

            with accepted.tolerance(timedelta(days=5)):  # accepts ±5 days
                validate.interval(data, min=date(2020, 12, 1), max=date(2020, 12, 31))


Failed Mapping Equalities
-------------------------

.. tabs::

    .. group-tab:: Failure

        .. code-block:: python
            :linenos:

            from datetime import datetime
            from datatest import validate

            remote_log = {
                'job165': datetime(2020, 11, 27, hour=3, minute=29, second=55),
                'job382': datetime(2020, 11, 27, hour=3, minute=36, second=33),
                'job592': datetime(2020, 11, 27, hour=3, minute=42, second=14),
                'job720': datetime(2020, 11, 27, hour=3, minute=50, second=7),
                'job826': datetime(2020, 11, 27, hour=3, minute=54, second=12),
            }

            master_log = {
                'job165': datetime(2020, 11, 27, hour=3, minute=28, second=1),
                'job382': datetime(2020, 11, 27, hour=3, minute=36, second=51),
                'job592': datetime(2020, 11, 27, hour=3, minute=40, second=18),
                'job720': datetime(2020, 11, 27, hour=3, minute=49, second=39),
                'job826': datetime(2020, 11, 27, hour=3, minute=55, second=20),
            }

            validate(remote_log, master_log)


        .. code-block:: none
            :emphasize-lines: 5-9

            Traceback (most recent call last):
              File "example.py", line 20, in <module>
                validate(remote_log, master_log)
            datatest.ValidationError: does not satisfy mapping requirements (5 differences): {
                'job165': Deviation(timedelta(seconds=+114), datetime(2020, 11, 27, 3, 28, 1)),
                'job382': Deviation(timedelta(seconds=-18), datetime(2020, 11, 27, 3, 36, 51)),
                'job592': Deviation(timedelta(seconds=+116), datetime(2020, 11, 27, 3, 40, 18)),
                'job720': Deviation(timedelta(seconds=+28), datetime(2020, 11, 27, 3, 49, 39)),
                'job826': Deviation(timedelta(seconds=-68), datetime(2020, 11, 27, 3, 55, 20)),
            }

    .. group-tab:: Acceptance

        .. code-block:: python
            :emphasize-lines: 20
            :linenos:

            from datetime import datetime, timedelta
            from datatest import validate, accepted

            remote_log = {
                'job165': datetime(2020, 11, 27, hour=3, minute=29, second=55),
                'job382': datetime(2020, 11, 27, hour=3, minute=36, second=33),
                'job592': datetime(2020, 11, 27, hour=3, minute=42, second=14),
                'job720': datetime(2020, 11, 27, hour=3, minute=50, second=7),
                'job826': datetime(2020, 11, 27, hour=3, minute=54, second=12),
            }

            master_log = {
                'job165': datetime(2020, 11, 27, hour=3, minute=28, second=1),
                'job382': datetime(2020, 11, 27, hour=3, minute=36, second=51),
                'job592': datetime(2020, 11, 27, hour=3, minute=40, second=18),
                'job720': datetime(2020, 11, 27, hour=3, minute=49, second=39),
                'job826': datetime(2020, 11, 27, hour=3, minute=55, second=20),
            }

            with accepted.tolerance(timedelta(seconds=120)):  # accepts ±120 seconds
                validate(remote_log, master_log)


.. note::

    The :class:`Deviation`'s repr (its printable representation) does some
    tricks with :py:mod:`datetime` objects to improve readability and help
    users understand their data errors. Compare the representations of the
    following datetime objects against their representations when included
    inside a Deviation:

    .. code-block:: python

        >>> from datetime import timedelta, date
        >>> from datatest import Deviation

        >>> timedelta(days=2)
        datetime.timedelta(days=2)

        >>> date(2020, 12, 25)
        datetime.date(2020, 12, 25)

        >>> Deviation(timedelta(days=2), date(2020, 12, 25))
        Deviation(timedelta(days=+2), date(2020, 12, 25))


    And below, we see a negative-value timedelta with a particularly
    surprising native repr. The Deviation repr modifies this to be more
    readable:

    .. code-block:: python

        >>> from datetime import timedelta, datetime
        >>> from datatest import Deviation

        >>> timedelta(seconds=-3)
        datetime.timedelta(days=-1, seconds=86397)

        >>> datetime(2020, 12, 25, 9, 30)
        datetime.datetime(2020, 12, 25, 9, 30)

        >>> Deviation(timedelta(seconds=-3), datetime(2020, 12, 25, 9, 30))
        Deviation(timedelta(seconds=-3), datetime(2020, 12, 25, 9, 30))


    While the timedelta reprs do differ, they *are* legitimate constructors
    for creating objects of equal value:

    .. code-block:: python

        >>> from datetime import timedelta

        >>> timedelta(days=+2) == timedelta(days=2)
        True

        >>> timedelta(seconds=-3) == timedelta(days=-1, seconds=86397)
        True
