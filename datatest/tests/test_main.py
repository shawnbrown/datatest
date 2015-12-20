# -*- coding: utf-8 -*-
import glob
import os
import sys
import tempfile
import textwrap

from . import _io as io
from . import _unittest as unittest
from ._contextlib import redirect_stderr

# Import code to test.
from datatest.main import DataTestProgram


# Define load_module_from_file() for all supported versions.
try:
    try:
        # Python 3.5
        from importlib.util import spec_from_file_location
        from importlib.util import module_from_spec
        def load_module_from_file(name, path):
            """Helper function for tests."""
            spec = spec_from_file_location(name, path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules[name] = module
            return module
    except (AttributeError, ImportError):
        # Python 3.4 and 3.3
        from importlib.machinery import SourceFileLoader
        def load_module_from_file(name, path):
            """Helper function for tests."""
            loader = SourceFileLoader(name, path)
            module = loader.load_module()
            return module
except ImportError:
    # Python 3.2, 3.1, 2.7 and 2.6
    from imp import load_source
    def load_module_from_file(name, path):
        """Helper function for tests."""
        return load_source(name, path)


class TestDataTestProgram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create a temporary directory and use it as the working directory."""
        cls._orig_dir = os.getcwd()
        cls._temp_dir = tempfile.mkdtemp()
        os.chdir(cls._temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Restore original working directory and delete temp dir."""
        os.chdir(cls._orig_dir)
        os.rmdir(cls._temp_dir)

    def setUp(self):
        """Assert that we're working in the temporary directory."""
        assert os.getcwd() == self._temp_dir

    def tearDown(self):
        """Delete all files in temporary directory."""
        for path in glob.glob(os.path.join(self._temp_dir, '*')):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    @staticmethod
    def load_module(source_code):
        """Write source_code to file and import as module."""
        filename = 'testmodule.py'
        modname = 'testmodule'
        with open(filename, 'w') as fh:
            source_code = textwrap.dedent(source_code)
            fh.write(source_code)
        module = load_module_from_file(modname, filename)
        return module

    def test_simple_case(self):
        source_code = """
            import datatest

            class TestA(datatest.DataTestCase):
                def test_one(self):
                    self.assertTrue(True)

                def test_two(self):
                    self.assertTrue(False)  # <- TEST FAILURE!

            class TestB(datatest.DataTestCase):
                def test_three(self):
                    self.assertTrue(True)

        """
        module = self.load_module(source_code)

        with open(os.devnull, 'w') as devnul:
            with redirect_stderr(devnul):
                program = DataTestProgram(module=module, exit=False, argv=[''])

        result = program.result
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)

    def test_required_method(self):
        source_code = """
            import datatest

            class TestA(datatest.DataTestCase):
                def test_one(self):
                    self.assertTrue(True)

                @datatest.required  # <- "REQUIRED" DECORATOR
                def test_two(self):
                    self.assertTrue(False)  # <- TEST FAILURE!

            class TestB(datatest.DataTestCase):
                def test_three(self):
                    self.assertTrue(True)

        """
        module = self.load_module(source_code)

        with open(os.devnull, 'w') as devnul:
            with redirect_stderr(devnul):
                program = DataTestProgram(module=module, exit=False, argv=[''])

        result = program.result
        self.assertEqual(result.testsRun, 2)  # <- Should stop early, "test_two" is required.
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)

    def test_required_class(self):
        source_code = """
            import datatest

            @datatest.required  # <- "REQUIRED" DECORATOR
            class TestA(datatest.DataTestCase):
                def test_one(self):
                    self.assertTrue(True)

                def test_two(self):
                    self.assertTrue(False)  # <- TEST FAILURE!

            class TestB(datatest.DataTestCase):
                def test_three(self):
                    self.assertTrue(True)

        """
        module = self.load_module(source_code)

        with open(os.devnull, 'w') as devnul:
            with redirect_stderr(devnul):
                program = DataTestProgram(module=module, exit=False, argv=[''])

        result = program.result
        self.assertEqual(result.testsRun, 2)  # <- Should stop early, "test_two" is required.
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)


# Patch for setUpClass and tearDownClass on older versions of Python.
try:
    unittest.TestCase.setUpClass  # New in 2.7, 3.1 and earlier.
except AttributeError:
    _setUp = TestDataTestProgram.setUp
    def setUp(self):
        TestDataTestProgram.setUpClass.__func__(self)
        _setUp(self)
    TestDataTestProgram.setUp = setUp

    _tearDown = TestDataTestProgram.tearDown
    def tearDown(self):
        _tearDown(self)
        TestDataTestProgram.tearDownClass.__func__(self)
    TestDataTestProgram.tearDown = tearDown
