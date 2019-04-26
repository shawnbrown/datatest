
.. module:: datatest

.. meta::
    :description: How to assert fuzzy matches.
    :keywords: approximate string, fuzzy matching, testing, datatest


#############################
How to Validate Fuzzy Matches
#############################

When comparing strings of text, it can sometimes be useful
to check that values are similar instead of asserting that
they are exactly the same. Datatest provides options for
*approximate string matching* (also called "fuzzy
matching").

When checking mappings or sequences of values, you can allow
approximate matches with the :meth:`allowed.fuzzy` acceptance:

.. code-block:: python
    :emphasize-lines: 7

    from datatest import validate, allowed

    data = {'A': 'aax', 'B': 'bbx'}

    requirement = {'A': 'aaa', 'B': 'bbb'}

    with allowed.fuzzy(cutoff=0.6):
        validate(data, requirement)

If variation is an inherent, natural feature of the data and
does not necessarily represent a defect, it may be appropriate
to use :meth:`validate.fuzzy` instead of the acceptance shown
previously:

.. code-block:: python
    :emphasize-lines: 7

    from datatest import validate

    data = {'A': 'aax', 'B': 'bbx'}

    requirement = {'A': 'aaa', 'B': 'bbb'}

    validate.fuzzy(data, requirement, cutoff=0.6)
