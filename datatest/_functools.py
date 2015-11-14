"""functools compatibility layer"""
from functools import *
from sys import version_info as _version_info


if _version_info[:2] <= (2, 7):  # For version 2.7 and earlier.

    def update_wrapper(wrapper,
                       wrapped,
                       assigned=WRAPPER_ASSIGNMENTS,
                       updated=WRAPPER_UPDATES):
        for attr in assigned:
            try:                                # <- This try/except
                value = getattr(wrapped, attr)  #    fixes issue #3445
            except AttributeError:              #    in Python 2.7 and
                pass                            #    earlier.
            else:
                setattr(wrapper, attr, value)
        for attr in updated:
            getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
        wrapper.__wrapped__ = wrapped
        return wrapper


    def wraps(wrapped,
              assigned=WRAPPER_ASSIGNMENTS,
              updated=WRAPPER_UPDATES):
        return partial(update_wrapper,  # <- Patched update_wrapper().
                       wrapped=wrapped,
                       assigned=assigned,
                       updated=updated)
