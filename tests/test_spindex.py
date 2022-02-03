
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
            sd = SynthDef('neg', test)
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
        # params = [
        #     ('', ''), ('', ''), ('', ''), ('', ''), ('', ''),
        #     ('', ''), ('', ''), ('', ''), ('', ''), ('', ''), ('', ''),
        #     ('', ''), ('', ''), ('', ''), ('', ''), ('', ''), ('', ''),
        # ]

        def test(): Out.ar(0, Saw().round(0.1))
        sd = SynthDef('test', test)
        result = list_ugen_cmds(sd)
        self.assertEqual(result[1][0], '1_round')


# def test(): Out.ar(0, Saw().xxx())
# sd = SynthDef('test', test)
# result = list_ugen_cmds(sd)
# self.assertEqual(result[1][0], '1_xxx')


if __name__ == '__main__':
    unittest.main()
