
import pytest
from datatest import working_directory
from datatest import Selector
from datatest import DataTestCase
from datatest import mandatory
from datatest import Missing, Extra, Deviation, Invalid


# Define fixtures.

def setUpModule():
    global detail
    global summary

    with working_directory(__file__):
        detail = Selector('country_of_birth.csv')
        summary = Selector('estimated_totals.csv')


# Begin tests.

class TestPopulation(DataTestCase):

    @mandatory
    def test_columns(self):
        required_set = set(summary.fieldnames)

        with self.allowedExtra():
            self.assertValid(detail.fieldnames, required_set)

    def test_states(self):
        data = detail({'state/territory'})
        requirement = summary({'state/territory'})

        omitted_territory = self.allowedSpecific([
            Missing('Jervis Bay Territory'),
        ])

        with omitted_territory:
            self.assertValid(data, requirement)

    def test_population(self):
        data = detail({'state/territory': 'population'}).sum()
        requirement = summary({'state/territory': 'population'}).sum()

        omitted_territory = self.allowedSpecific({
            'Jervis Bay Territory': Deviation(-388, 388),
        })

        with self.allowedPercent(0.03) | omitted_territory:
            self.assertValid(data, requirement)
