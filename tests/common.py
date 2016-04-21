# -*- coding: utf-8 -*-
import glob
import os
import shutil
import tempfile

from . import _io as io
from . import _unittest as unittest

from datatest import BaseSource


class MkdtempTestCase(unittest.TestCase):
    # TestCase changes cwd to temporary location.  After testing,
    # removes files and restores original cwd.
    @classmethod
    def setUpClass(cls):
        cls._orig_dir = os.getcwd()
        cls._temp_dir = tempfile.mkdtemp()  # Requires mkdtemp--cannot

    @classmethod
    def tearDownClass(cls):
        os.rmdir(cls._temp_dir)

    def setUp(self):
        os.chdir(self._temp_dir)

    def tearDown(self):
        for path in glob.glob(os.path.join(self._temp_dir, '*')):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        os.chdir(self._orig_dir)

try:
    unittest.TestCase.setUpClass  # New in 2.7
except AttributeError:
    _MkdtempTestCase = MkdtempTestCase
    class MkdtempTestCase(_MkdtempTestCase):
        def setUp(self):
            self.setUpClass.__func__(self)
            _MkdtempTestCase.setUp(self)

        def tearDown(self):
            _MkdtempTestCase.tearDown(self)
            self.tearDownClass.__func__(self)


def make_csv_file(fieldnames, datarows):
    """Helper function to make CSV file-like object using *fieldnames*
    (a list of field names) and *datarows* (a list of lists containing
    the row values).
    """
    init_string = []
    init_string.append(','.join(fieldnames)) # Concat cells into row.
    for row in datarows:
        row = [str(cell) for cell in row]
        init_string.append(','.join(row))    # Concat cells into row.
    init_string = '\n'.join(init_string)     # Concat rows into final string.
    return io.StringIO(init_string)


class MinimalSource(BaseSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames):
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__ + '(<data>, <fieldnames>)'

    def columns(self):
        return self._fieldnames

    def __iter__(self):
        for row in self._data:
            yield dict(zip(self._fieldnames, row))
