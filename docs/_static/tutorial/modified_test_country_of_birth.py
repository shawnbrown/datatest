
import pytest
from datatest import working_directory
from datatest import Select
from datatest import validate
from datatest import allowed
from datatest import Missing, Extra, Deviation, Invalid


# Define fixtures.

@pytest.fixture(scope='module')
@working_directory(__file__)
def detail():
    return Select('country_of_birth.csv')


@pytest.fixture(scope='module')
@working_directory(__file__)
def summary():
    return Select('estimated_totals.csv')


# Begin tests.

@pytest.mark.mandatory
def test_columns(detail, summary):
    required_set = set(summary.fieldnames)

    with allowed.extra():
        validate(detail.fieldnames, required_set)


def test_state_labels(detail, summary):
    data = detail({'state/territory'})
    requirement = summary({'state/territory'})

    omitted_territory = allowed.specific([
        Missing('Jervis Bay Territory'),
    ])

    with omitted_territory:
        validate(data, requirement)


def test_population_format(detail):
    data = detail({'population'})

    def integer_format(x):  # <- Helper function.
        return str(x).isdecimal()

    validate(data, integer_format)


def test_population_sums(detail, summary):
    data = detail({'state/territory': 'population'}).sum()
    requirement = summary({'state/territory': 'population'}).sum()

    omitted_territory = allowed.specific({
        'Jervis Bay Territory': Deviation(-388, 388),
    })

    with allowed.percent(0.03) | omitted_territory:
        validate(data, requirement)
