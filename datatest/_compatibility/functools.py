"""compatibility layer for functools (Python standard library)"""
from __future__ import absolute_import
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


try:
    partialmethod  # New in version 3.4.
except NameError:
    # Adapted from the Python 3.6 Standard Library.
    class partialmethod(object):
        def __init__(self, func, *args, **keywords):
            if not callable(func) and not hasattr(func, "__get__"):
                raise TypeError("{!r} is not callable or a descriptor"
                                     .format(func))

            if isinstance(func, partialmethod):
                self.func = func.func
                self.args = func.args + args
                self.keywords = func.keywords.copy()
                self.keywords.update(keywords)
            else:
                self.func = func
                self.args = args
                self.keywords = keywords

        def __repr__(self):
            args = ", ".join(map(repr, self.args))
            keywords = ", ".join("{}={!r}".format(k, v)
                                     for k, v in self.keywords.items())
            format_string = "{module}.{cls}({func}, {args}, {keywords})"
            return format_string.format(module=self.__class__.__module__,
                                        cls=self.__class__.__qualname__,
                                        func=self.func,
                                        args=args,
                                        keywords=keywords)

        def _make_unbound_method(self):
            def _method(*args, **keywords):
                call_keywords = self.keywords.copy()
                call_keywords.update(keywords)
                #cls_or_self, *rest = args
                cls_or_self, rest = args[0], args[1:]
                call_args = (cls_or_self,) + self.args + tuple(rest)
                return self.func(*call_args, **call_keywords)
            _method.__isabstractmethod__ = self.__isabstractmethod__
            _method._partialmethod = self
            return _method

        def __get__(self, obj, cls):
            get = getattr(self.func, "__get__", None)
            result = None
            if get is not None:
                new_func = get(obj, cls)
                if new_func is not self.func:
                    result = partial(new_func, *self.args, **self.keywords)
                    try:
                        result.__self__ = new_func.__self__
                    except AttributeError:
                        pass
            if result is None:
                result = self._make_unbound_method().__get__(obj, cls)
            return result

        @property
        def __isabstractmethod__(self):
            return getattr(self.func, "__isabstractmethod__", False)
