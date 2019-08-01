
import unittest

import sc3.builtins as bi
from sc3.functions import (Function, function, UnaryOpFunction,
                           BinaryOpFunction, NAryOpFunction)


class FunctionTestCase(unittest.TestCase):
    def test_unop(self):
        @function
        def f1():
            return 2

        self.assertEqual(f1(), 2)
        f = -f1
        self.assertEqual(f.selector, 'neg')
        self.assertEqual(f(), -2)
        f = +f1
        self.assertEqual(f.selector, 'pos')
        self.assertEqual(f(), 2)
        f = abs(-f1)
        self.assertEqual(f.selector, 'abs')
        self.assertEqual(f(), 2)
        f = ~f1
        self.assertEqual(f.selector, 'invert')
        self.assertEqual(f(), ~2)

        # builtins

        res = f1()
        unops = ['log', 'log2', 'log10', 'exp', 'sin', 'cos', 'tan', 'asin',
                 'acos', 'atan', 'sinh', 'cosh', 'tanh']
        for op in unops:
            f = getattr(f1, op)()
            try:
                self.assertEqual(f.selector, getattr(bi, op))
                self.assertEqual(f(), getattr(bi, op)(res))
            except ValueError as e:
                self.assertEqual(e.args[0], 'math domain error')
                self.assertTrue(op in {'asin', 'acos', 'atan'})

        unops = ['midicps', 'cpsmidi', 'midiratio', 'ratiomidi', 'octcps',
                 'cpsoct', 'ampdb', 'dbamp', 'squared', 'cubed', 'sqrt']
        for op in unops:
            f = getattr(f1, op)()
            self.assertEqual(f.selector, getattr(bi, op))
            self.assertEqual(f(), getattr(bi, op)(res))

        # etc., ... other types of tests for all this?

    def test_binop(self):
        @function
        def f1():
            return 2

        @function
        def f2():
            return 10

        self.assertEqual(f1(), 2)
        self.assertEqual(f2(), 10)
        f = f1 + f2
        self.assertEqual(f(), f1() + f2())
        f = f1 + 10
        self.assertEqual(f(), f1() + 10)
        f = 2 + f2
        self.assertEqual(f(), 2 + f2())
        f = f1 - f2
        self.assertEqual(f(), f1() - f2())
        f = f1 - 10
        self.assertEqual(f(), f1() - 10)
        f = 2 - f2
        self.assertEqual(f(), 2 - f2())
        f = f1 * f2
        self.assertEqual(f(), f1() * f2())
        f = f1 * 10
        self.assertEqual(f(), f1() * 10)
        f = 2 * f2
        self.assertEqual(f(), 2 * f2())
        f = f1 / f2
        self.assertEqual(f(), f1() / f2())
        f = f1 / 10
        self.assertEqual(f(), f1() / 10)
        f = 2 / f2
        self.assertEqual(f(), 2 / f2())
        f = f1 // f2
        self.assertEqual(f(), f1() // f2())
        f = f1 // 10
        self.assertEqual(f(), f1() // 10)
        f = 2 // f2
        self.assertEqual(f(), 2 // f2())

        # etc., ... other types of tests for all this?

    def test_narop(self):
        ...

    def test_args(self):
        ...


if __name__ == '__main__':
    unittest.main()
