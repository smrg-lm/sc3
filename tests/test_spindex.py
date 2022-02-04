
import unittest

import sc3
sc3.init()

from sc3.synth.ugen import SynthObject
from sc3.synth.synthdef import SynthDef
from sc3.synth.ugens.inout import Out
from sc3.synth.ugens.foscillators import Saw


def list_ugen_cmds(sd):
    ret = []
    for ugen in sd._children:
        inputs = None
        if ugen.inputs is not None:
            inputs = [
                x._dump_name() if isinstance(x, SynthObject)
                else x for x in ugen.inputs]
        ret.append([ugen._dump_name(), ugen.rate, inputs])
    return ret


# TODO: Actually send to a running server, maybe.


class SpIndexTestCase(unittest.TestCase):
    '''Test AbstractObject interface related to special index opcodes.'''

    def test_unary(self):
        params = [
            ('neg', '1_neg'), ('not_', '1_not'), ('bitnot', '1_bitNot'),
            ('abs', '1_abs'), ('as_int', '1_asInteger'),
            ('as_float', '1_asFloat'), ('ceil', '1_ceil'),
            ('floor', '1_floor'), ('frac', '1_frac'), ('sign', '1_sign'),
            ('squared', '1_squared'), ('cubed', '1_cubed'), ('sqrt', '1_sqrt'),
            ('exp', '1_exp'), ('reciprocal', '1_reciprocal'),
            ('midicps', '1_midicps'), ('cpsmidi', '1_cpsmidi'),
            ('midiratio', '1_midiratio'), ('ratiomidi', '1_ratiomidi'),
            ('dbamp', '1_dbamp'), ('ampdb', '1_ampdb'), ('octcps', '1_octcps'),
            ('cpsoct', '1_cpsoct'), ('log', '1_log'), ('log2', '1_log2'),
            ('log10', '1_log10'), ('sin', '1_sin'), ('cos', '1_cos'),
            ('tan', '1_tan'), ('asin', '1_asin'), ('acos', '1_acos'),
            ('atan', '1_atan'), ('sinh', '1_sinh'), ('cosh', '1_cosh'),
            ('tanh', '1_tanh'), ('rand', '1_rand'), ('rand2', '1_rand2'),
            ('linrand', '1_linrand'), ('bilinrand', '1_bilinrand'),
            ('sum3rand', '1_sum3rand'), ('distort', '1_distort'),
            ('softclip', '1_softclip'), ('coin', '1_coin'),
            ('rectwindow', '1_rectWindow'), ('hanwindow', '1_hanWindow'),
            ('welwindow', '1_welWindow'), ('triwindow', '1_triWindow'),
            ('ramp', '1_ramp'), ('scurve', '1_scurve')
        ]

        # 'isNil', 'notNil' are not accessible as opcode.
        # `not UGen()` is not implementable syntax in Python.
        # 'digitValue', 'silence', 'thru' are not accessible as opcode.

        for name1, name2 in params:
            def test(): Out.ar(0, getattr(Saw(), name1)())
            sd = SynthDef('test', test)
            result = list_ugen_cmds(sd)
            self.assertEqual(result[1][0], name2)

        # Alternative syntaxes.

        def test(): Out.ar(0, ~Saw())
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_bitNot')

        def test(): Out.ar(0, abs(Saw()))
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_abs')


    def test_binary(self):
        params = [
            ('__add__', '1_+'), ('__sub__', '1_-'), ('__mul__', '1_*'),
            ('__floordiv__', '1_div'), ('__truediv__', '1_/'),
            ('__mod__', '1_mod'),
            # ('', '1_=='), ('', '1_!='),  # TODO: Unused in sclang.
            ('__lt__', '1_<'),
            ('__gt__', '1_>'), ('__le__', '1_<='), ('__ge__', '1_>='),
            ('min', '1_min'), ('max', '1_max'), ('bitand', '1_bitAnd'),
            ('bitor', '1_bitOr'), ('bitxor', '1_bitXor'), ('lcm', '1_lcm'),
            ('gcd', '1_gcd'), ('round', '1_round'), ('roundup', '1_roundUp'),
            ('trunc', '1_trunc'), ('atan2', '1_atan2'), ('hypot', '1_hypot'),
            ('hypotx', '1_hypotApx'), ('pow', '1_pow'),
            ('lshift', '1_leftShift'), ('rshift', '1_rightShift'),
            ('urshift', '1_unsignedRightShift'), # ('fill', '1_fill'),  # TODO: Unused in sclang.
            ('ring1', '1_ring1'), ('ring2', '1_ring2'), ('ring3', '1_ring3'),
            ('ring4', '1_ring4'), ('difsqr', '1_difsqr'),
            ('sumsqr', '1_sumsqr'), ('sqrsum', '1_sqrsum'),
            ('sqrdif', '1_sqrdif'), ('absdif', '1_absdif'),
            ('thresh', '1_thresh'), ('amclip', '1_amclip'),
            ('scaleneg', '1_scaleneg'), ('clip2', '1_clip2'),
            ('excess', '1_excess'), ('fold2', '1_fold2'),
            ('wrap2', '1_wrap2'), ('first_arg', '1_firstArg'),
            ('rrand', '1_rrand'), ('exprand', '1_exprand')
        ]

        for name1, name2 in params:
            def test(): sig = Saw(); Out.ar(0, getattr(sig, name1)(sig))
            sd = SynthDef('test', test)
            result = list_ugen_cmds(sd)
            self.assertEqual(result[1][0], name2)

        # Alternative syntaxes.

        def test(): sig = Saw(); Out.ar(0, sig + sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_+')

        def test(): sig = Saw(); Out.ar(0, sig - sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_-')

        def test(): sig = Saw(); Out.ar(0, sig * sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_*')

        def test(): sig = Saw(); Out.ar(0, sig / sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_/')

        def test(): sig = Saw(); Out.ar(0, sig % sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_mod')

        def test(): sig = Saw(); Out.ar(0, sig < sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_<')

        def test(): sig = Saw(); Out.ar(0, sig > sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_>')

        def test(): sig = Saw(); Out.ar(0, sig <= sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_<=')

        def test(): sig = Saw(); Out.ar(0, sig >= sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_>=')

        def test(): sig = Saw(); Out.ar(0, sig & sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_bitAnd')

        def test(): sig = Saw(); Out.ar(0, sig | sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_bitOr')

        def test(): sig = Saw(); Out.ar(0, sig ^ sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_bitXor')

        def test(): sig = Saw(); Out.ar(0, sig ** sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_pow')

        def test(): sig = Saw(); Out.ar(0, sig << sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_leftShift')

        def test(): sig = Saw(); Out.ar(0, sig >> sig)
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_rightShift')


if __name__ == '__main__':
    unittest.main()
