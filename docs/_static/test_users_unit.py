from datatest import working_directory
from datatest import Selector
from datatest import DataTestCase


def setUpModule():
    global users
    with working_directory(__file__):
        users = Selector('users.csv')


class TestUserData(DataTestCase):

    def test_columns(self):
        self.assertValid(users.fieldnames, {'user_id', 'active'})

    def test_user_id(self):

        def is_wellformed(x):  # <- Helper function.
            return x[:-1].isdigit() and x[-1:].isupper()

        self.assertValid(users('user_id'), is_wellformed)

    def test_active(self):
        self.assertValid(users({'active'}), {'Y', 'N'})
