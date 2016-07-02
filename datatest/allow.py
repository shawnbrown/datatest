# -*- coding: utf-8 -*-
from .utils import itertools

from .differences import _make_decimal
from .differences import BaseDifference
from .differences import Missing
from .differences import Extra
from .error import DataAssertionError
#from .differences import Invalid
#from .differences import Deviation

__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


def _walk_diff(diff):
    """Iterate over difference or collection of differences."""
    if isinstance(diff, dict):
        diff = diff.values()
    elif isinstance(diff, BaseDifference):
        diff = (diff,)

    for item in diff:
        if isinstance(item, (dict, list, tuple)):
            for elt2 in _walk_diff(item):
                yield elt2
        else:
            if not isinstance(item, BaseDifference):
                raise TypeError('Object {0!r} is not derived from BaseDifference.'.format(item))
            yield item


class _BaseAllowance(object):
    """Base class for DataTestCase.allow...() context managers."""
    def __init__(self, test_case, msg=None):
        self.test_case = test_case
        self.obj_name = None
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        raise NotImplementedError()

    def _raiseFailure(self, standardMsg, differences):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        subject = self.test_case.subject
        #required = getattr(self.test_case, 'reference', None)
        try:
            required = self.test_case.reference
        except NameError:
            required = None

        exc = DataAssertionError(msg, differences, subject, required)
        exc.__cause__ = None  # Suppress context (usu. "raise ... from None")
        raise exc             # using verbose alternative to support older
                              # Python versions--see PEP 415.


class _AllowOnly(_BaseAllowance):
    """Context manager for DataTestCase.allowOnly() method."""
    def __init__(self, differences, test_case, msg=None):
        self.differences = differences
        super(_AllowOnly, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        diff = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        observed = list(_walk_diff(diff))
        allowed = list(_walk_diff(self.differences))
        not_allowed = [x for x in observed if x not in allowed]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!

        not_found = [x for x in allowed if x not in observed]
        if not_found:
            message = 'Allowed difference not found'
            self._raiseFailure(message, not_found)  # <- EXIT!
        return True


# TODO: Fix and normalize *msg* handling for all allowance managers.
class _AllowAny(_BaseAllowance):
    """Context manager for DataTestCase.allowAny() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        if number != None:
            assert number > 0, 'number must be positive'
        self.number = number
        #self.msg = msg
        self.filter_kwds = filter_by
        self.filter_class = BaseDifference
        super(_AllowAny, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])

        filter_class = self.filter_class
        is_class = lambda x: isinstance(x, filter_class)
        rejected_class, matched_class = self._partition(is_class, differences)

        rejected_kwds, matched_kwds = self._partition_kwds(matched_class, **self.filter_kwds)
        not_allowed = itertools.chain(rejected_kwds, rejected_class)

        message = getattr(exc_value, 'msg', '')
        matched_kwds = list(matched_kwds)
        observed = len(matched_kwds)
        if self.number and observed > self.number:
            not_allowed = itertools.chain(matched_kwds, not_allowed)  # Matching diffs go first.
            prefix = 'expected at most {0} matching difference{1}, got {2}: '
            plural = 's' if self.number != 1 else ''
            prefix = prefix.format(self.number, plural, observed)
            message = prefix + message

        not_allowed = list(not_allowed)
        if not_allowed:
            #if self.msg:
            #    message = self.msg + ': ' + message
            self._raiseFailure(message, not_allowed)  # <- EXIT!

        return True

    @classmethod
    def _partition_kwds(cls, differences, **filter_by):
        """Takes an iterable of *differences* and keyword filters,
        returns a 2-tuple of lists containing *nonmatches* and
        *matches* differences.
        """
        if not filter_by:
            return ([], differences)  # <- EXIT!

        for k, v in filter_by.items():
            if isinstance(v, str):
                filter_by[k] = (v,)  # If string, wrap in 1-tuple.
        filter_items = tuple(filter_by.items())

        def matches_filter(obj):
            for k, v in filter_items:
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return False
            return True

        return cls._partition(matches_filter, differences)

    @staticmethod
    def _partition(pred, iterable):
        """Use a predicate to partition entries into false entries and
        true entries.
        """
        t1, t2 = itertools.tee(iterable)
        return itertools.filterfalse(pred, t1), filter(pred, t2)


class _AllowMissing(_AllowAny):
    """Context manager for DataTestCase.allowMissing() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        super(_AllowMissing, self).__init__(test_case, number, msg, **filter_by)
        self.filter_class = Missing  # <- Only Missing differences.


class _AllowExtra(_AllowAny):
    """Context manager for DataTestCase.allowExtra() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        super(_AllowExtra, self).__init__(test_case, number, msg, **filter_by)
        self.filter_class = Extra  # <- Only Extra differences.


class _AllowDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowDeviation() method."""
    def __init__(self, lower, upper, test_case, msg, **filter_by):
        #assert deviation >= 0, 'Tolerance cannot be defined with a negative number.'

        lower = _make_decimal(lower)
        upper = _make_decimal(upper)

        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        self.lower = lower
        self.upper = upper
        super(_AllowDeviation, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            return (obj.value > self.upper) or (obj.value < self.lower)

        not_allowed = [x for x in differences if _not_allowed(x)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowPercentDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowPercentDeviation()
    method.
    """
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert 1 >= deviation >= 0, 'Percent tolerance must be between 0 and 1.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())
        self.deviation = deviation
        super(_AllowPercentDeviation, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            if not obj.required:
                return True  # <- EXIT!
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            percent = obj.value / obj.required
            return abs(percent) > self.deviation

        failed = [x for x in differences if _not_allowed(x)]
        if failed:
            self._raiseFailure(message, failed)  # <- EXIT!
        return True
