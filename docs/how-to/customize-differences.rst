
.. currentmodule:: datatest

.. meta::
    :description: How to customize error differences.
    :keywords: datatest, difference, customize


############################
How to Customize Differences
############################

When using a helper function for validation, datatest's default
behavior is to produce :class:`Invalid` differences when the
function returns False. But you can customize this behavior
by returning a difference object instead of False. The returned
difference is used in place of an automatically generated one.

.. tabs::

    .. group-tab:: Custom Difference

        Below, the ``eauals100()`` function returns True if *value* equals
        ``100`` and it returns a :class:`Deviation` difference when *value*
        is different. The resulting ValidationError uses these differences
        instead of generating its own:

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate, Deviation

            data = [98, 99, 100, 100, 100, 103]

            def equals100(value):
                """Returns True or a difference object."""
                expected = 100
                if value != expected:
                    diff = value - expected
                    return Deviation(diff, expected)
                return True

            validate(data, equals100)

        .. code-block:: none
            :emphasize-lines: 5-7

            Traceback (most recent call last):
              File "example.py", line 13, in <module>
                validate(data, equals100)
            datatest.ValidationError: does not satisfy equals100() (3 differences): [
                Deviation(-2, 100),
                Deviation(-1, 100),
                Deviation(+3, 100),
            ]

    .. group-tab:: Default Behavior

        In this example, ``eauals100()`` returns True if *value* equals
        ``100`` and it returns False when *value* is different. The resulting
        ValidationError contains an :class:`Invalid` difference for each
        False result---this is the default behavior:

        .. code-block:: python

            from datatest import validate

            data = [98, 99, 100, 100, 100, 103]

            def equals100(value):
                """Returns True or False."""
                return value == 100

            validate(data, equals100)

        .. code-block:: none
            :emphasize-lines: 5-7

            Traceback (most recent call last):
              File "example.py", line 9, in <module>
                validate(data, equals100)
            datatest.ValidationError: does not satisfy equals100() (3 differences): [
                Invalid(98),
                Invalid(99),
                Invalid(103),
            ]
