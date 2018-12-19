
.. module:: datatest

.. meta::
    :description: How to assert fuzzy matches.
    :keywords: approximate string, fuzzy matching, testing, datatest


#############################
How to Validate Fuzzy Matches
#############################

When comparing strings of text, it can sometimes be useful to assert
that values are similar instead of asserting that they are exactly the
same. To do this, we define a function that takes our requirement
and returns a collection of objects that implement *approximate string
matching* (also called "fuzzy matching"):


.. code-block:: python

    import difflib
    import datatest


    def make_fuzzy(obj, cutoff=0.6):
        """Make values that match when string similarity is greater
        than or equal to *cutoff*.

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

        query = datatest.Query.from_object(obj)
        return query.map(predicate_factory)


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 15

            ...

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

                fuzzy_reference = make_fuzzy(catalog_reference)
                datatest.validate(scraped_data, fuzzy_reference)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 17

            ...

            class MyTests(datatest.DataTestCase):

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

                    fuzzy_reference = make_fuzzy(catalog_reference)
                    self.assertValid(scraped_data, fuzzy_reference)
