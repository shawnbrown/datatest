
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


Default Behavior
================

In the following example, the helper function checks that text
values are upper case and have no extra whitespace. If the values
are good, the function returns ``True``, if the values are bad it
returns ``False``:

.. code-block:: python
    :linenos:
    :emphasize-lines: 6

    from datatest import validate


    def wellformed(x):  # <- Helper function.
        """Must be upercase and no extra whitespace."""
        return x == ' '.join(x.split()) and x.isupper()

    data = [
        'CAPE GIRARDEAU',
        'GREENE ',
        'JACKSON',
        'St. Louis',
    ]

    validate(data, wellformed)


Each time the helper function returns ``False``, an :class:`Invalid`
difference is created:

.. code-block:: none
    :emphasize-lines: 5-6

    Traceback (most recent call last):
      File "example.py", line 15, in <module>
        validate(data, wellformed)
    ValidationError: Must be upercase and no extra whitespace. (2 differences): [
        Invalid('GREENE '),
        Invalid('St. Louis'),
    ]


Custom Differences
==================

In this example, the helper function returns a custom ``BadWhitespace``
or ``NotUpperCase`` difference for each bad value:

.. code-block:: python
    :linenos:
    :emphasize-lines: 15,17

    from datatest import validate, Invalid


    class BadWhitespace(Invalid):
        """For strings with leading, trailing, or irregular whitespace."""


    class NotUpperCase(Invalid):
        """For strings that aren't upper case."""


    def wellformed(x):  # <- Helper function.
        """Must be upercase and no extra whitespace."""
        if x != ' '.join(x.split()):
            return BadWhitespace(x)
        if not x.isupper():
            return NotUpperCase(x)
        return True


    data = [
        'CAPE GIRARDEAU',
        'GREENE ',
        'JACKSON',
        'St. Louis',
    ]

    validate(data, wellformed)


These differences are use in the ValidationError:

.. code-block:: none
    :emphasize-lines: 5-6

    Traceback (most recent call last):
      File "example.py", line 15, in <module>
        validate(data, wellformed)
    ValidationError: Must be upercase and no extra whitespace. (2 differences): [
        BadWhitespace('GREENE '),
        NotUpperCase('St. Louis'),
    ]


.. caution::

    Typically, you should try to **stick with existing differences**
    in your data tests. Only create a custom subclass when its meaning
    is evident and doing so helps your data preparation workflow.

    Don't add a custom class when it doesn't benefit your testing
    process. At best, you're doing extra work for no added benefit.
    And at worst, an ambiguous or needlessly complex subclass can
    cause more problems than it solves.

    If you need to resolve ambiguity in a validation, you can split
    the check into multiple calls. Below, we perform the same check
    demonstrated earlier using two :func:`validate` calls:

    .. code-block:: python
        :linenos:
        :emphasize-lines: 14,21

        from datatest import validate

        data = [
            'CAPE GIRARDEAU',
            'GREENE ',
            'JACKSON',
            'St. Louis',
        ]

        def no_irregular_whitespace(x):  # <- Helper function.
            """Must have no irregular whitespace."""
            return x == ' '.join(x.split())

        validate(data, no_irregular_whitespace)


        def is_upper_case(x):  # <- Helper function.
            """Must be upper case."""
            return x.isupper()

        validate(data, is_upper_case)


..
    # In the future, after adding a comparator interface to validate(),
    # possibly change the example to something like the following.

    from enum import Enum
    from datatest import validate, Invalid


    # Likert Scale
    class response(Enum):
        STRONGLY_OPPOSE = 1
        OPPOSE = 2
        NEUTRAL = 3
        SUPPORT = 4
        STRONGLY_SUPPORT = 5


    # 7-Point Likert Scale
    #class response(Enum):
    #    STRONGLY_OPPOSE = 1
    #    OPPOSE = 2
    #    SOMEWHAT_OPPOSE = 3
    #    NEUTRAL = 4
    #    SOMEWHAT_SUPPORT = 5
    #    SUPPORT = 6
    #    STRONGLY_SUPPORT = 7


    class Change(Invalid):
        """For differences of 1 point."""


    class LargeChange(Invalid):
        """For differences of 2 or more points."""


    latest_survey = {
        'a': response.SUPPORT,
        'b': response.STRONGLY_OPPOSE,
        'c': response.STRONGLY_SUPPORT,
        'd': response.OPPOSE,
    }

    previous_survey = {
        'a': response.SUPPORT,
        'b': response.OPPOSE,
        'c': response.STRONGLY_SUPPORT,
        'd': response.SUPPORT,
    }

    validate(latest_survey, previous_survey)

