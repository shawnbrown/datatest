# -*- coding: utf-8 -*-
import pprint
from numbers import Number
from math import isnan
from .utils import decimal


def _make_decimal(d):
    if isinstance(d, float):
        d = str(d)
    d = decimal.Decimal(d)

    if d == d.to_integral():                   # Remove_exponent (from official
        return d.quantize(decimal.Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


class BaseDifference(object):
    def __new__(cls, *args, **kwds):
        if cls is BaseDifference:
            msg = 'cannot instantiate BaseDifference directly - make a subclass'
            raise NotImplementedError(msg)
        return super(BaseDifference, cls).__new__(cls)

    def __init__(self, value, required=None, **kwds):
        self.value = value
        self.required = required
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
    """Additional value that is not part of a required set."""
    def __init__(self, value, **kwds):
        super(Extra, self).__init__(value, **kwds)


class Missing(BaseDifference):
    """Missing value that is part of a required set."""
    def __init__(self, value, **kwds):
        super(Missing, self).__init__(value, **kwds)


class Invalid(BaseDifference):
    """Invalid item that does not match a required check."""
    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.required == None:
            required = ''
        else:
            required = ', ' + repr(self.required)
        return '{0}({1!r}{2}{3})'.format(clsname, self.value, required, kwds)


class Deviation(BaseDifference):
    """Deviation from a required numeric value."""
    def __init__(self, value, required, **kwds):
        empty = lambda x: not x or isnan(x)
        if (not empty(required) and empty(value)) or (required == 0 and value == 0):
            raise ValueError('numeric deviation must be positive or negative')

        if value or value is 0:
            value = _make_decimal(value)

        if required or required is 0:
            required = _make_decimal(required)

        super(Deviation, self).__init__(value, required, **kwds)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        value = self.value
        if value:
            try:
                value = '{0:+}'.format(value)  # Apply +/- sign.
            except (TypeError, ValueError):
                pass
        return '{0}({1}, {2}{3})'.format(clsname, value, self.required, kwds)


class NonStrictRelation(BaseDifference):
    """Base class for non-strict subset or superset relationships."""
    def __new__(cls, *args, **kwds):
        if cls is NonStrictRelation:
            msg = 'cannot instantiate NonStrictRelation directly - make a subclass'
            raise NotImplementedError(msg)
        return super(NonStrictRelation, cls).__new__(cls)

    def __init__(self, **kwds):
        super(NonStrictRelation, self).__init__(None, None, **kwds)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1})'.format(clsname, kwds)


class NotProperSubset(NonStrictRelation):
    """Not a proper subset of a required set."""
    pass


class NotProperSuperset(NonStrictRelation):
    """Not a proper superset of a required set."""
    pass
