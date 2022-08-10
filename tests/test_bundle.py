
import unittest
from functools import partial
import math
import sys

import sc3
sc3.init()

from sc3.base.main import main
from sc3.base.netaddr import NetAddr
from sc3.base.responders import OscFunc
from sc3.base._osclib import OscPacket
from sc3.base.clock import SystemClock


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

        o.free()

    def test_calc_dgram_size(self):
        test_data = [0, ['/m1', 0.5], [1, ['/m2', 1]], ['/m3', 'string']]
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        self.assertEqual(
            n._calc_bndl_dgram_size(test_data[1:]),
            len(n._osc_interface._build_bundle(0, test_data).dgram))

    @unittest.skipIf(sys.platform.startswith('darwin'), "OSX's UDP packet size is known to be shorter")
    def test_max_dgram_size(self):
        oscaddr = '/'
        test_msg = [oscaddr, 'x' * (NetAddr._MAX_UDP_DGRAM_SIZE - 12)]
        result = None

        def func(msg):
            nonlocal result
            result = msg
            main.resume()

        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        o = OscFunc(func, oscaddr)

        assert n._calc_msg_dgram_size(test_msg) == 65504
        n.send_msg(*test_msg)
        main.wait()
        self.assertEqual(test_msg, result)

        try:
            test_data = [oscaddr, 'x' * (NetAddr._MAX_UDP_DGRAM_SIZE - 8)]
            assert n._calc_msg_dgram_size(test_data) == 65508
            n.send_msg(*test_data)
        except OSError as e:
            import errno
            self.assertEqual(e.errno, errno.EMSGSIZE)

        o.free()

    def test_nested_bundle_time(self):
        # ValueError('nested bundle time must be >= enclosing bundle time').
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(1, ['/msg', 1], [0.5, ['/msg', 2]]), n)
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(0, ['/msg', 1], [None, ['/msg', 2]]), n)

    def test_bndl_atomicity(self):
        n = NetAddr("127.0.0.1", NetAddr.lang_port());
        messages = ['/msg1', '/msg2', '/msg3', '/msg4']
        scrambled = ['/msg4', '/msg2', '/msg1', '/msg3']
        results = []
        funcs = []

        def func(path):
            results.append([path, main.elapsed_time()])
            main.resume()

        for p in scrambled:
            f = partial(func, p)
            funcs.append(OscFunc(f, p))

        n.send_bundle(0, *[[m] for m in messages]);
        main.wait(tasks=len(messages))

        # The order of evaluation should always be 1, 2, 3, 4.
        prev_time = 0
        for m, r in zip(messages, results):
            self.assertEqual(m, r[0])
            self.assertTrue(r[1] >= prev_time, f'{r[1]} >= {prev_time}')
            prev_time = r[1]

        for o in funcs:
            o.free()

    # FIXME: This shouldn't happen in Windows.
    @unittest.skipIf(sys.platform.startswith('win32'), "Windows fails the test, I can't check why")
    def test_bndl_msg_recv_time(self):
        n = NetAddr("127.0.0.1", NetAddr.lang_port());
        oscaddr = '/msg'
        result = None

        def func(*args):
            nonlocal result
            result = args[1] < main.elapsed_time()
            main.resume()

        o = OscFunc(func, oscaddr)

        lst = [
            # Bundle: with no latency should always be True because client
            # time (main.elapsed_time) is read twice, low level and within the
            # OscFunc, this is something to bear in mind.
            [lambda: n.send_bundle(0, [oscaddr]), True],
            [lambda: n.send_bundle(None, [oscaddr]), True],
            # Bundle: should always be False with enough latency
            # (network + processing).
            [lambda: n.send_bundle(1, [oscaddr]), False],
            # Message: should always be True due to processing time.
            [lambda: n.send_msg(oscaddr), True]
        ]

        for i, (lmbd, value) in enumerate(lst):
            with self.subTest(case=i):
                lmbd()
                main.wait()
                self.assertIs(result, value)
                result = None

        o.free()

    def test_bndl_processing_time(self):
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        oscaddr = '/msg'

        # Same fractional send time and time of arrival for nested bundles.
        result = [None, None]

        def func(msg, time, *_):
            nonlocal result
            result[msg[1]] = math.modf(time)[0]
            main.resume()

        o = OscFunc(func, oscaddr)

        lst = [
            [0, [oscaddr, 0], [oscaddr, 1]],
            [0, [oscaddr, 0], [1, [oscaddr, 1]]],
            [0, [1, [oscaddr, 0], [2, [oscaddr, 1]]]]
        ]

        for args in lst:
            n.send_bundle(*args)
            main.wait(tasks=2)
            self.assertTrue(math.isclose(*result))
            result = [None, None]

        o.free()

        # Completion message as a bundle case.
        result = []

        def func(msg, *_):
            nonlocal result
            for tm in OscPacket(msg[1]).messages:
                result.append(
                    math.modf(SystemClock.osc_to_elapsed_time(tm.time))[0])
            main.resume()

        o = OscFunc(func, oscaddr)
        n.send_msg(oscaddr, [1, ['/xxx'], [2, ['/yyy']]])
        main.wait(tasks=1)
        self.assertTrue(math.isclose(*result))
        o.free()

if __name__ == '__main__':
    unittest.main()
