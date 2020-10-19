
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

    def test_default_rate(self):
        ...

    def test_array_controls(self):
        ...

    def test_controls(self):  # test_rates
        ...

    def test_prepend_args(self):
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

    # test or remove store_once.
    # remove store_at.

    def test_decorator(self):
        ...


if __name__ == '__main__':
    unittest.main()
