
.. py:currentmodule:: datatest

.. meta::
    :description: How to assert telephone number formats.
    :keywords: datatest, phone format, validate phone number


#############################
How to Validate Phone Numbers
#############################

To check that phone numbers are well-formed, you can use a regular
expression.


USA and Canada
==============


.. code-block:: python

    from datatest import validate

    pattern = r'^\(\d{3}\)[ ]\d{3}-\d{4}$'

    data = [
        '(914) 232-9901',
        '(914) 737-9938',
        '(213) 888-7636',
        '(202) 965-2900',
        '(858) 651-5050',
    ]

    validate.regex(data, pattern, msg='must use phone number format')


For other common US and Canadian formats, you can use the regex
patterns:

.. table::
    :widths: auto

    +-------------------------------+-------------------+
    | pattern                       | examples          |
    +===============================+===================+
    | ``^\(\d{3}\)[ ]\d{3}-\d{4}$`` | \(914) 232-9901   |
    +-------------------------------+-------------------+
    | ``^\d{3}-\d{3}-\d{4}$``       | 914-232-9901      |
    +-------------------------------+-------------------+
    | ``^\+?1-\d{3}-\d{3}-\d{4}$``  | 1-914-232-9901    |
    |                               +-------------------+
    |                               | +1-914-232-9901   |
    +-------------------------------+-------------------+


..
    THESE PHONE NUMBER PATTERNS ARE INCOMPLETE

    China
    =====

    .. code-block:: python

        from datatest import validate

        pattern = r'^\d{3}[ ]\d{3,4}[ ]\d{4}$'

        data = [
            '074 7284 5586',
            '400 669 5539',
        ]

        validate.regex(data, pattern, msg='must use phone number format')


    For common variants, you can use the following patterns:

    .. table::
        :widths: auto

        +--------------------------------------+-------------------+
        | ``^\d{3}[ ]\d{3,4}[ ]\d{4}$``        | 074 7284 5586     |
        |                                      +-------------------+
        |                                      | 400 669 5539      |
        +--------------------------------------+-------------------+
        | ``^\+86[ ]\d{3}[ ]\d{3,4}[ ]\d{4}$`` | +86 074 7284 5586 |
        |                                      +-------------------+
        |                                      | +86 400 669 5539  |
        +--------------------------------------+-------------------+


India
=====

.. code-block:: python

    import re
    from datatest import validate


    indian_phone_format = re.compile(r'''^
        (\+91[ ])?   # Optional international code.
        (\(0\))?     # Optional trunk prefix.
        # 10 digit codes with area & number splits.
        (
            \d{10}           # xxxxxxxxxx
            | \d{5}[ ]\d{5}  # xxxxx xxxxx
            | \d{4}[ ]\d{6}  # xxxx xxxxxx
            | \d{3}[ ]\d{7}  # xxx xxxxxxx
            | \d{2}[ ]\d{8}  # xx xxxxxxxx
        )
    $''', re.VERBOSE)

    data = [
        '+91 (0)99999 99999',
        '+91 99999 99999',
        '9999999999',
        '99999 99999',
        '9999 999999',
        '999 9999999',
        '99 99999999',
    ]

    validate(data, indian_phone_format, msg='must use phone number format')


United Kingdom
==============

.. code-block:: python

    import re
    from datatest import validate


    uk_phone_format = re.compile(r'''^(
        # 10 digit NSNs (leading zero doesn't count)
        \(01\d{2}[ ]\d{2}\d\)[ ]\d{2}[ ]\d{3} # (01xx xx) xx xxx
        | \(01\d{3}\)[ ]\d{3}[ ]\d{3}         # (01xxx) xxx xxx
        | \(01\d{2}\)[ ]\d{3}[ ]\d{4}         # (01xx) xxx xxxx
        | \(02\d\)[ ]\d{4}[ ]\d{4}            # (02x) xxxx xxxx
        | 0\d{3}[ ]\d{3}[ ]\d{4}              # 0xxx xxx xxxx
        | 0\d{2}[ ]\d{4}[ ]\d{4}              # 0xx xxxx xxxx
        | 07\d{3}[ ]\d{3}[ ]\d{3}             # 07xxx xxx xxx

        # 9 digit NSNs
        | \(0169[ ]77\)[ ]\d{4}               # (0169 77) xxxx
        | \(01\d{3}\)[ ]\d{2}[ ]\d{3}         # (01xxx) xx xxx
        | 0500[ ]\d{3}[ ]\d{3}                # 0500 xxx xxx
        | 0800[ ]\d{3}[ ]\d{3}                # 0800 xxx xxx
    )$''', re.VERBOSE)

    data = [
        '(01257) 421 282',
        '(01736) 759 307',
        '(0169 77) 3452',
        '0116 319 5885',
        '0191 384 6777',
        '020 8399 0617',
    ]

    validate(data, uk_phone_format, msg='must use phone number format')


..
    TO ADD:
      Germany
      Japan
      France

