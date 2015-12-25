"""Datatest main program"""
import sys as _sys
from unittest import TestProgram as _TestProgram
from unittest import defaultTestLoader as _defaultTestLoader
try:
    from unittest.signals import installHandler
except ImportError:
    installHandler = None

from datatest import DataTestRunner

__unittest = True
__datatest = True


class DataTestProgram(_TestProgram):
    def __init__(self, module='__main__', defaultTest=None, argv=None,
                   testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                   exit=True, verbosity=1, failfast=None, catchbreak=None,
                   buffer=None, ignore=False):
        self.ignore = ignore
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

    def runTests(self):
        try:
            if self.catchbreak and installHandler:
                installHandler()
        except AttributeError:
            pass  # does not have catchbreak attribute

        if self.testRunner is None:
            self.testRunner = DataTestRunner

        if isinstance(self.testRunner, type):
            try:
                kwds = ['verbosity', 'failfast', 'buffer', 'warnings', 'ignore']
                kwds = [attr for attr in kwds if hasattr(self, attr)]
                kwds = dict((attr, getattr(self, attr)) for attr in kwds)
                testRunner = self.testRunner(**kwds)
            except TypeError:
                if 'warnings' in kwds:
                    del kwds['warnings']
                testRunner = self.testRunner(**kwds)
        else:
            # assumed to be a TestRunner instance
            testRunner = self.testRunner

        self.result = testRunner.run(self.test)
        if self.exit:
            _sys.exit(not self.result.wasSuccessful())


if _sys.version_info[:2] == (3, 1):  # Patch methods for Python 3.1.
    def __init__(self, module='__main__', defaultTest=None, argv=None,
                   testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                   exit=True, ignore=False):
        self.ignore = ignore
        _TestProgram.__init__(self,
                              module=module,
                              defaultTest=defaultTest,
                              argv=argv,
                              testRunner=testRunner,
                              testLoader=testLoader,
                              exit=exit)
    DataTestProgram.__init__ = __init__

elif _sys.version_info[:2] == (2, 6):  # Patch runTests() for Python 2.6.
    def __init__(self, module='__main__', defaultTest=None, argv=None,
                   testRunner=DataTestRunner, testLoader=_defaultTestLoader,
                   exit=True, ignore=False):
        self.exit = exit  # <- 2.6 does not handle exit argument.
        self.ignore = ignore
        _TestProgram.__init__(self,
                              module=module,
                              defaultTest=defaultTest,
                              argv=argv,
                              testRunner=testRunner,
                              testLoader=testLoader)
    DataTestProgram.__init__ = __init__


main = DataTestProgram
