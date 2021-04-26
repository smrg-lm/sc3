
import unittest

import sc3
sc3.init()

from sc3.base.main import main
from sc3.base.netaddr import NetAddr
from sc3.base.responsedefs import OscFunc


class BundleTestCase(unittest.TestCase):
    def test_sc3_special_cases(self):
        oscaddr = '/msg'
        test_message = [
            oscaddr,
            None,  # int(0)
            True,  # int(1)
            False,  # int(0)
            [],  # int(0)
            ['/msg'],  # blob
            [None, ['/msg']],  # blob
            '[', 0.75, 'string', 1, [], ['/msg'], ']',  # array
        ]
        expected_value = [
            oscaddr, 0, 1, 0, 0,
            b'/msg\x00\x00\x00\x00,\x00\x00\x00',
            b'#bundle\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00'
            b'\x00\x00\x0c/msg\x00\x00\x00\x00,\x00\x00\x00',
            [0.75, 'string', 1, 0, b'/msg\x00\x00\x00\x00,\x00\x00\x00'],
        ]
        result = None

        def func(msg):
            nonlocal result
            result = msg
            main.resume()

        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        o = OscFunc(func, oscaddr)
        n.send_msg(*test_message)
        main.wait()

        for i, (r, v) in enumerate(zip(result, expected_value)):
            with self.subTest(position=i):
                self.assertEqual(type(r), type(v))
                self.assertEqual(r, v)

    def test_calc_dgram_size(self):
        test_data = [0, ['/m1', 0.5], [1, ['/m2', 1]], ['/m3', 'string']]
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        self.assertEqual(
            n._calc_bndl_dgram_size(test_data[1:]),
            len(n._osc_interface._build_bundle(test_data).dgram))

    def test_max_dgram_size(self):
        # Just send or not by now, scsynth can handle it, python-osc can't.
        oscaddr = '/'
        n = NetAddr('127.0.0.1', 57110)  # NetAddr.lang_port())

        try:
            test_data = [
                oscaddr, 'x' * (NetAddr._MAX_UDP_DGRAM_SIZE - 12)]
            assert n._calc_msg_dgram_size(test_data) == 65504
            n.send_msg(*test_data)
        except OSError as e:
            # Should not throw any error.
            self.assertTrue(False)

        try:
            test_data = [
                oscaddr, 'x' * (NetAddr._MAX_UDP_DGRAM_SIZE - 8)]
            assert n._calc_msg_dgram_size(test_data) == 65508
            n.send_msg(*test_data)
        except OSError as e:
            import errno
            self.assertEqual(e.errno, errno.EMSGSIZE)

    def test_nested_bundle_time(self):
        # ValueError('nested bundle time must be >= enclosing bundle time').
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(1, ['/msg', 1], [0.5, ['/msg', 2]]), n);
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(0, ['/msg', 1], [None, ['/msg', 2]]), n);


if __name__ == '__main__':
    unittest.main()
