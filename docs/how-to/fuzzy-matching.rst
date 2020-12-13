
.. currentmodule:: datatest

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

When checking mappings or sequences of values, you can accept
approximate matches with the :meth:`accepted.fuzzy` acceptance:

.. tabs::

    .. group-tab:: Using Acceptance

        .. code-block:: python
            :emphasize-lines: 19
            :linenos:

            from datatest import validate, accepted

            linked_record = {
                'id165': 'Saint Louis',
                'id382': 'Raliegh',
                'id592': 'Austin',
                'id720': 'Cincinatti',
                'id826': 'Philadelphia',
            }

            master_record = {
                'id165': 'St. Louis',
                'id382': 'Raleigh',
                'id592': 'Austin',
                'id720': 'Cincinnati',
                'id826': 'Philadelphia',
            }

            with accepted.fuzzy(cutoff=0.6):
                validate(linked_record, master_record)

    .. group-tab:: No Acceptance

        .. code-block:: python
            :linenos:

            from datatest import validate

            linked_record = {
                'id165': 'Saint Louis',
                'id382': 'Raliegh',
                'id592': 'Austin',
                'id720': 'Cincinatti',
                'id826': 'Philadelphia',
            }

            master_record = {
                'id165': 'St. Louis',
                'id382': 'Raleigh',
                'id592': 'Austin',
                'id720': 'Cincinnati',
                'id826': 'Philadelphia',
            }

            validate(linked_record, master_record)


        .. code-block:: none
            :emphasize-lines: 5-7

            Traceback (most recent call last):
              File "example.py", line 19, in <module>
                validate(linked_record, master_record)
            datatest.ValidationError: does not satisfy mapping requirements (3 differences): {
                'id165': Invalid('Saint Louis', expected='St. Louis'),
                'id382': Invalid('Raliegh', expected='Raleigh'),
                'id720': Invalid('Cincinatti', expected='Cincinnati'),
            }


If variation is an inherent, natural feature of the data and
does not necessarily represent a defect, it may be appropriate
to use :meth:`validate.fuzzy` instead of the acceptance shown
previously:

.. code-block:: python
    :emphasize-lines: 19
    :linenos:

    from datatest import validate

    linked_record = {
        'id165': 'Saint Louis',
        'id382': 'Raliegh',
        'id592': 'Austin',
        'id720': 'Cincinatti',
        'id826': 'Philadelphia',
    }

    master_record = {
        'id165': 'St. Louis',
        'id382': 'Raleigh',
        'id592': 'Austin',
        'id720': 'Cincinnati',
        'id826': 'Philadelphia',
    }

    validate.fuzzy(linked_record, master_record, cutoff=0.6)


That said, it's probably more appropriate to use an acceptance
for this specific example.

