from __future__ import annotations
import PyQuantKit

import unittest


class FinanceDecimalTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        PyQuantKit._FinanceDecimal.TICK_SIZE = 100
        super().__init__(*args, **kwargs)

    def test_init_decimal(self):
        a = PyQuantKit.FinanceDecimal(3.14159)
        self.assertEqual((a.k, a.tick_size), (314, 100), 'fast init error')

        b = PyQuantKit.FinanceDecimal(None, k=1798, tick_size=14)
        self.assertEqual((b.k, b.tick_size), (1798, 14), 'kwarg init error')

    def test_float_operator(self):
        a = PyQuantKit.FinanceDecimal(3.14159)

        self.assertAlmostEqual(a + 13, 1614 / 100, 6, 'float add error')
        self.assertAlmostEqual(a - 2.5, 64 / 100, 6, 'float sub error')
        self.assertEqual(a * 1.3, 3.14 * 1.3, 'float mul error')
        self.assertEqual(a / 0.42, 3.14 / 0.42, 'float div error')

    def test_decimal_operator(self):
        a = PyQuantKit.FinanceDecimal(3.14159)

        b = a.decimal_add(13)
        self.assertEqual((b.k, b.tick_size), (1614, 100), 'decimal add error')

        b = a.decimal_add(PyQuantKit.FinanceDecimal(None, k=130, tick_size=10))
        self.assertEqual((b.k, b.tick_size), (1614, 100), 'decimal add error')

        b = a.decimal_sub(2.5)
        self.assertEqual((b.k, b.tick_size), (64, 100), 'decimal sub error')

        b = a.decimal_sub(PyQuantKit.FinanceDecimal(None, k=25, tick_size=10))
        self.assertEqual((b.k, b.tick_size), (64, 100), 'decimal sub error')

        b = a.decimal_mul(1.3)
        self.assertEqual((b.k, b.tick_size), (408, 100), 'decimal mul error')

        b = a.decimal_mul(PyQuantKit.FinanceDecimal(None, k=13, tick_size=10))
        self.assertEqual((b.k, b.tick_size), (408, 100), 'decimal mul error')

        b = a.decimal_div(0.42)
        self.assertEqual((b.k, b.tick_size), (748, 100), 'decimal div error')

        b = a.decimal_div(PyQuantKit.FinanceDecimal(None, k=42, tick_size=100))
        self.assertEqual((b.k, b.tick_size), (748, 100), 'decimal div error')

    def test_serialization(self):
        a = PyQuantKit.FinanceDecimal(3.14159)

        self.assertEqual(f'{a}', '3.14', '__str__ failed')
        self.assertEqual(f'{a.__repr__()}', '<FinanceDecimal, k=314, tick=100>', "__repr__ failed")
        self.assertEqual(a.to_json(fmt="tuple"), (314, 100), "to_tuple failed")
        self.assertEqual(a.to_json(), '{"k": 314, "tick_size": 100}', "to_json failed")

        a = PyQuantKit.FinanceDecimal.from_json('{"k": 314, "tick_size": 100}')
        self.assertEqual((a.k, a.tick_size), (314, 100), "from_json failed")

        a = PyQuantKit.FinanceDecimal.from_json('13.902')
        self.assertEqual((a.k, a.tick_size), (13902, 1000), "from_json failed")


if __name__ == '__main__':
    unittest.main()
