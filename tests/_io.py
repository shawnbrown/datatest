from io import *
from sys import version_info as _version_info


if _version_info[:2] <= (2, 7):  # For version 2.7 and earlier.
    import StringIO as _StringIO

    StringIO = _StringIO.StringIO
    class StringIO(_StringIO.StringIO):
        def write(self, str):
            str = unicode(str)
            return _StringIO.StringIO.write(self, str)
