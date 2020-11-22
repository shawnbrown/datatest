
.. currentmodule:: datatest

.. meta::
    :description: How to validate date formats.
    :keywords: datatest, date format, validate, validation


##############################
How to Validate Addresses (US)
##############################


===========================
CASS Certified Verification
===========================

Unfortunately, the only "real" way to validate addresses is to use
a verification service or program. Simple validation checks cannot
guarantee that an address is correct or deliverable. In the United
States, proper address verification requires the use of `CASS certified`_
software. Several online services offer proper address verification
but to use one you must write code to interact with a service's API.
Implementing such a solution is beyond the scope of this document.

.. _`CASS certified`: https://postalpro.usps.com/certifications/cass


====================
Heuristic Evaluation
====================

Sometimes the benefits of comprehensive address verification are not
enough to justify the work required to interface with a third-party
service or the possible cost of a subscription fee. Simple checks for
well-formedness and set membership can catch many obvious errors and
omissions. If this weaker form of verification is useful for your
situation, the following examples could be helpful.


Example Data
------------

The validation examples below are designed to check address data
like the following:

    ============================  =============  =====  ==========
    street                        city           state  zipcode
    ============================  =============  =====  ==========
    1600 Pennsylvania Avenue NW   Washington     DC     20500
    30 Rockefeller Plaza          New York       NY     10112
    350 Fifth Avenue, 34th Floor  New York       NY     10118-3299
    1060 W Addison St             Chicago        IL     60613
    15 Central Park W Apt 7P      New York       NY     10023-7711
    11 Wall St                    New York       NY     10005
    2400 Fulton St                San Francisco  CA     94118-4107
    351 Farmington Ave            Hartford       CT     06105-6400
    ============================  =============  =====  ==========


Street Address
--------------

Street addresses are difficult to validate with a simple check. The US
Postal Service publishes addressing standards designed to account for
a majority of address styles (see `delivery address line`_). But these
standards do not account for all situations.

You could build a function to check that "street" values contain
`commonly used suffixes`_, but such a test could give misleading results
when checking hyphenated address ranges, grid-style addresses, and rural
routes. If you are not using a third-party verification service, it may
be best to simply check that the field is not empty.

.. _`delivery address line`: https://pe.usps.com/text/pub28/28c2_012.htm
.. _`commonly used suffixes`: https://pe.usps.com/text/pub28/28apc_002.htm

The example below uses a regular expression, ``\w+``, to match one or
more letters or numbers:

.. code-block:: python

    from datatest import validate
    ...

    validate.regex(df['street'], r'\w+')


City Name
---------

The US Postal Service sells a regularly updated *City State Product*
file. For paying customers who purchase the USPS file or for users of
third-party services, "city" values can be matched against a controlled
vocabulary of approved city names. As with street validation, when such
resources are unavailable it's probably best to check that the field is
not empty.

The example below uses a regular expression, ``[A-Za-z]+``, to match one
or more letters:

.. code-block:: python

    from datatest import validate
    ...

    validate.regex(df['city'], r'[A-Za-z]+')


State Abbreviation
------------------

Unlike the previous fields, the set of possible state abbreviations is small
and easy to check against. The set includes codes for all 50 states, the
District of Columbia, US territories, associate states, and armed forces
delivery codes.

In this example, we use :func:`validate.subset` to check that the values in
the "state" column are members of the ``state_codes`` set:

.. code-block:: python

    from datatest import validate
    ...

    state_codes = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'AS', 'GU', 'MP', 'PR', 'VI', 'FM', 'MH', 'PW',
        'AA', 'AE', 'AP',
    }
    validate.subset(df['state'], state_codes)


ZIP Code
--------

The set of valid ZIP Codes is very large but they can be easily checked for
well-formedness. Basic ZIP Codes are five digits and extended ZIP+4 Codes are
nine digits (e.g., 20500 and 20500-0005).

This example uses a regex, ``^\d{5}(-\d{4})?$``, to match the two possible
formats:

.. code-block:: python

    from datatest import validate
    ...

    validate.regex(df['zipcode'], r'^\d{5}(-\d{4})?$')


State and ZIP Code Consistency
------------------------------

ZIP Code digits are associated with specific states and regions. For example,
all ZIP Codes in Indiana begin with "4" (46350, 46247, etc.) and all ZIP Codes
in Pennsylvania begin with "1" (15501, 16512, etc.). We can use these known
associations as a sanity check to make sure that our "state" and "zipcode"
values are plausible and consistent.

The following example defines a helper function, ``state_zip_consistency()``,
to check the first digit of a ZIP Code against a set of associated state
codes:

.. code-block:: python

    from datatest import validate
    ...

    def state_zip_consistency(state_zipcode):
        """ZIP Code should be consistent with state."""
        lookup = {
            '0': {'CT', 'MA', 'ME', 'NH', 'NJ', 'NY', 'PR', 'RI', 'VT', 'VI', 'AE'},
            '1': {'DE', 'NY', 'PA'},
            '2': {'DC', 'MD', 'NC', 'SC', 'VA', 'WV'},
            '3': {'AL', 'FL', 'GA', 'MS', 'TN', 'AA'},
            '4': {'IN', 'KY', 'MI', 'OH'},
            '5': {'IA', 'MN', 'MT', 'ND', 'SD', 'WI'},
            '6': {'IL', 'KS', 'MO', 'NE'},
            '7': {'AR', 'LA', 'OK', 'TX'},
            '8': {'AZ', 'CO', 'ID', 'NM', 'NV', 'UT', 'WY'},
            '9': {'AK', 'AS', 'CA', 'GU', 'HI', 'MH', 'FM', 'MP', 'OR', 'PW', 'WA', 'AP'},
        }
        state, zipcode = state_zipcode
        first_digit = zipcode[0]
        return state in lookup[first_digit]

    validate(df[['state', 'zipcode']], state_zip_consistency)

This check works well to detect data processing errors that might mis-align or
otherwise damage "zipcode" and "city" values. But it cannot detect if ZIP Codes
are assigned to the wrong states within in the same number-group---for example,
it wouldn't be able to determine if a Kentucky ZIP Code was used on an Indiana
address (since both Kentucky and Indiana have ZIP Codes beginning with "4").
