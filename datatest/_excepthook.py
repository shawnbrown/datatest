# -*- coding: utf-8 -*-
import sys
from .validation import ValidationError


if sys.excepthook:
    existing_excepthook = sys.excepthook
else:
    existing_excepthook = sys.__excepthook__


def _next_is_internal(tb):
    """Return True if the next traceback refers to an internal part of
    datatest.
    """
    tb_next = tb.tb_next
    if not tb_next:
        return False
    return (tb_next.tb_frame.f_globals.get('__datatest', False)
            or tb_next.tb_frame.f_globals.get('__unittest', False))


def excepthook(err_type, err_value, err_traceback):
    """Hide calls internal to datatest for ValidationError instances
    and print traceback and exception to sys.stderr.
    """
    if not issubclass(err_type, ValidationError):
        return existing_excepthook(err_type, err_value, err_traceback)

    try:
        tb = err_traceback
        while tb:
            if _next_is_internal(tb):
                tb.tb_next = None  # <- Only settable in 3.7 and newer.
                break
            tb = tb.tb_next

        existing_excepthook(err_type, err_value, err_traceback)

    except (AttributeError, TypeError):
        # In older versions of Python, "tb_next" is a read-only attribute.
        # Trying to set "tb_next" in versions 3.0 through 3.6 will raise an
        # AttributeError whereas versions 2.7 and older will raise a TypeError.
        limit = 1
        tb = err_traceback
        while tb:
            if _next_is_internal(tb):
                break
            limit += 1
            tb = tb.tb_next

        import traceback
        traceback.print_exception(err_type, err_value, err_traceback, limit)

