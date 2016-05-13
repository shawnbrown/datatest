# -*- coding: utf-8 -*-
import pprint
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
    """Base class for to indicate non-strict subset or superset
    relationships.
    """
    def __new__(cls, *args, **kwds):
        if cls is NonStrictRelation:
            msg = 'cannot instantiate NonStrictRelation directly - make a subclass'
            raise NotImplementedError(msg)
        return super(NonStrictRelation, cls).__new__(cls)

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
