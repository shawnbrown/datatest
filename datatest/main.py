"""Datatest main program"""

from unittest import TestProgram as _TestProgram
from unittest import defaultTestLoader as _defaultTestLoader
from datatest import DataTestRunner

__unittest = True
__datatest = True


class DataTestProgram(_TestProgram):
    def __init__(self, module='__main__', defaultTest=None, argv=None,
                    testRunner=DataTestRunner,  # <- Default Test Runner!!!
                    testLoader=_defaultTestLoader, exit=True,
                    verbosity=1, failfast=None, catchbreak=None,
                    buffer=None, warnings=None):
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
                              buffer=buffer,
                              warnings=warnings)

main = DataTestProgram
