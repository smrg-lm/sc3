
import unittest

import sc3
from sc3.synth.synthdef import SynthDef, synthdef
from sc3.synth.ugens.line import DC
from sc3.synth.ugens.inout import Out

sc3.init()


class SynthDefTestCase(unittest.TestCase):
    def test_build(self):
        def graph():
            Out.ar(0, DC.ar(0.5) * 1)

        sd = SynthDef('test', graph)
        self.assertEqual(sd.name, 'test')
        self.assertIs(sd.func, graph)
        self.assertEqual(sd.metadata, dict())
        self.assertEqual(sd.variants, dict())
        self.assertIsNone(sd.desc)

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
        ...

    def test_variants(self):
        ...

    def test_metadata(self):
        ...

    def test_add(self):
        ...

    def test_send(self):
        ...

    def test_store(self):
        ...

    def test_load(self):
        ...

    def test_wrap(self):
        ...

    def test_as_bytes(self):
        ...

    def test_decorator(self):
        ...


if __name__ == '__main__':
    unittest.main()
