
import unittest
import operator

import sc3
import sc3.base.builtins as bi
from sc3.base.functions import (
    Function, function, UnaryOpFunction, BinaryOpFunction, NAryOpFunction)

sc3.init()


class FunctionTestCase(unittest.TestCase):
    def test_unop(self):
        @function
        def f1():
            return 2

        self.assertIs(type(f1), Function)
        self.assertEqual(f1(), 2)
        f = -f1
        self.assertIs(type(f), UnaryOpFunction)
        self.assertIs(f.a, f1)
        self.assertIs(f.selector, operator.neg)
        self.assertEqual(f(), -2)
        f = +f1
        self.assertIs(type(f), UnaryOpFunction)
        self.assertIs(f.a, f1)
        self.assertIs(f.selector, operator.pos)
        self.assertEqual(f(), 2)
        f = abs(-f1)
        self.assertIs(type(f), UnaryOpFunction)
        self.assertIs(type(f.a), UnaryOpFunction)
        self.assertIs(f.a.a, f1)
        self.assertIs(f.selector, operator.abs)
        self.assertEqual(f(), 2)
        f = ~f1
        self.assertIs(type(f), UnaryOpFunction)
        self.assertIs(f.a, f1)
        self.assertIs(f.selector, operator.invert)
        self.assertEqual(f(), ~2)

        # builtins

        res = f1()
        unops = ['log', 'log2', 'log10', 'exp', 'sin', 'cos', 'tan', 'asin',
                 'acos', 'atan', 'sinh', 'cosh', 'tanh']
        for op in unops:
            with self.subTest(op=op):
                f = getattr(f1, op)()
                try:
                    self.assertIs(type(f), UnaryOpFunction)
                    self.assertIs(f.a, f1)
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

    def test_binop(self):
        @function
        def f1():
            return 2

        @function
        def f2():
            return 10

        def assert_type_ab_selector(f, a, b, selector):
            self.assertIs(type(f), BinaryOpFunction)
            self.assertEqual(f.a, a)
            self.assertEqual(f.b, b)
            self.assertEqual(f.selector, selector)

        self.assertEqual(f1(), 2)
        self.assertEqual(f2(), 10)
        f = f1 + f2
        assert_type_ab_selector(f, f1, f2, operator.add)
        self.assertEqual(f(), f1() + f2())
        f = f1 + 10
        assert_type_ab_selector(f, f1, 10, operator.add)
        self.assertEqual(f(), f1() + 10)
        f = 2 + f2
        assert_type_ab_selector(f, 2, f2, operator.add)
        self.assertEqual(f(), 2 + f2())
        f = f1 - f2
        assert_type_ab_selector(f, f1, f2, operator.sub)
        self.assertEqual(f(), f1() - f2())
        f = f1 - 10
        assert_type_ab_selector(f, f1, 10, operator.sub)
        self.assertEqual(f(), f1() - 10)
        f = 2 - f2
        assert_type_ab_selector(f, 2, f2, operator.sub)
        self.assertEqual(f(), 2 - f2())
        f = f1 * f2
        assert_type_ab_selector(f, f1, f2, operator.mul)
        self.assertEqual(f(), f1() * f2())
        f = f1 * 10
        assert_type_ab_selector(f, f1, 10, operator.mul)
        self.assertEqual(f(), f1() * 10)
        f = 2 * f2
        assert_type_ab_selector(f, 2, f2, operator.mul)
        self.assertEqual(f(), 2 * f2())
        f = f1 / f2
        assert_type_ab_selector(f, f1, f2, operator.truediv)
        self.assertEqual(f(), f1() / f2())
        f = f1 / 10
        assert_type_ab_selector(f, f1, 10, operator.truediv)
        self.assertEqual(f(), f1() / 10)
        f = 2 / f2
        assert_type_ab_selector(f, 2, f2, operator.truediv)
        self.assertEqual(f(), 2 / f2())
        f = f1 // f2
        assert_type_ab_selector(f, f1, f2, operator.floordiv)
        self.assertEqual(f(), f1() // f2())
        f = f1 // 10
        assert_type_ab_selector(f, f1, 10, operator.floordiv)
        self.assertEqual(f(), f1() // 10)
        f = 2 // f2
        assert_type_ab_selector(f, 2, f2, operator.floordiv)
        self.assertEqual(f(), 2 // f2())

        f = f1 % f2
        assert_type_ab_selector(f, f1, f2, bi.mod)
        self.assertEqual(f(), f1() % f2())
        f = f1 % 10
        assert_type_ab_selector(f, f1, 10, bi.mod)
        self.assertEqual(f(), f1() % 10)
        f = 2 % f2
        assert_type_ab_selector(f, 2, f2, bi.mod)
        self.assertEqual(f(), 2 % f2())

    def test_narop(self):
        ...

    def test_args(self):
        @function
        def f1(a=1):
            return a

        @function
        def f2(b=2):
            return b

        @function
        def f3(c=3):
            return c

        @function
        def f4():
            return 100

        self.assertEqual(f1(), 1)
        self.assertEqual(f2(), 2)
        self.assertEqual(f3(), 3)
        self.assertEqual(f4(), 100)

        f123 = f1 + f2 + f3
        # *args are for all functions.
        self.assertEqual(f123(10), 30)
        # Remaining *args are ignored.
        self.assertEqual(f123(10, 100, 1000), 30)
        # **kwargs are selective.
        self.assertEqual(f123(a=10), 15)
        self.assertEqual(f123(b=10), 14)
        self.assertEqual(f123(c=10), 13)
        self.assertEqual(f123(a=10, b=10), 23)
        self.assertEqual(f123(a=10, c=10), 22)
        self.assertEqual(f123(b=10, c=10), 21)
        self.assertEqual(f123(xxx=10), 6)
        # *args cannot be overridden as in normal functions.
        err_msg = "f2\(\) got multiple values for argument 'b'"
        self.assertRaisesRegex(TypeError, err_msg, f123, 10, b=2)

        f1234 = f123 + f4
        # No arguments signature ignores parameters.
        self.assertEqual(f1234(), 106)
        self.assertEqual(f1234(10), 130)
        self.assertEqual(f1234(a=11, b=12, c=13), 136)
        f4123 = f4 + f123
        self.assertEqual(f4123(), 106)
        self.assertEqual(f4123(10), 130)
        self.assertEqual(f4123(a=11, b=12, c=13), 136)
        # *args cannot be overridden, just another path.
        err_msg = "f3\(\) got multiple values for argument 'c'"
        self.assertRaisesRegex(TypeError, err_msg, f4123, 10, 100, 1000, c=3)


if __name__ == '__main__':
    unittest.main()
