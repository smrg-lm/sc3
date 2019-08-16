
import unittest

from sc3.ugen import UGen
from sc3.ugens.osc import Impulse
from sc3.ugens.infougens import BufSampleRate
from sc3.ugens.poll import Poll


class UGenTestCase(unittest.TestCase):
    def test_internal_interface(self):
        # _method_selector_for_rate
        self.assertEqual(Impulse._method_selector_for_rate('audio'), 'ar')
        self.assertEqual(Impulse._method_selector_for_rate('control'), 'kr')
        self.assertEqual(Poll._method_selector_for_rate('scalar'), 'new')
        self.assertEqual(BufSampleRate._method_selector_for_rate('scalar'), 'ir')
        self.assertRaises(AttributeError, Impulse._method_selector_for_rate, 'scalar')
        self.assertRaises(AttributeError, BufSampleRate._method_selector_for_rate, 'audio')

        # _arg_name_for_input_at
        ugen = Impulse.ar()
        for i, name in enumerate(['freq', 'phase', 'mul', 'add', None]):
            self.assertEqual(ugen._arg_name_for_input_at(i), name)



if __name__ == '__main__':
    unittest.main()
