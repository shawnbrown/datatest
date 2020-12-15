"""Test API for 0.9.x compatibility."""
from . import _unittest as unittest
import datatest
from datatest.__past__ import api09  # <- MONKEY PATCH!!!


class TestSubsetAndSupersetMethods(unittest.TestCase):
    """Semantics were inverted in the following version (0.10.x)."""

    def test_subset(self):
        """Check old-style 0.9.x API validate.subset() behavior."""
        data = ['A', 'B', 'C', 'D']
        requirement = set(['A', 'B'])
        datatest.validate.subset(data, requirement)

    def test_superset(self):
        """Check old-style 0.9.x API validate.superset() behavior."""
        data = ['A', 'B']
        requirement = set(['A', 'B', 'C', 'D'])
        datatest.validate.superset(data, requirement)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
