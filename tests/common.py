# -*- coding: utf-8 -*-
import glob
import os
import shutil
import sys
import tempfile
import warnings
from functools import wraps

from . import _io as io
from . import _unittest as unittest


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


def ignore_deprecations(obj):
    """A class and function decorator to ignore DeprecationWarnings."""
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', DeprecationWarning)
                return func(*args, **kwds)
        return wrapper

    if isinstance(obj, type):
        # If object is a class, decorate its methods.
        for key, val in obj.__dict__.items():
            if callable(val):
                setattr(obj, key, decorate(val))
    else:
        # Else decorate the object itself.
        obj = decorate(obj)

    return obj


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
