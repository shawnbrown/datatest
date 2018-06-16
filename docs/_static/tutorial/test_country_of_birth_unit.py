
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

        self.assertValid(detail.fieldnames, required_set)

    def test_states(self):
        data = detail({'state/territory'})
        requirement = summary({'state/territory'})

        self.assertValid(data, requirement)

    def test_population(self):
        data = detail({'state/territory': 'population'}).sum()
        requirement = summary({'state/territory': 'population'}).sum()

        self.assertValid(data, requirement)
