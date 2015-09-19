# -*- coding: utf-8 -*-
import glob
import os
import shutil
import tempfile

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
