
.. module:: datatest

.. meta::
    :description: How to compare data between two files.
    :keywords: compare files, reference data, datatest


.. _comparing-files:

##########################################
Using Reference Data (Comparing Two Files)
##########################################

This tutorial demonstrates how to compare a detailed file
of individual records against a summary file of aggregate
records.

For this example, we have a file of Australian population
counts by country of birth:

    +-----------------+------------------+------------+
    | state/territory | country_of_birth | population |
    +=================+==================+============+
    | Australian      | Australia        | 270,033    |
    | Capital         |                  |            |
    | Territory       |                  |            |
    +-----------------+------------------+------------+
    | Australian      | China            | 11,351     |
    | Capital         |                  |            |
    | Territory       |                  |            |
    +-----------------+------------------+------------+
    | Australian      | England          | 12,757     |
    | Capital         |                  |            |
    | Territory       |                  |            |
    +-----------------+------------------+------------+
    | ...             | ...              | ...        |
    +-----------------+------------------+------------+

We want to check that the data in our file is correct before
we use it for analysis.

To do this, we're going to validate our data using a reference
file of estimated totals for each Australian state or territory:

    +-----------------+------------+
    | state/territory | population |
    +=================+============+
    | Australian      | 389,785    |
    | Capital         |            |
    | Territory       |            |
    +-----------------+------------+
    | Jervis Bay      | 388        |
    | Territory       |            |
    +-----------------+------------+
    | New South Wales | 7,507,350  |
    +-----------------+------------+
    | ...             | ...        |
    +-----------------+------------+


.. tip::

    It's important to use reference data that comes from somewhere other
    than the data file we want to test. **The more independent the source,
    the more confident we can be in our conclusions.** Ideally, we want
    to use high-quality reference data from an independent organization
    run by an independent group of people---but in many cases, such ideal
    conditions are rare. Regardless of the situation, it helps to maximize
    the independence of our reference data as much as we can in the given
    circumstances.

    In this example, our detailed records are *Australian Census counts*
    and our summary records are *projected population estimates* based on
    an earlier census. While these datasets are both produced by the same
    organization (the Australian Bureau of  Statistics), they were produced
    at **different times** and made using **different methods**.


*******************
Using this Tutorial
*******************

To follow along and perform these steps yourself, download both of
the following data files and one of the tests scripts:

* **Detailed File:** :download:`country_of_birth.csv </_static/tutorial/country_of_birth.csv>`
* **Summary File:** :download:`estimated_totals.csv </_static/tutorial/estimated_totals.csv>`
* **Test Script (download one):**
    * :download:`test_country_of_birth.py </_static/tutorial/test_country_of_birth.py>` (for Pytest)
    * :download:`test_country_of_birth_unit.py </_static/tutorial/test_country_of_birth_unit.py>` (for Unittest)

To run the tests, use the following command:

.. tabs::

    .. code-tab:: none Pytest

        pytest test_country_of_birth.py

    .. code-tab:: none Unittest

        python -m datatest test_country_of_birth_unit.py


************************
Step-by-Step Explanation
************************


0. Fixtures
===========

For this example, the script defines two fixtures (one :class:`Selector`
for each CSV file):

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_country_of_birth.py
            :pyobject: detail
            :lineno-match:

        .. literalinclude:: /_static/tutorial/test_country_of_birth.py
            :pyobject: summary
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_country_of_birth_unit.py
            :pyobject: setUpModule
            :lineno-match:


1. Field Names
==============

To check the column names of our file, we will compare the
:attr:`fieldnames <Selector.fieldnames>` property of our
detailed file against a :py:class:`set` of :attr:`fieldnames
<Selector.fieldnames>` from the summary file:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_country_of_birth.py
            :pyobject: test_columns
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_columns
            :lineno-match:


    .. note::

        The test above is marked as ``mandatory`` because later tests
        cannot pass unless the data contains the expected fieldnames.
        When a mandatory test fails, the test session ends early.


Running our test script for the first time gives us the following
message:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 12-14

            _________________________________ test_columns _________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                @pytest.mark.mandatory
                def test_columns(detail, summary):
                    required_set = set(summary.fieldnames)

            >       validate(detail.fieldnames, required_set)
            E       ValidationError: does not satisfy set membership (3 differences): [
                        Extra('country_of_birth'),
                        Extra('pop'),
                        Missing('population'),
                    ]

            test_country_of_birth.py:30: ValidationError


    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8-10

            ======================================================================
            FAIL: test_columns (test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 29, in test_columns
                self.assertValid(detail.fieldnames, required_set)
            ValidationError: mandatory test failed, stopping early: does not satisfy set membership (3 differences): [
                Extra('country_of_birth'),
                Extra('pop'),
                Missing('population'),
            ]

    The error above indicates that our detailed file is missing the
    column "``population``" and includes some other extra columns.


Opening **country_of_birth.csv** (our detailed file), we can see
that the column "``pop``" is obviously the population column:

.. literalinclude:: /_static/tutorial/country_of_birth.csv
    :language: none
    :lineno-match:
    :lines: 1-4
    :emphasize-lines: 1


We fix this by replacing "``pop``" with "``population``" and saving
our changes.


Now when we run our tests, we get the following message:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 12

            _________________________________ test_columns _________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                @pytest.mark.mandatory
                def test_columns(detail, summary):
                    required_set = set(summary.fieldnames)

            >       validate(detail.fieldnames, required_set)
            E       ValidationError: does not satisfy set membership (2 differences): [
                        Extra('country_of_birth'),
                    ]

            test_country_of_birth.py:30: ValidationError


    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8

            ======================================================================
            FAIL: test_columns (test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 29, in test_columns
                self.assertValid(detail.fieldnames, required_set)
            ValidationError: mandatory test failed, stopping early: does not satisfy set membership (1 difference): [
                Extra('country_of_birth'),
            ]

    The "``country_of_birth``" column is listed as extra but, in this
    case, the difference is valid---a detailed file *should* contain
    more columns than a summary file.


To handle this, we add an "allowance" so the extra column won't trigger
a test failure:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth.py
            :pyobject: test_columns
            :lineno-match:
            :emphasize-lines: 5

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_columns
            :lineno-match:
            :emphasize-lines: 5


2. State/Territory Values
=========================

Now that the column names have been fixed, we can start
to validate the content of  these columns. Below, we check
that the :py:class:`set` of "``states/territories``" values
in our detailed file match the values in the summary file:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_country_of_birth.py
            :pyobject: test_states
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_states
            :lineno-match:



Running our script now gives the folowing message:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 12

            _________________________________ test_states __________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                def test_states(detail, summary):
                    data = detail({'state/territory'})
                    requirement = summary({'state/territory'})

            >       validate(data, requirement)
            E       ValidationError: does not satisfy set membership (1 difference): [
                        Missing('Jervis Bay Territory'),
                    ]

            test_country_of_birth.py:38: ValidationError

    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8

            ======================================================================
            FAIL: test_states (modified_test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 36, in test_states
                self.assertValid(data, requirement)
            ValidationError: does not satisfy set membership (1 difference): [
                Missing('Jervis Bay Territory'),
            ]


    Above, we can see that our detailed file is missing
    "``Jervis Bay Territory``". Jervis Bay Territory is a very
    small terrirory in Australia containing only a few hundred
    residents (391 in the 2016 census). It is often counted as part
    of the Australian Capital Territory for various administrative
    purposes.


Since Jervis Bay Territory has such a small population, we are
going to allow this omission with the following change:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth.py
            :pyobject: test_states
            :lineno-match:
            :emphasize-lines: 5-7,9

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_states
            :lineno-match:
            :emphasize-lines: 5-7,9


3. Population Sums
==================

To check the totals, we sum the population values by state for
each of our data sources. We validate the data by comparing
results from our detailed file against results from the summary
file:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_country_of_birth.py
            :pyobject: test_population
            :lineno-start: 46

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_population
            :lineno-start: 46


Running this test gives the following message:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 12-20

            _______________________________ test_population ________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                def test_population(detail, summary):
                    data = detail({'state/territory': 'population'}).sum()
                    requirement = summary({'state/territory': 'population'}).sum()

            >       validate(data, requirement)
            E       ValidationError: does not satisfy mapping requirement (9 differences): {
                        'Australian Capital Territory': Deviation(+7612, 389785),
                        'Jervis Bay Territory': Deviation(-388, 388),
                        'New South Wales': Deviation(-27122, 7507350),
                        'Northern Territory': Deviation(+2421, 226412),
                        'Queensland': Deviation(-18310, 4721503),
                        'South Australia': Deviation(+39328, 1637325),
                        'Tasmania': Deviation(+505685, 514245),
                        'Victoria': Deviation(+77294, 5849330),
                        ...
            E
            E       ...Full output truncated, use '-vv' to show

            test_country_of_birth.py:50: ValidationError

    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8-16

            ======================================================================
            FAIL: test_population (modified_test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 47, in test_population
                self.assertValid(data, requirement)
            ValidationError: does not satisfy mapping requirement (9 differences): {
                'Australian Capital Territory': Deviation(+7612, 389785),
                'Jervis Bay Territory': Deviation(-388, 388),
                'New South Wales': Deviation(-27122, 7507350),
                'Northern Territory': Deviation(+2421, 226412),
                'Queensland': Deviation(-18310, 4721503),
                'South Australia': Deviation(+39328, 1637325),
                'Tasmania': Deviation(+505685, 514245),
                'Victoria': Deviation(+77294, 5849330),
                'Western Australia': Deviation(+23030, 2451380),
            }

    Above, we see the deviations between the values in our detailed
    file and values in the summary file. Because these two files were
    created using different processes, we don't expect the values to
    be the same but we do expect the values to be close---and most of
    them are.


Although the report look messy at first, the percent error for most
of these deviations is quite small. As an example, in Victoria, the
population from our detailed file is 77,297 counts higher than the
population in the summary file. But our expected population is over
5.8 million so the percent error is only +1.3%.

Since we're comparing detailed *counts* against summary *estimates*,
a small percent error is entirely acceptable. To relect this decision
in our tests, we will allow a percent error of ±3%:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :lineno-start: 46
            :emphasize-lines: 5

            def test_population(detail, summary):
                data = detail({'state/territory': 'population'}).sum()
                requirement = summary({'state/territory': 'population'}).sum()

                with allowed.percent(0.03):  # <- Allow +/- 3%
                    validate(data, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :lineno-start: 43
            :emphasize-lines: 5

            def test_population(self):
                data = detail({'state/territory': 'population'}).sum()
                requirement = summary({'state/territory': 'population'}).sum()

                with self.allowedPercent(0.03):  # <- Allow +/- 3%
                    self.assertValid(data, requirement)


Rerunning our script with this new allowance gives the following message:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 13-14

            _______________________________ test_population ________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                def test_population(detail, summary):
                    data = detail({'state/territory': 'population'}).sum()
                    requirement = summary({'state/territory': 'population'}).sum()

                    with allowed.percent(0.03):  # <- Allow +/- 3%
            >           validate(data, requirement)
            E           ValidationError: does not satisfy mapping requirement (2 differences): {
                            'Jervis Bay Territory': Deviation(-388, 388),
                            'Tasmania': Deviation(+505685, 514245),
                        }

            test_country_of_birth.py:51: ValidationError

    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8-9

            ======================================================================
            FAIL: test_population (test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 48, in test_population
                self.assertValid(data, requirement)
            ValidationError: does not satisfy mapping requirement (2 differences): {
                'Jervis Bay Territory': Deviation(-388, 388),
                'Tasmania': Deviation(+505685, 514245),
            }


In a previous test, we established that Jervis Bay Territory is
a known omission. We can handle this difference by allowing it
explicitly:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth.py
            :pyobject: test_population
            :lineno-match:
            :emphasize-lines: 5-7,9

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/modified_test_country_of_birth_unit.py
            :pyobject: TestPopulation.test_population
            :lineno-match:
            :emphasize-lines: 5-7,9


Running the test script again gives us one final difference to address:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 17

            _______________________________ test_population ________________________________

            detail = <Selector 'country_of_birth.csv'>
            summary = <Selector 'estimated_totals.csv'>

                def test_population(detail, summary):
                    data = detail({'state/territory': 'population'}).sum()
                    requirement = summary({'state/territory': 'population'}).sum()

                    omitted_territory = allowed.specific({
                        'Jervis Bay Territory': Deviation(-388, 388),
                    })

                    with allowed.percent(0.05) | omitted_territory:
            >           validate(data, requirement)
            E           ValidationError: does not satisfy mapping requirement (1 difference): {
                            'Tasmania': Deviation(+505685, 514245),
                        }

            test_country_of_birth.py:55: ValidationError


    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 8

            ======================================================================
            FAIL: test_population (test_country_of_birth_unit.TestPopulation)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "~/australian_population/test_country_of_birth_unit.py", line 52, in test_population
                self.assertValid(data, requirement)
            ValidationError: does not satisfy mapping requirement (1 difference): {
                'Tasmania': Deviation(+505685, 514245),
            }


In our detailed file, the population for Tasmania exceeds the expected
count by 505,685. Since the expected value is 514,245, this means that
the total count in our detailed file is almost *twice* as large as it
should be (505,685 + 514,245 = 1,019,930).

Looking in our **country_of_birth.csv** file, we can see that
the records for Tasmania include a row with a "SUBTOTAL":

.. literalinclude:: /_static/tutorial/country_of_birth.csv
    :language: none
    :lineno-match:
    :lines: 36-45
    :emphasize-lines: 9

With this "SUBTOTAL" row, our file is double-counting the population
in Tasmania. To correct the issue, we simply delete this row and
save our changes.


4. Clean Data
=============

By stepping through our tests one failure at a time, we have
cleaned our data. Running the script now should report all of
the tests as passing:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none

            ============================= test session starts ==============================
            platform linux -- Python 3.6.5, pytest-3.6.0, py-1.5.3, pluggy-0.6.0
            rootdir: ~/australian_population, inifile:
            plugins: datatest-0.1.2
            collected 3 items

            test_country_of_birth.py ...                                          [100%]

            =========================== 3 passed in 0.15 seconds ===========================

    .. group-tab:: Unittest

        .. code-block:: none

            ======================================================================
            ~/australian_population/test_country_of_birth_unit.py
            ...
            ----------------------------------------------------------------------
            Ran 3 tests in 0.042s

            OK


If you're having trouble replicating the steps above, you can check
your work against the following files:

* **Detailed File (cleaned):** :download:`modified_country_of_birth.csv </_static/tutorial/modified_country_of_birth.csv>`
* **Test Script (with allowances):**
    * :download:`modified_test_country_of_birth.py </_static/tutorial/modified_test_country_of_birth.py>` (for Pytest)
    * :download:`modified_test_country_of_birth_unit.py </_static/tutorial/modified_test_country_of_birth_unit.py>` (for Unittest)
