"""Comparison objects returned by data source queries."""
import re
from numbers import Number

from ..utils.builtins import *
from ..utils import collections
from ..utils import functools
from ..utils import itertools

from ..utils.misc import _expects_multiple_params
from ..utils.misc import _is_nsiterable
from ..utils.misc import _unique_everseen
from .api07_diffs import xExtra
from .api07_diffs import xMissing
from .api07_diffs import xInvalid
from .api07_diffs import xDeviation
from .api07_diffs import xNotProperSubset
from .api07_diffs import xNotProperSuperset

from .api07_diffs import _xgetdiff
from .api07_diffs import _xNOTFOUND

_regex_type = type(re.compile(''))


def _compare_sequence(data, required):
    """Compare *data* against sequence of *required* values."""
    assert isinstance(required, collections.Sequence)

    if isinstance(data, str):
        raise ValueError("uncomparable types: 'str' and sequence type")

    if not isinstance(data, collections.Sequence):
        type_name = type(data).__name__
        msg = "expected sequence type, but got " + repr(type_name)
        raise ValueError(msg)

    differences = dict()
    zipped = itertools.zip_longest(data, required, fillvalue=_xNOTFOUND)
    for index, (data_val, required_val) in enumerate(zipped):
        if data_val != required_val:
            differences[index] = _xgetdiff(data_val, required_val)
    return differences


def _compare_mapping(data, required):
    """Compare *data* against mapping of *required* values."""
    assert isinstance(required, collections.Mapping)
    if not isinstance(data, collections.Mapping):
        type_name = type(data).__name__
        msg = "expected mapping type, but got " + repr(type_name)
        raise ValueError(msg)

    differences = dict()
    all_keys = itertools.chain(required.keys(), data.keys())
    for key in _unique_everseen(all_keys):
        data_val = data.get(key, _xNOTFOUND)
        required_val = required.get(key, _xNOTFOUND)
        if data_val != required_val:
            differences[key] = _xgetdiff(data_val, required_val)
    return differences


def _compare_set(data, required):
    """Compare *data* against set of *required* values."""
    assert isinstance(required, collections.Set)

    if isinstance(data, collections.Mapping):
        data = data.values()

    if not isinstance(data, collections.Set):
        if isinstance(data, str):
            raise TypeError("uncomparable types: 'str' and 'set'")

        try:
            data = set(data)
        except TypeError:
            type_name = type(data).__name__
            msg = "uncomparable types: '{0}' and 'set'".format(type_name)
            raise TypeError(msg)

    missing = (xMissing(x) for x in required.difference(data))
    extra = (xExtra(x) for x in data.difference(required))
    return list(itertools.chain(missing, extra))


def _compare_other(data, required):
    """Compare *data* against *required* condition.  The *required*
    argument can be a callable, regular expression, or other object.
    """
    # Prepare wrapper for callable.
    if callable(required):
        if _expects_multiple_params(required):
            def wrapper(args):
                try:
                    return required(*args)  # <- Unpack args.
                except TypeError:
                    if not isinstance(args, collections.Iterable):
                        args = (args,)          # If arg not iterable, rerun using
                        return required(*args)  # 1-tuple for clearer error msg.
                    else:
                        raise  # Re-raise previous exception.
                except Exception:
                    return False  # All others, return False.
        else:
            def wrapper(x):
                try:
                    return required(x)
                except Exception:
                    return False
    # Prepare wrapper for compiled regular expression.
    elif isinstance(required, _regex_type):
        def wrapper(x):
            try:
                return required.search(x) != None
            except Exception:
                return False
    # Prepare wrapper for str or other object comparison.
    else:
        def wrapper(x):
            return x == required

    if isinstance(data, collections.Mapping):
        diffs = dict()
        for key, val in data.items():
            if not wrapper(val):
                diffs[key] = _xgetdiff(val, required, is_common=True)
        return diffs  # <- EXIT!

    is_not_str = not isinstance(data, str)

    if isinstance(data, collections.Sequence) and is_not_str:
        diffs = dict()
        for index, val in enumerate(data):
            if not wrapper(val):
                diffs[index] = _xgetdiff(val, required, is_common=True)
        return diffs  # <- EXIT!

    # For Sets and other Iterables.
    if isinstance(data, collections.Iterable) and is_not_str:
        diffs = [_xgetdiff(x, required, is_common=True) for x in data if not wrapper(x)]
        return diffs  # <- EXIT!

    # For string or non-iterable.
    if not wrapper(data):
        return [_xgetdiff(data, required, is_common=True)]

    return []  # If no differences, return empty list.


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


class BaseCompare(object):
    """Common base class for all comparison objects."""
    def __new__(cls, *args, **kwds):
        if cls is BaseCompare:
            msg = 'cannot instantiate BaseCompare directly - make a subclass'
            raise NotImplementedError(msg)
        return super(BaseCompare, cls).__new__(cls)


class CompareSet(BaseCompare, set):
    """A set of values, usually returned from a data source method like
    :meth:`columns() <BaseSource.columns>` or :meth:`distinct()
    <BaseSource.distinct>`, that can be compared against required data
    to produce a collection of differences.
    """
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

        if _is_nsiterable(first_value) and len(first_value) == 1:
            data = (x[0] for x in data)  # Unpack single-item tuple.

        set.__init__(self, data)

    def make_rows(self, names):
        """Return an iterable of dictionary rows (like
        :mod:`csv.DictReader`) using *names* to construct dictionary
        keys.
        """
        single_value = next(iter(self))
        if _is_nsiterable(single_value):
            assert len(names) == len(single_value), "length of 'names' must match data items"
            iterable = iter(dict(zip(names, values)) for values in self)
        else:
            if _is_nsiterable(names):
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
        objects.  If *other* is callable, constructs a list of xInvalid
        objects for values where *other* returns False.  If *other* is
        a CompareSet or other collection, differences are compiled as a
        list of xExtra and xMissing objects.
        """
        if callable(other):
            if _expects_multiple_params(other):
                wrapped = other
                other = lambda x: wrapped(*x)

            differences = [xInvalid(x) for x in self if not other(x)]

        else:
            if not isinstance(other, CompareSet):
                other = CompareSet(other)

            if op in ('==', '<=', '<'):
                extra = self.difference(other)
                if op == '<' and not (extra or other.difference(self)):
                    extra = [xNotProperSubset()]
                else:
                    extra = (xExtra(x) for x in extra)
            else:
                extra = []

            if op in ('==', '>=', '>'):
                missing = other.difference(self)
                if op == '>' and not (missing or self.difference(other)):
                    missing = [xNotProperSuperset()]
                else:
                    missing = (xMissing(x) for x in missing)
            else:
                missing = []

            differences = list(itertools.chain(extra, missing))

        return differences


# Decorate CompareSet comparison magic methods (cannot be decorated
# in-line as class must first be defined).
_other_to_compareset = _coerce_other(CompareSet)
CompareSet.__lt__ = _other_to_compareset(CompareSet.__lt__)
CompareSet.__gt__ = _other_to_compareset(CompareSet.__gt__)
CompareSet.__le__ = _other_to_compareset(CompareSet.__le__)
CompareSet.__ge__ = _other_to_compareset(CompareSet.__ge__)


class CompareDict(BaseCompare, dict):
    """A dictionary of values, usually returned from a data source
    method like :meth:`sum() <BaseSource.sum>` or :meth:`mapreduce()
    <BaseSource.mapreduce>`, that can be compared against required data
    to produce a collection of differences.
    """
    def __init__(self, data, key_names=None):
        """Initialize object."""
        if not isinstance(data, collections.Mapping):
            data = dict(data)

        try:
            iterable = iter(data.items())
            first_key, first_value = next(iterable)
            if _is_nsiterable(first_key) and len(first_key) == 1:
                iterable = itertools.chain([(first_key, first_value)], iterable)
                iterable = ((k[0], v) for k, v in iterable)
                data = dict(iterable)
        except StopIteration:
            first_key = []

        dict.__init__(self, data)

        if key_names == None:  # If missing, make keys (_0, _1, ...).
            key_names = range(len(first_key))
            key_names = tuple('_' + str(x) for x in key_names)
        elif not _is_nsiterable(key_names):
            key_names = (key_names,)

        self.key_names = key_names

    def __repr__(self):
        cls_name = self.__class__.__name__
        key_names = self.key_names
        if _is_nsiterable(key_names) and len(key_names) == 1:
            key_names = key_names[0]
        dict_repr = dict.__repr__(self)
        return '{0}({1}, key_names={2!r})'.format(cls_name, dict_repr, key_names)

    def make_rows(self, names):
        """Return an iterable of dictionary rows (like
        :mod:`csv.DictReader`) using *names* to construct dictionary
        keys.
        """
        if not _is_nsiterable(names):
            names = (names,)

        key_names = self.key_names

        collision = set(names) & set(key_names)
        if collision:
            collision = ', '.join(collision)
            raise ValueError("names conflict: {0}".format(collision))

        single_key, single_value = next(iter(self.items()))
        iterable = self.items()
        if not _is_nsiterable(single_key):
            iterable = (((k,), v) for k, v in iterable)
            single_key = (single_key,)
        if not _is_nsiterable(single_value):
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
        objects.  If *other* is callable, constructs a list of xInvalid
        objects for values where *other* returns False.  If *other* is
        a CompareDict or other mapping object (like a dict),
        differences are compiled as a list of xDeviation and xInvalid
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
                    if not _is_nsiterable(key):
                        key = (key,)
                    kwds = dict(zip(self.key_names, key))
                    differences.append(xInvalid(value, **kwds))
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

                if not _is_nsiterable(key):
                    key = (key,)
                kwds = dict(zip(self.key_names, key))

                # Numeric vs numeric.
                if isinstance(self_val, Number) and isinstance(other_val, Number):
                    diff = self_val - other_val
                    if diff:
                        differences.append(xDeviation(diff, other_val, **kwds))
                # Numeric vs empty.
                elif isinstance(self_val, Number) and not other_val:
                    diff = self_val - 0
                    differences.append(xDeviation(diff, other_val, **kwds))
                # Empty vs numeric.
                elif not self_val and isinstance(other_val, Number):
                    if other_val == 0:
                        diff = self_val
                    else:
                        diff = 0 - other_val
                    differences.append(xDeviation(diff, other_val, **kwds))
                # Object vs empty.
                elif self_val and not other_val:
                    differences.append(Extra(self_val, **kwds))
                # Empty vs object.
                elif not self_val and other_val:
                    differences.append(xMissing(other_val, **kwds))
                # Object vs object.
                else:
                    if self_val != other_val:
                        differences.append(xInvalid(self_val, other_val, **kwds))

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
