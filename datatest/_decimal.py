"""decimal compatibility layer"""
from decimal import *


try:
    Decimal.from_float  # New in 2.7
except AttributeError:
    import math as _math

    def _bit_length(integer):
        s = bin(integer)    # binary representation:  bin(-37) --> '-0b100101'
        s = s.lstrip('-0b') # remove leading zeros and minus sign
        return len(s)       # len('100101') --> 6

    @classmethod
    def _from_float(cls, f):
        if isinstance(f, int):                # handle integer inputs
            return cls(f)
        if not isinstance(f, float):
            raise TypeError("argument must be int or float.")
        if _math.isinf(f) or _math.isnan(f):
            return cls(repr(f))
        if _math.copysign(1.0, f) == 1.0:
            sign = 0
        else:
            sign = 1
        n, d = abs(f).as_integer_ratio()
        #k = d.bit_length() - 1
        k = _bit_length(d) - 1
        result = _dec_from_triple(sign, str(n*5**k), -k)
        if cls is Decimal:
            return result
        else:
            return cls(result)

    Decimal.from_float = _from_float


try:
    assert Decimal('1.0') == 1.0  # Changed in Python 3.2
except AssertionError:
    import numbers as _numbers
    from decimal import _dec_from_triple

    # Adapted from Python 3.2 standard library.
    def _convert_for_comparison(self, other, equality_op=False):
        if isinstance(other, Decimal):
            return self, other
        if isinstance(other, _numbers.Rational):
            if not self._is_special:
                self = _dec_from_triple(self._sign,
                                        str(int(self._int) * other.denominator),
                                        self._exp)
            return self, Decimal(other.numerator)
        if equality_op and isinstance(other, _numbers.Complex) and other.imag == 0:
            other = other.real
        if isinstance(other, float):
            context = getcontext()
            if equality_op:
                context.flags[FloatOperation] = 1
            else:
                context._raise_error(FloatOperation,
                    "strict semantics for mixing floats and Decimals are enabled")
            return self, Decimal.from_float(other)
        return NotImplemented, NotImplemented

    class FloatOperation(DecimalException, TypeError):
        """Enable stricter semantics for mixing floats and Decimals."""
        pass

    def _eq(self, other, context=None):
        self, other = _convert_for_comparison(self, other, equality_op=True)
        if other is NotImplemented:
            return other
        if self._check_nans(other, context):
            return False
        return self._cmp(other) == 0
    Decimal.__eq__ = _eq

    def _ne(self, other, context=None):
        self, other = _convert_for_comparison(self, other, equality_op=True)
        if other is NotImplemented:
            return other
        if self._check_nans(other, context):
            return True
        return self._cmp(other) != 0
    Decimal.__ne__ = _ne

    def _lt(self, other, context=None):
        self, other = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) < 0
    Decimal.__lt__ = _lt

    def _le(self, other, context=None):
        self, other = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) <= 0
    Decimal.__le__ = _le

    def _gt(self, other, context=None):
        self, other = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) > 0
    Decimal.__gt__ = _gt

    def _ge(self, other, context=None):
        self, other = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) >= 0
    Decimal.__ge__ = _ge
