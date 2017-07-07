
.. module:: datatest

.. meta::
    :description: How to assert fuzzy matches.
    :keywords: testing, fuzzy match, datatest


###########################
How to Assert Fuzzy Matches
###########################

When comparing strings of text, it can sometimes be useful to assert
that values are similar instead of asserting that they are exactly the
same. To do this, we define an assertion that implements approximate
string matching (also called fuzzy matching):

.. code-block:: python

    import difflib
    import datatest


    class FuzzyTestCase(datatest.DataTestCase):
        def assertFuzzy(self, data, requirement, cutoff=0.6, msg=None):
            """Assert that measures of string similarity are greater than
            or equal to *cutoff*.

            Similarity measures are determined using the ratio() method
            of the difflib.SequenceMatcher class. The values range from
            1.0 (exactly the same) to 0.0 (completely different).
            """
            class FuzzyMatcher(str):
                def __eq__(inner_self, other):
                    if not isinstance(other, str):
                        return NotImplemented
                    matcher = difflib.SequenceMatcher(a=inner_self, b=other)
                    return matcher.ratio() >= cutoff  # <- closes over cutoff

            func = lambda x: FuzzyMatcher(x) if isinstance(x, str) else x
            requirement = datatest.DataQuery.from_object(requirement).map(func)

            msg = msg or 'string similarity of {0} or higher'.format(cutoff)
            self.assertValid(data, requirement, msg)
    ...


Tests that inherit from ``FuzzyTestCase``, can use the ``assertFuzzy()``
method to check for approximate string matches:

.. code-block:: python
    :emphasize-lines: 15

    ...

    class TestFuzzy(FuzzyTestCase):
        def test_assertion(self):
            scraped_data = {
                'MKT-GA4530': '4 1/2 inch Angle Grinder',
                'FLK-87-5': 'Fluke 87 5 Multimeter',
                'LEW-K2698-1': 'Lincoln Electric Easy MIG 180',
            }
            catalog_reference = {
                'MKT-GA4530': '4-1/2in Angle Grinder',
                'FLK-87-5': 'Fluke 87-5 Multimeter',
                'LEW-K2698-1': 'Lincoln Easy MIG 180',
            }
            self.assertFuzzy(scraped_data, catalog_reference, 0.75)


    if __name__ == '__main__':
        datatest.main()


**************************
Allowing Fuzzy Differences
**************************

While it's usually more efficient to assert approximate matches and
allow specific differences, it may be appropriate to allow approximate
differences in certain cases. To do this, we can extend ``FuzzyTestCase``
from the previous example by defining an allowance:

.. code-block:: python

    class FuzzyTestCase(datatest.DataTestCase):
        ...

        def allowedFuzzy(self, cutoff=0.6, msg=None):
            """Allows Invalid differences whose measures of similarity are
            greater than or equal to *cutoff*.

            Similarity measures are determined using the ratio() method
            of the difflib.SequenceMatcher class. The values range from
            1.0 (exactly the same) to 0.0 (completely different).
            """
            def approx_diff(invalid, expected):
                matcher = difflib.SequenceMatcher(a=expected, b=invalid)
                return matcher.ratio() >= cutoff  # <- closes over cutoff
            msg = msg or 'string similarity of {0} or higher'.format(cutoff)
            return self.allowedInvalid() & self.allowedArgs(approx_diff, msg)
