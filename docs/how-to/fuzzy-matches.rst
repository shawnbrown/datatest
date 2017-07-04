
.. module:: datatest

.. meta::
    :description: How to assert set relations.
    :keywords: datatest, reference data


###########################
How to Assert Fuzzy Matches
###########################

When comparing strings of text, it may be necessary to assert that
values are similar even though they are not exactly the same. To do
this, we define an assertion that implements approximate string
matching (also called fuzzy matching):


.. code-block:: python

    import datatest


    class FuzzyTestCase(datatest.DataTestCase):
        @staticmethod
        def _edit_distance(a, b):         # Edit distance, also called
            maxlen = max(len(a), len(b))  # Levenshtein distance, is a
            n, m = len(a), len(b)         # common measure of similarity
            if n > m:                     # for comparing text values.
                a, b = b, a
                n, m = m, n
            current = range(n + 1)
            for i in range(1, m + 1):
                previous, current = current, [i] + [0] * n
                for j in range(1, n + 1):
                    add, delete = previous[j] + 1, current[j - 1] + 1
                    change = previous[j - 1]
                    if a[j - 1] != b[i - 1]:
                        change = change + 1
                    current[j] = min(add, delete, change)
            distance = current[n]
            return distance

        def assertFuzzy(self, data, requirement, tolerance, msg=None):
            """Assert that edit distance of two strings is less than or
            equal to percent *tolerance*.
            """
            class PercentFuzzy(str):
                def __eq__(inner_self, other):
                    if not isinstance(other, str):
                        return NotImplemented
                    distance = self._edit_distance(inner_self, other)
                    percent = distance / max(len(inner_self), len(other))
                    return tolerance >= percent  # <- closes over tolerance

            func = lambda x: PercentFuzzy(x) if isinstance(x, str) else x
            requirement = datatest.DataQuery.from_object(requirement).map(func)

            msg = msg or 'percent difference of {0} or less'.format(tolerance)
            self.assertValid(data, requirement, msg)

    ...


This works by calculating a measure of similarity and asserting that
this measure is equal to or less than a given tolerance:

.. code-block:: python

    ...

    class TestFuzzy(FuzzyTestCase):
        def test_assertion(self):
            scraped_data = {
                'MKT-GA4530': '4 1/2 inch Angle Grinder',
                'FLK-87-5': 'Fluke 87 5 Multimeter',
                'LEW-K2698-1': 'Lincoln Elec Easy MIG 180',
            }
            catalog_reference = {
                'MKT-GA4530': '4-1/2in Angle Grinder',
                'FLK-87-5': 'Fluke 87-5 Multimeter',
                'LEW-K2698-1': 'Lincoln Easy MIG 180',
            }
            self.assertFuzzy(scraped_data, catalog_reference, 0.25)


    if __name__ == '__main__':
        datatest.main()


.. note::

    The assertFuzzy() method in the above example creates a subclass
    of :py:class:`str` that overrides ``__eq__()``---the comparison
    method for equality.

    We could have created a helper-function that retrieves values
    from required_dict and performs a fuzzy match directly. But our
    implementation would grow increasingly complex if we wanted to
    cleanly handle dictionaries with extra or missing keys. By creating
    a subclass and overriding the equality comparison, we let
    ``assertValid()`` handle the matching and error reporting
    details for us.
