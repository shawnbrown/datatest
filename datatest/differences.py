# -*- coding: utf-8 -*-
import pprint
from ._decimal import Decimal as _Decimal


def _make_decimal(d):
    if isinstance(d, float):
        d = str(d)
    d = _Decimal(d)

    if d == d.to_integral():             # Remove_exponent (from official
        return d.quantize(_Decimal(1))   # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


class DataAssertionError(AssertionError):
    """Data assertion failed."""
    def __init__(self, msg, diff, reference=None, subject=None):
        """Initialize self, store difference for later reference."""
        if not diff:
            raise ValueError('Missing difference.')
        self.diff = diff
        self.msg = msg
        self.reference = str(reference)  # Reference data source or object.
        self.subject = str(subject)  # Subject data source.
        self._verbose = False  # <- Set by DataTestResult if verbose.

        return AssertionError.__init__(self, msg)

    def __repr__(self):
        return self.__class__.__name__ + ': ' + self.__str__()

    def __str__(self):
        diff = pprint.pformat(self.diff, width=1)
        if any([diff.startswith('{') and diff.endswith('}'),
                diff.startswith('[') and diff.endswith(']'),
                diff.startswith('(') and diff.endswith(')')]):
            diff = diff[1:-1]

        if self._verbose:
            msg_extras = '\n\nREFERENCE DATA:\n{0}\nSUBJECT DATA:\n{1}'
            msg_extras = msg_extras.format(self.reference, self.subject)
        else:
            msg_extras = ''

        return '{0}:\n {1}{2}'.format(self.msg, diff, msg_extras)


class BaseDifference(object):
    def __init__(self, item, **kwds):
        self.item = item
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1!r}{2})'.format(clsname, self.item, kwds)

    def __hash__(self):
        return hash((self.__class__, self.__repr__()))

    def __eq__(self, other):
        return hash(self) == hash(other)

    @staticmethod
    def _format_kwds(kwds):
        if not kwds:
            return ''  # <- EXIT!
        kwds = sorted(kwds.items())
        try:
            kwds = [(k, unicode(v)) for k, v in kwds]  # Only if `unicode` is defined.
        except NameError:
            pass
        kwds = ['{0}={1!r}'.format(k, v) for k, v in kwds]
        kwds = ', '.join(kwds)
        return ', ' + kwds


class Extra(BaseDifference):
    pass


class Missing(BaseDifference):
    pass


class Invalid(BaseDifference):
    def __init__(self, item, expected=None, **kwds):
        self.item = item
        self.expected = expected
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.expected == None:
            expected = ''
        else:
            expected = ', ' + repr(self.expected)
        return '{0}({1!r}{2}{3})'.format(clsname, self.item, expected, kwds)


class Deviation(BaseDifference):
    def __init__(self, diff, expected, **kwds):
        if not diff:
            raise ValueError('diff must be positive or negative number')
        self.diff = _make_decimal(diff)
        if expected != None:
            expected = _make_decimal(expected)
        self.expected = expected
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        diff = '{0:+}'.format(self.diff)  # Apply +/- sign.
        return '{0}({1}, {2}{3})'.format(clsname, diff, self.expected, kwds)


class NonStrictRelation(BaseDifference):
    """Base class for to indicate non-strict subset or superset relationships."""
    def __init__(self, **kwds):
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1})'.format(clsname, kwds)


class NotProperSubset(NonStrictRelation):
    pass


class NotProperSuperset(NonStrictRelation):
    pass
