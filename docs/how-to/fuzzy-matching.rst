
.. module:: datatest

.. meta::
    :description: How to assert fuzzy matches.
    :keywords: approximate string, fuzzy matching, testing, datatest


###########################
How to Assert Fuzzy Matches
###########################

When comparing strings of text, it can sometimes be useful to assert
that values are similar instead of asserting that they are exactly the
same. To do this, we define an assertion that implements approximate
string matching (also called "fuzzy matching"):


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python

            import difflib
            from datatest import validate, Query


            def validate_fuzzy(data, requirement, cutoff=0.6, msg=None):
                """Assert that measures of string similarity are greater than
                or equal to *cutoff*.

                Similarity measures are determined using the ratio() method
                of the difflib.SequenceMatcher class. The values range from
                1.0 (exactly the same) to 0.0 (completely different).
                """
                class FuzzyString(str):
                    def __new__(cls, value):
                        if isinstance(value, str):
                            return super().__new__(cls, value)
                        return value

                    def __eq__(self, other):
                        if not isinstance(other, str):
                            return NotImplemented
                        matcher = difflib.SequenceMatcher(a=self, b=other)
                        return matcher.ratio() >= cutoff

                def predicate_factory(value):
                    if isinstance(value, tuple):
                        return tuple(FuzzyString(x) for x in obj)
                    return FuzzyString(value)

                query = Query.from_object(data)
                data = query.map(predicate_factory)

                __tracebackhide__ = True
                msg = msg or 'string similarity of {0} or higher'.format(cutoff)
                validate(data, requirement, msg)


            def test_matching():
                scraped_data = {
                    'MKT-GA4530': '4-1/2in Angle Grinder',
                    'FLK-87-5': 'Fluke 87-5 Multimeter',
                    'LEW-K2698-1': 'EM 180',  # <- This fails, too different.
                }
                catalog_reference = {
                    'MKT-GA4530': '4 1/2 inch Angle Grinder',
                    'FLK-87-5': 'Fluke 87 5 Multimeter',
                    'LEW-K2698-1': 'Lincoln Electric Easy MIG 180',
                }
                validate_fuzzy(scraped_data, catalog_reference)


    .. group-tab:: Unittest

        .. code-block:: python

            import difflib
            from datatest import DataTestCase, Query


            class MyTests(DataTestCase):

                def assertFuzzy(self, data, requirement, cutoff=0.6, msg=None):
                    """Assert that measures of string similarity are greater than
                    or equal to *cutoff*.

                    Similarity measures are determined using the ratio() method
                    of the difflib.SequenceMatcher class. The values range from
                    1.0 (exactly the same) to 0.0 (completely different).
                    """
                    class FuzzyString(str):
                        def __new__(cls2, value):
                            if isinstance(value, str):
                                return super().__new__(cls2, value)
                            return value

                        def __eq__(self2, other):
                            if not isinstance(other, str):
                                return NotImplemented
                            matcher = difflib.SequenceMatcher(a=self2, b=other)
                            return matcher.ratio() >= cutoff

                    def predicate_factory(value):
                        if isinstance(value, tuple):
                            return tuple(FuzzyString(x) for x in obj)
                        return FuzzyString(value)

                    query = Query.from_object(data)
                    data = query.map(predicate_factory)

                    msg = msg or 'string similarity of {0} or higher'.format(cutoff)
                    self.assertValid(data, requirement, msg)

                def test_matching(self):
                    scraped_data = {
                        'MKT-GA4530': '4-1/2in Angle Grinder',
                        'FLK-87-5': 'Fluke 87-5 Multimeter',
                        'LEW-K2698-1': 'EM 180',  # <- This fails, too different.
                    }
                    catalog_reference = {
                        'MKT-GA4530': '4 1/2 inch Angle Grinder',
                        'FLK-87-5': 'Fluke 87 5 Multimeter',
                        'LEW-K2698-1': 'Lincoln Electric Easy MIG 180',
                    }
                    self.assertFuzzy(scraped_data, catalog_reference)

