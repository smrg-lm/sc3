
import operator
import math

from . import classlibrary as clb


clb.ClassLibrary.late_imports(__name__, ('sc3.base.builtins', 'bi'))


class AbstractObject():
    def _compose_unop(self, selector):
        raise NotImplementedError(
            f'{type(self).__name__} does not implement _compose_unop')

    def _compose_binop(self, selector, other):
        raise NotImplementedError(
            f'{type(self).__name__} does not implement _compose_binop')

    def _rcompose_binop(self, selector, other):
        raise NotImplementedError(
            f'{type(self).__name__} does not implement _rcompose_binop')

    def _compose_narop(self, selector, *args):
        raise NotImplementedError(
            f'{type(self).__name__} does not implement _compose_narop')


    # NOTE: If needed by subclasses, operations below, as a whole or in sets,
    # can be implemented as mixins. There are inconsistencies regarding
    # supported operations in specific UGen objects.


    ### Unary operators ###

    def __neg__(self):
        return self._compose_unop(operator.neg)  # -

    def __pos__(self):
        return self._compose_unop(operator.pos)  # + (not in _specialindex)

    def __abs__(self):
        return self._compose_unop(operator.abs)  # abs()

    def __invert__(self):
        return self._compose_unop(operator.invert)  # ~ (bitwise inverse)


    # # Python's numeric type conversion
    #
    # def __complex__(self):
    #     raise NotImplementedError()
    #
    # def __int__(self):
    #     raise NotImplementedError()
    #
    # def __float__(self):  # used by math.floor
    #     raise NotImplementedError()


    # # Python's builtin round and math trunc/floor/ceil.
    #
    # def __round__(self, ndigits=0):
    #     return self._compose_binop(round, ndigits)
    #
    # def __trunc__(self):
    #     return self._compose_unop(math.trunc)  # binary in sclang, possible si problem
    #
    # def __ceil__(self):
    #     return self._compose_unop(math.ceil)
    #
    # def __floor__(self):
    #     return self._compose_unop(math.floor)


    def reciprocal(self):
        return self._compose_unop(bi.reciprocal)

    def ceil(self):
        return self._compose_unop(bi.ceil)

    def floor(self):
        return self._compose_unop(bi.floor)

    def frac(self):
        return self._compose_unop(bi.frac)

    def sign(self):
        return self._compose_unop(bi.sign)

    def log(self):  #, base=math.e):  # In SI is unary, can't change the base.
        return self._compose_unop(bi.log)

    def log2(self):
        return self._compose_unop(bi.log2)

    def log10(self):
        return self._compose_unop(bi.log10)

    # def log1p(self):
    #     return self._compose_unop(bi.log1p)

    def exp(self):
        return self._compose_unop(bi.exp)

    def sin(self):
        return self._compose_unop(bi.sin)

    def cos(self):
        return self._compose_unop(bi.cos)

    def tan(self):
        return self._compose_unop(bi.tan)

    def asin(self):
        return self._compose_unop(bi.asin)

    def acos(self):
        return self._compose_unop(bi.acos)

    def atan(self):
        return self._compose_unop(bi.atan)

    def sinh(self):
        return self._compose_unop(bi.sinh)

    def cosh(self):
        return self._compose_unop(bi.cosh)

    def tanh(self):
        return self._compose_unop(bi.tanh)

    # def asinh(x):
    #     return self._compose_unop(bi.asinh)

    # def acosh(x):
    #     return self._compose_unop(bi.acosh)

    # def atanh(x):
    #     return self._compose_unop(bi.atanh)

    def midicps(self):
        return self._compose_unop(bi.midicps)

    def cpsmidi(self):
        return self._compose_unop(bi.cpsmidi)

    def midiratio(self):
        return self._compose_unop(bi.midiratio)

    def ratiomidi(self):
        return self._compose_unop(bi.ratiomidi)

    def octcps(self):
        return self._compose_unop(bi.octcps)

    def cpsoct(self):
        return self._compose_unop(bi.cpsoct)

    def ampdb(self):
        return self._compose_unop(bi.ampdb)

    def dbamp(self):
        return self._compose_unop(bi.dbamp)

    def squared(self):
        return self._compose_unop(bi.squared)

    def cubed(self):
        return self._compose_unop(bi.cubed)

    def sqrt(self):
        return self._compose_unop(bi.sqrt)

    def rand(self):
        return self._compose_unop(bi.rand)

    def rand2(self):
        return self._compose_unop(bi.rand2)

    def linrand(self):
        return self._compose_unop(bi.linrand)

    def bilinrand(self):
        return self._compose_unop(bi.bilinrand)

    def sum3rand(self):
        return self._compose_unop(bi.sum3rand)

    def coin(self):
        return self._compose_unop(bi.coin)

    def distort(self):
        return self._compose_unop(bi.distort)

    def softclip(self):
        return self._compose_unop(bi.softclip)

    # even
    # odd

    def rectwindow(self):
        return self._compose_unop(bi.rectwindow)

    def hanwindow(self):
        return self._compose_unop(bi.hanwindow)

    def welwindow(self):
        return self._compose_unop(bi.welwindow)

    def triwindow(self):
        return self._compose_unop(bi.triwindow)

    def scurve(self):
        return self._compose_unop(bi.scurve)

    def ramp(self):
        return self._compose_unop(bi.ramp)

    def degrad(self):
        return self._compose_unop(bi.degrad)

    def raddeg(self):
        return self._compose_unop(bi.raddeg)

    # isPositive
    # isNegative
    # isStrictlyPositive

    # complex and cartesian
    # rho
    # theta
    # rotate
    # dist


    ### Binary operators ###

    def __add__(self, other): # +
        return self._compose_binop(operator.add, other)

    def __radd__(self, other):
        return self._rcompose_binop(operator.add, other)

    def __sub__(self, other): # -
        return self._compose_binop(operator.sub, other)

    def __rsub__(self, other):
        return self._rcompose_binop(operator.sub, other)

    def __mul__(self, other): # *
        return self._compose_binop(operator.mul, other)

    def __rmul__(self, other):
        return self._rcompose_binop(operator.mul, other)

    # def __matmul__(self, other): # @
    #     return self._compose_binop(operator.matmul, other)

    # def __rmatmul__(self, other):
    #     return self._rcompose_binop(operator.matmul, other)

    def __truediv__(self, other): # /
        return self._compose_binop(operator.truediv, other)

    def __rtruediv__(self, other):
        return self._rcompose_binop(operator.truediv, other)

    def __floordiv__(self, other): # //
        return self._compose_binop(operator.floordiv, other)

    def __rfloordiv__(self, other):
        return self._rcompose_binop(operator.floordiv, other)

    def __mod__(self, other): # %
        return self._compose_binop(bi.mod, other)

    def __rmod__(self, other):
        return self._rcompose_binop(bi.mod, other)

    # def __divmod__(self, other): # divmod(), método integrado
    #     return self._compose_binop('divmod', other)

    # def __rdivmod__(self, other):
    #     return self._rcompose_binop('divmod', other)

    def __pow__(self, other): # pow(), **, object.__pow__(self, other[, modulo])
        return self._compose_binop(operator.pow, other)

    def __rpow__(self, other):
        return self._rcompose_binop(operator.pow, other)

    def __lshift__(self, other): # <<
        return self._compose_binop(operator.lshift, other)

    def __rlshift__(self, other):
        return self._rcompose_binop(operator.lshift, other)

    def __rshift__(self, other): # >>
        return self._compose_binop(operator.rshift, other)

    def __rrshift__(self, other):
        return self._rcompose_binop(operator.rshift, other)

    def __and__(self, other): # &
        return self._compose_binop(operator.and_, other)

    def __rand__(self, other):
        return self._rcompose_binop(operator.and_, other)

    def __xor__(self, other): # ^
        return self._compose_binop(operator.xor, other)

    def __rxor__(self, other):
        return self._rcompose_binop(operator.xor, other)

    def __or__(self, other): # |
        return self._compose_binop(operator.or_, other)

    def __ror__(self, other):
        return self._rcompose_binop(operator.or_, other)

    # bitHammingDistance  # _HammingDistance -> ./lang/LangPrimSource/PyrBitPrim.cpp

    def __lt__(self, other): # <
        return self._compose_binop(operator.lt, other)

    def __le__(self, other): # <=
        return self._compose_binop(operator.le, other)

    # def __eq__(self, other):  # == (used in ugen dispatch, performBinaryOpOnUGen -> Object.performBinaryOpOnSomething)
    #     return self._compose_binop(operator.eq, other)

    # def __ne__(self, other):  # != # (used in ugen dispatch, performBinaryOpOnUGen -> Object.performBinaryOpOnSomething)
    #     return self._compose_binop(operator.ne, other)

    def __gt__(self, other): # >
        return self._compose_binop(operator.gt, other)

    def __ge__(self, other): # >=
        return self._compose_binop(operator.ge, other)


    def min(self, other):
        return self._compose_binop(bi.min, other)

    def max(self, other=0):
        return self._compose_binop(bi.max, other)

    def lcm(self, other):
        return self._compose_binop(bi.lcm, other)

    def gcd(self, other):
        return self._compose_binop(bi.gcd, other)

    def round(self, other=1):
        return self._compose_binop(bi.round, other)

    def roundup(self, other=1):
        return self._compose_binop(bi.roundup, other)

    def trunc(self, other=1):
        return self._compose_binop(bi.trunc, other)

    def atan2(self, other):
        return self._compose_binop(bi.atan2, other)

    def hypot(self, other):
        return self._compose_binop(bi.hypot, other)

    def hypotx(self, other):
        return self._compose_binop(bi.hypotx, other)

    # def leftshift(self, other):
    #     return self._compose_binop(bi.leftshift, other)
    #
    # def rightshift(self, other):
    #     return self._compose_binop(bi.rightshift, other)
    #
    # def urightshift(self, other):
    #     return self._compose_binop(bi.urightshift, other)

    def ring1(self, other):
        return self._compose_binop(bi.ring1, other)

    def ring2(self, other):
        return self._compose_binop(bi.ring2, other)

    def ring3(self, other):
        return self._compose_binop(bi.ring3, other)

    def ring4(self, other):
        return self._compose_binop(bi.ring4, other)

    def difsqr(self, other):
        return self._compose_binop(bi.difsqr, other)

    def sumsqr(self, other):
        return self._compose_binop(bi.sumsqr, other)

    def sqrsum(self, other):
        return self._compose_binop(bi.sqrsum, other)

    def sqrdif(self, other):
        return self._compose_binop(bi.sqrdif, other)

    def absdif(self, other):
        return self._compose_binop(bi.absdif, other)

    def thresh(self, other):
        return self._compose_binop(bi.thresh, other)

    def amclip(self, other):
        return self._compose_binop(bi.amclip, other)

    def scaleneg(self, other):
        return self._compose_binop(bi.scaleneg, other)

    def clip2(self, other):
        return self._compose_binop(bi.clip2, other)

    def fold2(self, other):
        return self._compose_binop(bi.fold2, other)

    def wrap2(self, other):
        return self._compose_binop(bi.wrap2, other)

    def excess(self, other):
        return self._compose_binop(bi.excess, other)

    def first_arg(self, other):
        # firstArg -> _FirstArg -> SetRaw(a, slotRawObject(a));
        # // this is useful when two ugens need to be called, but only
        # // one of their outputs is needed. (Operators help file).
        return self._compose_binop(bi.first_arg, other)

    def rrand(self, other):
        return self._compose_binop(bi.rrand, other)

    def exprand(self, other):
        return self._compose_binop(bi.exprand, other)


    ### Nary operators ###

    def clip(self, lo, hi):
        return self._compose_narop(bi.clip, lo, hi)

    def wrap(self, lo, hi):
        return self._compose_narop(bi.wrap, lo, hi)

    def fold(self, lo, hi):
        return self._compose_narop(bi.fold, lo, hi)

    def blend(self, other, frac=0.5):
        return self._compose_narop(bi.blend, frac)

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._compose_narop(
            bi.linlin, inmin, inmax, outmin, outmax, clip)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._compose_narop(
            bi.linexp, inmin, inmax, outmin, outmax, clip)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._compose_narop(
            bi.explin, inmin, inmax, outmin, outmax, clip)

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._compose_narop(
            bi.expexp, inmin, inmax, outmin, outmax, clip)

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._compose_narop(
            bi.lincurve, inmin, inmax, outmin, outmax, curve, clip)

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._compose_narop(
            bi.curvelin, inmin, inmax, outmin, outmax, curve, clip)

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._compose_narop(
            bi.bilin, incenter, inmin, inmax, outcenter, outmin, outmax, clip)

    def biexp(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._compose_narop(
            bi.biexp, incenter, inmin, inmax, outcenter, outmin, outmax, clip)

    def moddif(self, other, mod=1.0):
        return self._compose_narop(bi.moddif, other, mod)

    # degreeToKey
