"""Datatest main program"""
import sys as _sys
from unittest import TestProgram as _TestProgram
from unittest import defaultTestLoader as _defaultTestLoader

from datatest import DataTestRunner

__unittest = True
__datatest = True


if _sys.version_info[:2] == (3, 1):
    class DataTestProgram(_TestProgram):
        def __init__(self, module='__main__', defaultTest=None, argv=None,
                       testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                       exit=True):
            _TestProgram.__init__(self,
                                  module=module,
                                  defaultTest=defaultTest,
                                  argv=argv,
                                  testRunner=testRunner,
                                  testLoader=testLoader,
                                  exit=exit)

elif _sys.version_info[:2] == (2, 6):
    class DataTestProgram(_TestProgram):
        def __init__(self, module='__main__', defaultTest=None, argv=None,
                       testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                       exit=True):
            self.exit = exit  # <- Base class does not handle exit argument.
            _TestProgram.__init__(self,
                                  module=module,
                                  defaultTest=defaultTest,
                                  argv=argv,
                                  testRunner=testRunner,
                                  testLoader=testLoader)

        def runTests(self):
            if isinstance(self.testRunner, type):
                try:
                    testRunner = self.testRunner(verbosity=self.verbosity)
                except TypeError:
                    testRunner = self.testRunner()
            else:
                testRunner = self.testRunner
            self.result = testRunner.run(self.test)
            if self.exit:
                _sys.exit(not self.result.wasSuccessful())

else:  # For all other supported versions of Python.
    class DataTestProgram(_TestProgram):
        def __init__(self, module='__main__', defaultTest=None, argv=None,
                       testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                       exit=True, verbosity=1, failfast=None, catchbreak=None,
                       buffer=None):
            _TestProgram.__init__(self,
                                  module=module,
                                  defaultTest=defaultTest,
                                  argv=argv,
                                  testRunner=testRunner,
                                  testLoader=testLoader,
                                  exit=exit,
                                  verbosity=verbosity,
                                  failfast=failfast,
                                  catchbreak=catchbreak,
                                  buffer=buffer)


main = DataTestProgram
