"""builtins compatibility layer"""

try:
    from io import open as _open
    assert open == _open  # Starting in 3.1
except AssertionError:
    open = _open


try:
    callable  # Removed from 3.0 and 3.1, added back in 3.2.
except NameError:
    def callable(obj):
        parent_types = type(obj).__mro__
        return any('__call__' in typ.__dict__ for typ in parent_types)


# In the move to Python 3.0, map, filter, zip were replaced with their
# iterable equivalents from the itertools module.
try:
    map.__iter__
    filter.__iter__
    zip.__iter__
except AttributeError:
    from itertools import imap    as map
    from itertools import ifilter as filter
    from itertools import izip    as zip
