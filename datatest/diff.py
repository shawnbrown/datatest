# -*- coding: utf-8 -*-

from decimal import Decimal as _Decimal


class DiffBase(object):
    def __init__(self):
        raise NotImplementedError('Do not instantiate directly -- use '
                                  'subclasses instead.')

    def __repr__(self):
        raise NotImplementedError

    def _kwds_format(self):
        if not hasattr(self, 'kwds') or self.kwds == {}:
            return ''  # <- EXIT!
        kwds = sorted(self.kwds.items())
        try:
            kwds = [(k, unicode(v)) for k, v in kwds]  # Only if `unicode` is defined.
        except NameError:
            pass
        kwds = ['{0}={1!r}'.format(k, v) for k, v in kwds]
        kwds = ', '.join(kwds)
        return ', ' + kwds

    def __hash__(self):
        return hash((self.__class__, self.__repr__()))

    def __eq__(self, other):
        return hash(self) == hash(other)


class _ColumnBase(DiffBase):
    def __init__(self, diff):
        self.diff = diff

    def __repr__(self):
        clsname = self.__class__.__name__
        #try:
        #    return '{0}({1!r})'.format(clsname, unicode(self.diff))
        #except:
        return '{0}({1!r})'.format(clsname, self.diff)

class ExtraColumn(_ColumnBase): pass
class MissingColumn(_ColumnBase): pass


class _ValueBase(DiffBase):
    def __init__(self, diff, **kwds):
        self.diff = diff
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._kwds_format()
        return '{0}({1!r}{2})'.format(clsname, self.diff, kwds)

class ExtraValue(_ValueBase): pass
class MissingValue(_ValueBase): pass
class InvalidValue(_ValueBase): pass


def _make_decimal(d):
    if isinstance(d, float):
        d = str(d)
    d = _Decimal(d)

    # Remove_exponent (from official docs: 9.4.10. Decimal FAQ).
    if d == d.to_integral():
        return d.quantize(_Decimal(1))
    return d.normalize()


class InvalidNumber(DiffBase):
    def __init__(self, diff, value, **kwds):
        self.diff = _make_decimal(diff)
        self.sum = _make_decimal(value)
        self.kwds = kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._kwds_format()
        diff = '+' + str(self.diff) if self.diff > 0 else str(self.diff)
        return '{0}({1}, {2}{3})'.format(clsname, diff, self.sum, kwds)
