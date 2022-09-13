from __future__ import annotations

import decimal
import math

import numpy as np


# noinspection PyPep8Naming, PyShadowingBuiltins
class float_(object):
    def __init__(self, value: int | float | str | np.float_, /, precision: int = 100):
        if not isinstance(precision, int):
            raise TypeError('precision of Finance.float must be int')

        self._value = value.float if isinstance(value, self.__class__) else np.float_(value)
        self._precision = precision
        self._tick_size = 1. / self._precision

        self._int = round(self._value * self._precision)
        self._err = self._value * self._precision - self._int
        self._sign = np.sign(self._value)

        self._decimal_exponent = math.ceil(np.log10(self._precision))
        self._decimal_str = (self._int / self._precision).__format__(f'.{self._decimal_exponent}f')
        self._decimal = decimal.Decimal(self._decimal_str)

    def __repr__(self):
        return self._decimal_str

    def __format__(self, *args, **kwargs):
        return self._value.__format__(*args, **kwargs)

    @property
    def float(self):
        return self._value

    @property
    def precision(self):
        return self._precision

    @property
    def tick_size(self):
        return self._tick_size

    @property
    def decimal(self):
        return self._decimal

    # method using np.float_
    def __abs__(self, *args, **kwargs):
        return self._value.__abs__(*args, **kwargs)

    def __and__(self, *args, **kwargs):
        return self._value.__and__(*args, **kwargs)

    def __rand__(self, *args, **kwargs):
        return self._value.__rand__(*args, **kwargs)

    def __or__(self, *args, **kwargs):
        return self._value.__or__(*args, **kwargs)

    def __ror__(self, *args, **kwargs):  # real signature unknown
        return self._value.__ror__(*args, **kwargs)

    def __float__(self, *args, **kwargs):
        return self._value.__float__(*args, **kwargs)

    def __floordiv__(self, *args, **kwargs):
        return self._value.__floordiv__(*args, **kwargs)

    def __int__(self, *args, **kwargs):
        return self._value.__int__(*args, **kwargs)

    def __invert__(self, *args, **kwargs):
        return self._value.__invert__(*args, **kwargs)

    def __lshift__(self, *args, **kwargs):
        return self._value.__lshift__(*args, **kwargs)

    def __rlshift__(self, *args, **kwargs):
        return self._value.__rlshift__(*args, **kwargs)

    def __rrshift__(self, *args, **kwargs):  # real signature unknown
        return self._value.__rrshift__(*args, **kwargs)

    def __rshift__(self, *args, **kwargs):  # real signature unknown
        return self._value.__rshift__(*args, **kwargs)

    # method using Decimal
    def __hash__(self):
        return self._decimal.__hash__()

    # overridden method
    def __bool__(self):
        if self._int == 0:
            return False
        else:
            return True

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision > other._int * self.precision
        else:
            return self._decimal > other

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision < other._int * self.precision
        else:
            return self._decimal < other

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision == other._int * self.precision
        else:
            return self._decimal == other

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision != other._int * self.precision
        else:
            return self._decimal != other

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision >= other._int * self.precision
        else:
            return self._decimal >= other

    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self._int * other.precision <= other._int * self.precision
        else:
            return self._decimal <= other

    def __add__(self, other):
        if isinstance(other, self.__class__):
            _precision = max(self._precision, other._precision)
            return self.__class__(self._value + other._value, precision=_precision)
        else:
            return self._value.__add__(other)

    def __divmod__(self, other):
        if isinstance(other, self.__class__):
            return self._value.__divmod__(other._value)
        else:
            return self._value.__divmod__(other)

    def __mod__(self, other):
        return self.__class__(self._value.__mod__(other), precision=self._precision)

    def __mul__(self, other):
        return self.__class__(self._value.__mul__(other), precision=self._precision)

    def __neg__(self, other):
        return self.__class__(self._value.__neg__(other), precision=self._precision)

    def __pos__(self):
        return self

    def __pow__(self, other):  # real signature unknown
        return self.__class__(self._value.__pow__(other), precision=self._precision)

    def __radd__(self, other):  # real signature unknown
        return self.__add__(other)

    def __rdivmod__(self, other):  # real signature unknown
        if isinstance(other, self.__class__):
            return self._value.__rdivmod__(other._value)
        else:
            return self._value.__rdivmod__(other)

    def __rfloordiv__(self, other):  # real signature unknown
        return self.__class__(self._value.__rfloordiv__(other), precision=self._precision)

    def __rmod__(self, other):  # real signature unknown
        return self.__class__(self._value.__rmod__(other), precision=self._precision)

    def __rmul__(self, other):  # real signature unknown
        return self.__class__(self._value.__rmul__(other), precision=self._precision)

    def __rpow__(self, other):  # real signature unknown
        return self.__class__(self._value.__rpow__(other), precision=self._precision)

    def __rsub__(self, other):  # real signature unknown
        return self.__class__(self._value.__rsub__(other), precision=self._precision)

    def __rtruediv__(self, other):  # real signature unknown
        return self.__class__(self._value.__rtruediv__(other), precision=self._precision)

    def __rxor__(self, other):  # real signature unknown
        return self.__class__(self._value.__rxor__(other), precision=self._precision)

    def __sub__(self, other):
        return self.__class__(self._value.__sub__(other), precision=self._precision)

    def __truediv__(self, other):
        return self.__class__(self._value.__truediv__(other), precision=self._precision)

    def __xor__(self, other):
        return self.__class__(self._value.__xor__(other), precision=self._precision)


def unit_test():
    f0 = float_(10.23456, 50)
    f1 = float_(20.588, 50)

    print(f0)
    print(f1)

    print(divmod(f0, f1))

    print(1.25 + f0)
    print(1.25 - f0)
    print(1.25 * f0)
    print(1.25 ** f0)
    print(1.25 / f0)
    print(1.25 // f0)
    print(1.25 % f0)

    print(f1 + 2.45)
    print(f1 - 2.45)
    print(f1 * 2.45)
    print(f1 ** 2.45)
    print(f1 / 2.45)
    print(f1 // 2.45)
    print(f1 % 2.45)

    print(f1 + f0)
    print(f1 - f0)
    print(f1 * f0)
    print(f1 ** f0)
    print(f1 / f0)
    print(f1 // f0)
    print(f1 % f0)


if __name__ == '__main__':
    unit_test()
