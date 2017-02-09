"""compatibility layer for built-in functions"""
from __future__ import absolute_import
from .misc import _is_consumable


try:
    from io import open as _open
    assert open == _open  # Starting in 3.1
    open = open
except AssertionError:
    open = _open


try:
    callable = callable  # Removed from 3.0 and 3.1, added back in 3.2.
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
    map = map
    filter = filter
    zip = zip
except AttributeError:
    from itertools import imap as map
    from itertools import ifilter as filter
    from itertools import izip as zip


try:
    max([0, 1], default=None)  # The default keyword for max()
    min([0, 1], default=None)  # and min() is new in 3.4.
    max = max
    min = min
except TypeError:
    from itertools import chain as _chain

    _max = max
    def max(*iterable, **kwds):
        """
        max(iterable, *[, default, key])
        max(arg1, arg2, *args, *[, key])
        """
        allowed_kwds = ('default', 'key')
        for key in kwds:
            if key not in allowed_kwds:
                msg = "'{0}' is an invalid keyword argument for this function"
                raise TypeError(msg.format(key))

        if len(iterable) == 1:
            iterable = iterable[0]

        try:
            first_item = next(iter(iterable))
            if _is_consumable(iterable):
                iterable = _chain([first_item], iterable)
        except StopIteration:
            if 'default' not in kwds:
                raise ValueError('max() arg is an empty sequence')
            return kwds['default']

        if 'key' in kwds:
            return _max(iterable, key=kwds['key'])
        return _max(iterable)

    _min = min
    def min(*iterable, **kwds):
        """
        min(iterable, *[, default, key])
        min(arg1, arg2, *args, *[, key])
        """
        allowed_kwds = ('default', 'key')
        for key in kwds:
            if key not in allowed_kwds:
                msg = "'{0}' is an invalid keyword argument for this function"
                raise TypeError(msg.format(key))

        if len(iterable) == 1:
            iterable = iterable[0]

        try:
            first_item = next(iter(iterable))
            if _is_consumable(iterable):
                iterable = _chain([first_item], iterable)
        except StopIteration:
            if 'default' not in kwds:
                raise ValueError('min() arg is an empty sequence')
            return kwds['default']

        if 'key' in kwds:
            return _min(iterable, key=kwds['key'])
        return _min(iterable)
