# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from .utils import decimal


def _make_decimal(d):
    if isinstance(d, float):
        d = str(d)
    d = decimal.Decimal(d)

    if d == d.to_integral():                   # Remove_exponent (from official
        return d.quantize(decimal.Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


class BaseDifference(object):
    """The base class from which all differences must inherit."""
    def __new__(cls, *args, **kwds):
        if cls is BaseDifference:
            msg = 'cannot instantiate BaseDifference directly - make a subclass'
            raise NotImplementedError(msg)
        return super(BaseDifference, cls).__new__(cls)

    def __init__(self, value, required=None, **kwds):
        self._value = value
        self._required = required
        self._kwds = kwds

    @property
    def value(self):
        """The subject *value* that differs from the required value."""
        return self._value

    @property
    def required(self):
        """The *required* value that was expected by the test (not all
        differences will use this property)."""
        return self._required

    @property
    def kwds(self):
        """A dictionary of the keyword arguments to help indicate where
        the difference was detected in the subject data.
        """
        return self._kwds

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


class Missing(BaseDifference):
    """A value missing from the subject data which was part of the
    required data.
    """
    def __init__(self, value, **kwds):
        super(Missing, self).__init__(value, **kwds)


class Extra(BaseDifference):
    """An extra value found in the subject data that was not part of the
    required data.
    """
    def __init__(self, value, **kwds):
        super(Extra, self).__init__(value, **kwds)


class Invalid(BaseDifference):
    """A value in the subject data that did not satisfy a required
    condition (well-formedness, date range, regular expression match,
    etc.).
    """
    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.required == None:
            required = ''
        else:
            required = ', ' + repr(self.required)
        return '{0}({1!r}{2}{3})'.format(clsname, self.value, required, kwds)


class Deviation(BaseDifference):
    """The deviation between a numeric value in the subject data and a
    numeric value in the required data.
    """
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


class _NotFoundSentinel(object):
    """Sentinel for handling membership in collections."""
    def __repr__(self):
        return '<not found>'
_NOTFOUND = _NotFoundSentinel()
del _NotFoundSentinel


# TODO: Investigate possibility of removing **kwds from _getdiff().
def _getdiff(first, second, is_common=False, **kwds):
    """Returns difference object for two objects known to be unequal.
    The *is_common* flag, when True, signals that the *second* argument
    should be omitted when creating an "Invalid" difference.
    """
    # Prepare for numeric comparisons.
    _isnum = lambda x: isinstance(x, Number) and not isnan(x)
    first_isnum = _isnum(first)
    second_isnum = _isnum(second)

    # Numeric vs numeric.
    if first_isnum and second_isnum:
        difference = first - second
        return Deviation(difference, second, **kwds)

    # Numeric vs empty (or not found).
    if first_isnum and (not second or second is _NOTFOUND):
        if second is _NOTFOUND:
            second = None

        difference = first - 0
        return Deviation(difference, second, **kwds)

    # Empty (or not found) vs numeric.
    if (not first or first is _NOTFOUND) and second_isnum:
        if first is _NOTFOUND:
            first = None

        if second == 0:
            difference = first
        else:
            difference = 0 - second
        return Deviation(difference, second, **kwds)

    # Object vs _NOTFOUND.
    if second is _NOTFOUND:
        return Extra(first, **kwds)

    # _NOTFOUND vs object.
    if first is _NOTFOUND:
        return Missing(second, **kwds)

    # All other pairs of objects.
    if is_common:
        return Invalid(first, **kwds)
    return Invalid(first, second, **kwds)
