
import unittest

import sc3
sc3.init()

from sc3.synth.synthdef import SynthDef, synthdef, _logger
from sc3.synth.ugens.line import DC
from sc3.synth.ugens.inout import Out
from sc3.synth.spec import spec
from sc3.synth.synthdesc import MdPlugin
from sc3.base.platform import Platform


_logger.setLevel('ERROR')


class SynthDefTestCase(unittest.TestCase):
    def test_build(self):
        def graph():
            Out.ar(0, DC.ar(0.5) * 1)

        sd = SynthDef('test', graph)
        self.assertEqual(sd.name, 'test')
        self.assertIs(sd.func, graph)
        self.assertEqual(sd.metadata, dict())
        self.assertEqual(sd.variants, dict())
        # self.assertIsNone(sd.desc)

        # Content, maybe goes in a test_synthdesc.py file
        # and/or test_synthdef_optimizations.py.
        self.assertEqual(sd._constants, {0.5: 0, 0.0: 1})
        ugen_set = {DC, Out}
        for u in sd._children:
            self.assertTrue(type(u) in ugen_set)

    def test_rate_annot(self):
        # Annotations

        def allin(a:'ir', b:'ar', c:'kr', d:'tr',
                  f:'ir', g:'kr', h:'ar', i:'tr'):
             Out(0,  DC() / a / b / c / d / f / g / h / i)

        sd = SynthDef('test', allin)

        controls = [
            ('Control', 'scalar'), ('TrigControl', 'control'),
            ('AudioControl', 'audio'), ('Control', 'control')]

        for c, (name, rate) in zip(sd._children[:4], controls):
            self.assertEqual(c.name, name)
            self.assertEqual(c.rate, rate)
            # TODO: check index.

        # Argument rate and override.

        rates = {
            'ar': ['AudioControl', 'audio', True],
            'kr': ['Control', 'control', False],
            'ir': ['Control', 'scalar', True],
            'tr': ['TrigControl', 'control', True]}

        keys = rates.keys()

        for r in keys:
            exec(f"def {r}(a:'{r}'): Out(0, DC() * a)\n")
            for o in keys ^ [r]:
                exec(
                    f"sd = SynthDef('test', {r}, ['{o}'])\n"
                    f"c = sd._children[0]\n"
                    f"self.assertEqual(c.name, rates['{o}'][0])\n"
                    f"self.assertEqual(c.rate, rates['{o}'][1])\n"
                    # f"print(c.name, c.rate, '{o}')\n"
                )

        for r in keys:
            exec(
                f"def {r}(a:'{r}'): Out(0, DC() * a)\n"
                f"sd = SynthDef('test', {r}, [0.8])\n"  # LagControl
                f"c = sd._children[0]\n"
                f"if rates['{r}'][2]:\n"
                f"    self.assertEqual(c.name, rates['{r}'][0])\n"
                f"    self.assertEqual(c.rate, rates['{r}'][1])\n"
                f"else:\n"
                f"    self.assertEqual(c.name, 'LagControl')\n"
                f"    self.assertEqual(c.rate, 'control')\n"
            )

        # Invalid cases.

        def wrong(a:0.8=0): Out(0, DC() * a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a:float=0): Out(0, DC() * a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a:['ar']=0): Out(0, DC() * a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a, *args): Out(0, DC() * a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a, **kwargs): Out(0, DC() * a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        # def ok(a=0): Out(0, DC() * a)
        # sd = SynthDef('test', ok, [['ar', 'kr', 'ir']])  # *** BUG: Creates LagControl(s).

    def test_array_controls(self):
        def ok(a=(0,)): Out(0, DC() * a)
        sd = SynthDef('test', ok)
        self.assertEqual(sd._all_control_names[0].index, 0)
        self.assertEqual(sd._all_control_names[0].rate, 'control')
        self.assertEqual(sd._all_control_names[0].default_value, [0])

        def ok(a=(0, 1)): Out(0, DC() * a)
        sd = SynthDef('test', ok)
        self.assertEqual(sd._all_control_names[0].index, 0)
        self.assertEqual(sd._all_control_names[0].rate, 'control')
        self.assertEqual(sd._all_control_names[0].default_value, [0, 1])

        def ok(a:'ar'=(2, 3)): Out(0, DC() * a)
        sd = SynthDef('test', ok)
        self.assertEqual(sd._all_control_names[0].index, 0)
        self.assertEqual(sd._all_control_names[0].rate, 'audio')
        self.assertEqual(sd._all_control_names[0].default_value, [2, 3])

        def ok(a:'ir'=(4, 5), b:'tr'=3, c:'kr'=(2, 1)): Out(0, DC() / a / b / c)
        sd = SynthDef('test', ok, ['ir', 0.9, [0.8, 0.7]])
        self.assertEqual(sd._all_control_names[0].index, 0)
        self.assertEqual(sd._all_control_names[0].rate, 'scalar')
        self.assertEqual(sd._all_control_names[0].default_value, [4, 5])
        self.assertEqual(sd._all_control_names[0].lag, 0.0)
        self.assertEqual(sd._all_control_names[1].index, 2)
        self.assertEqual(sd._all_control_names[1].rate, 'trigger')
        self.assertEqual(sd._all_control_names[1].default_value, 3)
        self.assertEqual(sd._all_control_names[1].lag, 0.0)  # Ignores 0.9.
        self.assertEqual(sd._all_control_names[2].index, 3)
        self.assertEqual(sd._all_control_names[2].rate, 'control')
        self.assertEqual(sd._all_control_names[2].default_value, [2, 1])
        self.assertEqual(sd._all_control_names[2].lag, [0.8, 0.7])

        # Check: sd = SynthDef('test', ok, ['ir', 0.9, [0.8, (0.7, 0.6)]])
        # Check: actual synthdef cmds.

        # Invalid cases.

        def wrong(a=(0, (1, 2))): Out(0, DC() / a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a=([1, 2], 0)): Out(0, DC() / a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

        def wrong(a=(0, {1, 2})): Out(0, DC() / a)
        self.assertRaises(ValueError, lambda: SynthDef('test', wrong))

    def test_prepend(self):
        ref_data0 = [[1, 2], [3, 4]]
        ref_data1 = 567

        def test(data0=None, data1:'ar'=None, off=10, amp=0.1):
            for i, d in enumerate(data0):
                self.assertEqual(d, ref_data0[i])
            self.assertEqual(data1, ref_data1)
            Out(0, DC() * amp + off)

        sd = SynthDef('test', test, prepend=[ref_data0, ref_data1])
        self.assertEqual(sd._all_control_names[0].name, 'off')
        self.assertEqual(sd._all_control_names[0].rate, 'control')
        self.assertEqual(sd._all_control_names[0].default_value, 10)
        self.assertEqual(sd._all_control_names[1].name, 'amp')
        self.assertEqual(sd._all_control_names[1].rate, 'control')
        self.assertEqual(sd._all_control_names[1].default_value, 0.1)

    def test_variants(self):
        def test(a:'ar', b:'ir', c):
            Out(0, DC() / a / b / c)

        variants = {
            'one': {'a': 1},
            'two': {'a': 1, 'c': 3},
            'three': {'a': 1, 'b': 2, 'c': 3}
        }

        sd = sd = SynthDef('test', test, variants=variants)
        self.assertEqual(sd._all_control_names[0].rate, 'audio')
        self.assertEqual(sd._all_control_names[0].default_value, 0.0)
        self.assertEqual(sd._all_control_names[1].rate, 'scalar')
        self.assertEqual(sd._all_control_names[1].default_value, 0.0)
        self.assertEqual(sd._all_control_names[2].rate, 'control')
        self.assertEqual(sd._all_control_names[2].default_value, 0.0)
        # TODO: With server: 'test', 'test.one', 'test.two', 'test.three'.

    def test_metadata(self):
        # Values of 'specs' dict must be ControlSpec objects.
        md = {
            'specs': {
                'a': spec('amp'),
                'c': spec('db')
            },
            'text': 'Test metadata 1.'
        }

        def test(a:'ar'=220, b=2, c=0.1): Out(0, DC() / a / b / c)
        sd = SynthDef('test', test, metadata=md)
        self.assertEqual(sd._all_control_names[0].rate, 'audio')
        self.assertEqual(sd._all_control_names[0].default_value, 220)
        self.assertEqual(sd._all_control_names[2].rate, 'control')
        self.assertEqual(sd._all_control_names[2].default_value, 0.1)

        sd.store(dir=Platform.tmp_dir)
        ds = MdPlugin().read_file(Platform.tmp_dir / 'test.scjsonmd')
        self.assertEqual(sd.metadata, ds)

        md = {
            'specs': {
                'a': spec('freq'),
                'c': spec('amp')
            },
            'text': 'Test metadata 2.'
        }

        def test(a:'ar'=None, b=None, c=0.1): Out(0, DC() / a / b / c)
        sd = SynthDef('test', test, metadata=md)
        self.assertEqual(sd._all_control_names[0].rate, 'audio')
        self.assertEqual(sd._all_control_names[0].default_value, 440)
        self.assertEqual(sd._all_control_names[2].rate, 'control')
        self.assertEqual(sd._all_control_names[2].default_value, 0.1)

        sd.store(dir=Platform.tmp_dir)
        ds = MdPlugin().read_file(Platform.tmp_dir / 'test.scjsonmd')
        self.assertEqual(sd.metadata, ds)

    # def test_wrap(self):
    #     ...

    # def test_as_bytes(self):
    #     ...

    def test_decorator(self):
        @synthdef
        def sd(a, b:'ar'):
            Out(0, DC() / a / b)

        unames = [
            'AudioControl', 'Control', 'DC',
            'BinaryOpUGen', 'BinaryOpUGen', 'Out']
        for item, name in zip(sd._children, unames):
            self.assertEqual(item.name, name)

        @synthdef(
            rates=[0.02, 0.02],
            variants={'low': {'freq': 110}}
        )
        def sd(a, b:'ir', c:'ar'):
            Out(0, DC() / a / b / c)

        self.assertEqual(sd._children[0].name, 'Control')
        self.assertEqual(sd._children[0].rate, 'scalar')
        self.assertEqual(sd._children[1].name, 'AudioControl')
        self.assertEqual(sd._children[1].rate, 'audio')
        self.assertEqual(sd._children[2].name, 'LagControl')
        self.assertEqual(sd._children[2].rate, 'control')

        self.assertEqual(sd._all_control_names[0].rate, 'control')
        self.assertEqual(sd._all_control_names[0].default_value, 0.0)
        self.assertEqual(sd._all_control_names[0].lag, 0.02)
        self.assertEqual(sd._all_control_names[1].rate, 'scalar')
        self.assertEqual(sd._all_control_names[1].default_value, 0.0)
        self.assertEqual(sd._all_control_names[1].lag, 0.0)
        self.assertEqual(sd._all_control_names[2].rate, 'audio')
        self.assertEqual(sd._all_control_names[2].default_value, 0.0)
        self.assertEqual(sd._all_control_names[2].lag, 0.0)

    # def test_optimize_graph(sef):
    #     ...  # To test empty synths.

    # def test_add(self):
    #     ...

    # def test_send(self):
    #     ...

    # def test_store(self):
    #     ...

    # def test_load(self):
    #     ...


if __name__ == '__main__':
    unittest.main()
