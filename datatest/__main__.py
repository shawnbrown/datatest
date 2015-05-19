"""Main entry point"""

import sys
if sys.argv[0].endswith('__main__.py'):
    import os.path
    # We change sys.argv[0] to make help message more useful
    # use executable without path, unquoted
    # (it's just a hint anyway)
    # (if you have spaces in your executable you get what you deserve!)
    executable = os.path.basename(sys.executable)
    sys.argv[0] = executable + ' -m datatest'
    del os

__unittest = True
__datatest = True

#from unittest import main, TestProgram
from unittest import main
from datatest.runner import DataTestRunner

main(module=None, testRunner=DataTestRunner)
