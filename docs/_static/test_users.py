import pytest
from datatest import working_directory
from datatest import Selector
from datatest import validate


@pytest.fixture(scope='module')
@working_directory(__file__)
def users():
    return Selector('users.csv')


def test_columns(users):
    validate(users.fieldnames, {'user_id', 'active'})


def test_user_id(users):

    def is_wellformed(x):  # <- Helper function.
        return x[:-1].isdigit() and x[-1:].isupper()

    validate(users('user_id'), is_wellformed)


def test_active(users):
    validate(users({'active'}), {'Y', 'N'})
