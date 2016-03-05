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
    def __init__(self, msg, differences, subject=None, required=None):
        """Initialize self, store *differences* for later reference."""
        if not differences:
            raise ValueError('Missing differences.')
        self.differences = differences
        self.msg = msg
        self.subject = str(subject)    # Subject data source.
        self.required = str(required)  # Required object or reference source.
        self._verbose = False  # <- Set by DataTestResult if verbose.

        return AssertionError.__init__(self, msg)

    def __repr__(self):
        return self.__class__.__name__ + ': ' + self.__str__()

    def __str__(self):
        diff = pprint.pformat(self.differences, width=1)
        if any([diff.startswith('{') and diff.endswith('}'),
                diff.startswith('[') and diff.endswith(']'),
                diff.startswith('(') and diff.endswith(')')]):
            diff = diff[1:-1]

        if self._verbose:
            msg_extras = '\n\nSUBJECT:\n{0}\nREQUIRED:\n{1}'
            msg_extras = msg_extras.format(self.subject, self.required)
        else:
            msg_extras = ''

        return '{0}:\n {1}{2}'.format(self.msg, diff, msg_extras)


class BaseDifference(object):
    def __init__(self, value, **kwds):
        self.value = value
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1!r}{2})'.format(clsname, self.value, kwds)

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
    def __init__(self, value, required=None, **kwds):
        self.value = value
        self.required = required
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.required == None:
            required = ''
        else:
            required = ', ' + repr(self.required)
        return '{0}({1!r}{2}{3})'.format(clsname, self.value, required, kwds)


class Deviation(BaseDifference):
    def __init__(self, value, required, **kwds):
        if not value:
            raise ValueError('value must be positive or negative number')
        self.value = _make_decimal(value)
        if required != None:
            required = _make_decimal(required)
        self.required = required
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        value = '{0:+}'.format(self.value)  # Apply +/- sign.
        return '{0}({1}, {2}{3})'.format(clsname, value, self.required, kwds)


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
