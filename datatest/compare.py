"""Comparison objects returned by data source queries."""
import inspect
from numbers import Number

from .utils.builtins import *
from .utils import collections
from .utils import functools
from .utils import itertools

from .differences import Extra
from .differences import Missing
from .differences import Invalid
from .differences import Deviation
from .differences import NotProperSubset
from .differences import NotProperSuperset


def _is_nscontainer(x):
    """Returns True if *x* is a non-string container object."""
    return not isinstance(x, str) and isinstance(x, collections.Container)


def _coerce_other(target_type, *type_args, **type_kwds):
    """Callable decorator for comparison methods to convert *other*
    argument into given *target_type* instance.
    """
    def callable(f):
        @functools.wraps(f)
        def wrapped(self, other):
            if not isinstance(other, target_type):
                try:
                    other = target_type(other, *type_args, **type_kwds)
                except TypeError:
                    return NotImplemented
            return f(self, other)
        return wrapped

    return callable


def _expects_multiple_params(func):
    """Returns True if callable obj expects multiple parameters."""
    try:
        funcsig = inspect.signature(func)
        params_dict = funcsig.parameters
        parameters = params_dict.values()
        args_type = (inspect._POSITIONAL_OR_KEYWORD, inspect._POSITIONAL_ONLY)
        args = [x for x in parameters if x.kind in args_type]
        varargs = [x for x in parameters if x.kind == inspect._VAR_POSITIONAL]

    except AttributeError:  # For Python 3.2 and earlier
        try:
            args, varargs = inspect.getfullargspec(func)[:2]

        except AttributeError:  # For Python 2.7 and earlier
            args, varargs = inspect.getargspec(func)[:2]

    return len(args) > 1 or bool(varargs)  # <- EXIT!


class BaseCompare(object):
    """Common base class for all comparison objects."""
    def __new__(cls, *args, **kwds):
        if cls is BaseCompare:
            msg = 'cannot instantiate BaseCompare directly - make a subclass'
            raise NotImplementedError(msg)
        return super(BaseCompare, cls).__new__(cls)


class CompareSet(BaseCompare, set):
    """DataSource query result set."""
    def __init__(self, data):
        """Initialize object."""
        if isinstance(data, collections.Mapping):
            raise TypeError('cannot be mapping')

        try:
            if isinstance(data, collections.Set):
                first_value = next(iter(data))
            else:
                data = iter(data)
                first_value = next(data)
                data = itertools.chain([first_value], data)  # Rebuild original.
        except StopIteration:
            first_value = None

        if _is_nscontainer(first_value) and len(first_value) == 1:
            data = (x[0] for x in data)  # Unpack single-item tuple.

        set.__init__(self, data)

    def make_rows(self, names):
        """Return an iterable of dictionary rows (like
        :mod:`csv.DictReader`) using *names* to construct dictionary
        keys.
        """
        single_value = next(iter(self))
        if _is_nscontainer(single_value):
            assert len(names) == len(single_value), "length of 'names' must match data items"
            iterable = iter(dict(zip(names, values)) for values in self)
        else:
            if _is_nscontainer(names):
                assert len(names) == 1, "length of 'names' must match data items"
                names = names[0]  # Unwrap names value.
            iterable = iter({names: value} for value in self)
        return iterable

    def __eq__(self, other):
        if not isinstance(other, CompareSet):
            try:
                other = CompareSet(other)
            except TypeError:
                return False
        return super(CompareSet, self).__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def all(self, key=None):
        assert callable(key) or key == None, 'key must be callable or None'
        if key == None:
            key = lambda x: x  # Default to identity function.
        elif _expects_multiple_params(key):
            wrapped = key
            key = lambda x: wrapped(*x)

        return all(key(x) for x in self.__iter__())  # Note: all() fn is lazy.

    def compare(self, other, op='=='):
        """Compare *self* to *other* and return a list of difference
        objects.  If *other* is callable, constructs a list of Invalid
        objects for values where *other* returns False.  If *other* is
        a CompareSet or other collection, differences are compiled as a
        list of Extra and Missing objects.
        """
        if callable(other):
            if _expects_multiple_params(other):
                wrapped = other
                other = lambda x: wrapped(*x)

            differences = [Invalid(x) for x in self if not other(x)]

        else:
            if not isinstance(other, CompareSet):
                other = CompareSet(other)

            if op in ('==', '<=', '<'):
                extra = self.difference(other)
                if op == '<' and not (extra or other.difference(self)):
                    extra = [NotProperSubset()]
                else:
                    extra = (Extra(x) for x in extra)
            else:
                extra = []

            if op in ('==', '>=', '>'):
                missing = other.difference(self)
                if op == '>' and not (missing or self.difference(other)):
                    missing = [NotProperSuperset()]
                else:
                    missing = (Missing(x) for x in missing)
            else:
                missing = []

            differences = list(itertools.chain(extra, missing))

        return differences


# Decorate CompareSet comparison magic methods (cannot be decorated in-line as
# class must first be defined).
_other_to_compareset = _coerce_other(CompareSet)
CompareSet.__lt__ = _other_to_compareset(CompareSet.__lt__)
CompareSet.__gt__ = _other_to_compareset(CompareSet.__gt__)
CompareSet.__le__ = _other_to_compareset(CompareSet.__le__)
CompareSet.__ge__ = _other_to_compareset(CompareSet.__ge__)


class CompareDict(BaseCompare, dict):
    """DataSource query result mapping."""
    def __init__(self, data, key_names):
        """Initialize object."""
        if not isinstance(data, collections.Mapping):
            data = dict(data)
        if not _is_nscontainer(key_names):
            key_names = (key_names,)

        try:
            iterable = iter(data.items())
            first_key, first_value = next(iterable)
            if _is_nscontainer(first_key) and len(first_key) == 1:
                iterable = itertools.chain([(first_key, first_value)], iterable)
                iterable = ((k[0], v) for k, v in iterable)
                data = dict(iterable)
        except StopIteration:
            pass

        dict.__init__(self, data)
        self.key_names = key_names

    def __repr__(self):
        cls_name = self.__class__.__name__
        key_names = self.key_names
        if _is_nscontainer(key_names) and len(key_names) == 1:
            key_names = key_names[0]
        dict_repr = dict.__repr__(self)
        return '{0}({1}, key_names={2!r})'.format(cls_name, dict_repr, key_names)

    def make_rows(self, names):
        """Return an iterable of dictionary rows (like
        :mod:`csv.DictReader`) using *names* to construct dictionary
        keys.
        """
        if not _is_nscontainer(names):
            names = (names,)

        key_names = self.key_names

        collision = set(names) & set(key_names)
        if collision:
            collision = ', '.join(collision)
            raise ValueError("names conflict: {0}".format(collision))

        single_key, single_value = next(iter(self.items()))
        iterable = self.items()
        if not _is_nscontainer(single_key):
            iterable = (((k,), v) for k, v in iterable)
            single_key = (single_key,)
        if not _is_nscontainer(single_value):
            iterable = ((k, (v,)) for k, v in iterable)
            single_value = (single_value,)

        assert len(single_key) == len(key_names)
        assert len(single_value) == len(names)

        def make_dictrow(k, v):
            x = dict(zip(key_names, k))
            x.update(dict(zip(names, v)))
            return x
        return iter(make_dictrow(k, v) for k, v in iterable)

    def compare(self, other):
        """Compare *self* to *other* and return a list of difference
        objects.  If *other* is callable, constructs a list of Invalid
        objects for values where *other* returns False.  If *other* is
        a CompareDict or other mapping object (like a dict),
        differences are compiled as a list of Deviation and Invalid
        objects.
        """
        # Evaluate self._data with function.
        if callable(other):
            if _expects_multiple_params(other):
                wrapped = other
                other = lambda x: wrapped(*x)

            keys = sorted(self.keys())
            differences = []
            for key in keys:
                value = self[key]
                if not other(value):
                    if not _is_nscontainer(key):
                        key = (key,)
                    kwds = dict(zip(self.key_names, key))
                    differences.append(Invalid(value, **kwds))
        # Compare self to other.
        else:
            if not isinstance(other, CompareDict):
                other = CompareDict(other, key_names=None)
            keys = itertools.chain(self.keys(), other.keys())
            keys = sorted(set(keys))
            differences = []
            for key in keys:
                self_val = self.get(key)
                other_val = other.get(key)
                if not _is_nscontainer(key):
                    key = (key,)
                one_num = any((
                    isinstance(self_val, Number),
                    isinstance(other_val, Number),
                ))
                num_or_none = all((
                    isinstance(self_val, Number) or self_val == None,
                    isinstance(other_val, Number) or other_val == None,
                ))
                # Numeric comparison.
                if one_num and num_or_none:
                    self_num = self_val if self_val != None else 0
                    other_num = other_val if other_val != None else 0
                    if self_num != other_num:
                        diff = self_num - other_num
                        kwds = dict(zip(self.key_names, key))
                        invalid = Deviation(diff, other_val, **kwds)
                        differences.append(Deviation(diff, other_val, **kwds))
                # Object comparison.
                else:
                    if self_val != other_val:
                        kwds = dict(zip(self.key_names, key))
                        differences.append(Invalid(self_val, other_val, **kwds))

        return differences

    def all(self, key=None):
        assert callable(key) or key == None, 'key must be callable or None'
        if key == None:
            key = lambda x: x  # Default to identity function.
        elif _expects_multiple_params(key):
            wrapped = key
            key = lambda x: wrapped(*x)

        return all(key(x) for x in self.values())  # Note: all() fn is lazy.


# Decorate CompareDict comparison magic methods (cannot be decorated in-line
# as class must first be defined).
_other_to_comparedict = _coerce_other(CompareDict, key_names=None)
CompareDict.__eq__ = _other_to_comparedict(CompareDict.__eq__)
CompareDict.__ne__ = _other_to_comparedict(CompareDict.__ne__)
