from __future__ import annotations

import json
import math
import sys
import typing

TICK_SIZE = 100

if sys.version_info.minor >= 9:
    def lcm(a: int, b: int):
        return math.lcm(a, b)
else:
    def lcm(a: int, b: int):
        return int(a * b / math.gcd(a, b))


class FinanceDecimal(object):
    def __init__(self, value: float | int | None, /, k: int = None, tick_size: int = None):

        if tick_size is None:
            self.__tick_size = TICK_SIZE
        elif isinstance(tick_size, int):
            self.__tick_size = tick_size
        else:
            raise TypeError(f'tick_size of {self.__class__.__name__} must be integer')

        if value is None:
            if isinstance(k, int):
                self.__num = k
            else:
                raise TypeError(f'k of {self.__class__.__name__} must be integer')
        elif isinstance(value, (int, float)):
            self.__num = round(value * self.tick_size)
        else:
            raise TypeError(f'value of {self.__class__.__name__} must be float or integer')

    @classmethod
    def composite(cls, k: int, tick_size: int) -> FinanceDecimal:
        return cls(None, k=k, tick_size=tick_size)

    @classmethod
    def parse(cls, s: str) -> FinanceDecimal:
        _int_str, _res_str = s.split('.')
        _int_part = int(_int_str)
        _res_part = int(_res_str)

        i = len(_res_str)
        tick_size = 10 ** i
        k = _int_part * tick_size + _res_part
        r = cls(None, k=k, tick_size=tick_size)
        return r

    def __hash__(self):
        raise NotImplementedError(f'{self.__class__.__name__} cannot be hashed')

    def __float__(self) -> float:
        return self.value

    def __bool__(self) -> bool:
        return self.__num.__bool__()

    def __str__(self) -> str:
        return self.to_json(fmt='compact')

    def __repr__(self):
        return f'<{self.__class__.__name__}, k={self.__num}, tick={self.__tick_size}>'

    def to_tuple(self) -> tuple:
        return self.__num, self.__tick_size

    def to_json(self, fmt='str', **kwargs) -> str | tuple | dict:
        if fmt == 'compact':
            if self.k <= 1:
                return f'{round(self.value)}'

            i = math.ceil(math.log(self.__tick_size, 10))
            r = self.__num.__divmod__(self.__tick_size)

            return f'{r[0]}.{round(r[1] * (10 ** i) / self.__tick_size)}'
        elif fmt == 'dict':
            return dict(k=self.__num, tick_size=self.__tick_size)
        elif fmt == 'tuple':
            return self.to_tuple()
        else:
            return f'{{"k": {self.__num}, "tick_size": {self.__tick_size}}}'

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> FinanceDecimal:
        if isinstance(json_message, dict):
            r = cls(None, k=json_message['k'], tick_size=json_message['tick_size'])
        elif isinstance(json_message, tuple):
            r = cls(None, k=json_message[0], tick_size=json_message[1])
        elif isinstance(json_message, (str, bytes, bytearray)):
            if json_message.startswith('{') and json_message.endswith('}'):
                d = json.loads(json_message)
                r = cls(None, k=d['k'], tick_size=d['tick_size'])
            else:
                r = cls.parse(json_message)
        else:
            raise TypeError(f'Invalid type {type(json_message)} for {cls.__name__}.from_json')

        return r

    @typing.overload
    def __add__(self, other: float | int) -> float:
        ...

    @typing.overload
    def __add__(self, other: FinanceDecimal) -> FinanceDecimal:
        ...

    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.decimal_add(other)
        else:
            return self.__float__() + other

    @typing.overload
    def __sub__(self, other: float | int) -> float:
        ...

    @typing.overload
    def __sub__(self, other: FinanceDecimal) -> FinanceDecimal:
        ...

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return self.decimal_sub(other)
        else:
            return self.__float__() - other

    @typing.overload
    def __mul__(self, other: float | int) -> float:
        ...

    @typing.overload
    def __mul__(self, other: FinanceDecimal) -> FinanceDecimal:
        ...

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return self.decimal_mul(other)
        else:
            return self.__float__() * other

    @typing.overload
    def __truediv__(self, other: float | int) -> float:
        ...

    @typing.overload
    def __truediv__(self, other: FinanceDecimal) -> FinanceDecimal:
        ...

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.decimal_div(other)
        else:
            return self.__float__() / other

    def decimal_add(self, b: FinanceDecimal | float | int, tick_size: int = None) -> FinanceDecimal:
        if isinstance(b, (float, int)):
            if tick_size is None:
                tick_size = self.tick_size

            k_a = round(self.k * tick_size / self.tick_size)
            r = self.composite(k=round(k_a + b * tick_size), tick_size=tick_size)
        elif isinstance(b, FinanceDecimal):
            if tick_size is None:
                tick_size = lcm(self.tick_size, b.tick_size)

            k_a = round(self.k * tick_size / self.tick_size)
            k_b = round(b.k * tick_size / b.tick_size)
            r = self.composite(k=k_a + k_b, tick_size=tick_size)
        else:
            raise TypeError(f'{self.__class__.__name__} can not add with {type(b)}')

        return r

    def decimal_sub(self, b: FinanceDecimal | float | int, tick_size: int = None) -> FinanceDecimal:
        if isinstance(b, (float, int)):
            if tick_size is None:
                tick_size = self.tick_size

            k_a = round(self.k * tick_size / self.tick_size)
            r = self.composite(k=round(k_a - b * tick_size), tick_size=tick_size)
        elif isinstance(b, FinanceDecimal):
            if tick_size is None:
                tick_size = lcm(self.tick_size, b.tick_size)

            k_a = round(self.k * tick_size / self.tick_size)
            k_b = round(b.k * tick_size / b.tick_size)
            r = self.composite(k=k_a - k_b, tick_size=tick_size)
        else:
            raise TypeError(f'{self.__class__.__name__} can not sub with {type(b)}')

        return r

    def decimal_div(self, b: FinanceDecimal | float | int, tick_size: int = None) -> FinanceDecimal:
        if tick_size is None:
            r = self.composite(k=round(self.k / float(b)), tick_size=self.tick_size)
        else:
            k_a = round(self.k * tick_size / self.tick_size)
            r = self.composite(k=round(k_a / float(b)), tick_size=tick_size)

        return r

    def decimal_mul(self, b: FinanceDecimal | float | int, tick_size: int = None) -> FinanceDecimal:
        if tick_size is None:
            r = self.composite(k=round(self.k * float(b)), tick_size=self.tick_size)
        else:
            k_a = round(self.k * tick_size / self.tick_size)
            r = self.composite(k=round(k_a * float(b)), tick_size=tick_size)

        return r

    def __copy__(self):
        return self.composite(k=self.__num, tick_size=self.__tick_size)

    @property
    def value(self) -> float:
        return self.__num / self.tick_size

    @property
    def k(self) -> int:
        return self.__num

    @property
    def tick_size(self) -> int:
        return self.__tick_size

    @tick_size.setter
    def tick_size(self, tick_size: int):
        if isinstance(tick_size, int):
            raise TypeError(f'tick_size of {self.__class__.__name__} must be integer')

        multiplier = tick_size / self.__tick_size
        self.__num = round(self.__num * multiplier)
        self.__tick_size = tick_size
