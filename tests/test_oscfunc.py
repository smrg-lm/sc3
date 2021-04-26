
import unittest
from threading import Thread, Barrier
from functools import partial

import sc3
sc3.init()

from sc3.base.main import main
from sc3.base.netaddr import NetAddr
from sc3.base.responsedefs import OscFunc


class OscFuncTestCase(unittest.TestCase):
    def test_bndl_atomicity(self):
        n = NetAddr("127.0.0.1", NetAddr.lang_port());
        messages = ['/msg1', '/msg2', '/msg3', '/msg4']
        scrambled = ['/msg4', '/msg2', '/msg1', '/msg3']
        results = []
        funcs = []
        barrier = Barrier(len(messages) + 1, timeout=1)

        def func(path):
            results.append([path, main.elapsed_time()])
            Thread(target=lambda: barrier.wait(), daemon=True).start()

        for p in scrambled:
            f = partial(func, p)
            funcs.append(OscFunc(f, p))

        n.send_bundle(0, *[[m] for m in messages]);
        barrier.wait()

        # The order of evaluation should always be 1, 2, 3, 4.
        prev_time = 0
        for m, r in zip(messages, results):
            self.assertEqual(m, r[0])
            self.assertTrue(r[1] >= prev_time, f'{r[1]} >= {prev_time}')
            prev_time = r[1]

        for f in funcs:
            f.free()

    def test_bndl_msg_recv_time(self):
        n = NetAddr("127.0.0.1", NetAddr.lang_port());
        oscpath = '/msg'
        result = None

        def func(*args):
            nonlocal result
            result = args[1] < main.elapsed_time()
            main.resume()

        f = OscFunc(func, oscpath)

        lst = [
            # Bundle: with no latency should be always be True because client
            # time (main.elapsed_time) is read twice, low level and within the
            # OscFunc, this is something to bear in mind.
            [lambda: n.send_bundle(0, [oscpath]), True],
            [lambda: n.send_bundle(None, [oscpath]), True],
            # Bundle: should be always be False with enough latency
            # (network + processing).
            [lambda: n.send_bundle(1, [oscpath]), False],
            # Message: should be always be True due to processing time.
            [lambda: n.send_msg(oscpath), True]
        ]

        for i, (lamb, value) in enumerate(lst):
            with self.subTest(case=i):
                lamb()
                main.wait()
                self.assertIs(result, value)
                result = None

        f.free()

    # BUG: Messages should have exactly the same decimal part (as in sclang).
    # This is needed for nested bundle times. Requires low level change
    # to UDP/TCP code. Is not critical.
    # def test_bndl_processing_time(self):
    #     n = NetAddr('127.0.0.1', NetAddr.lang_port())
    #     o = OscFunc(lambda *args: print(args), '/msg')
    #     # Same time of arrival.
    #     n.send_bundle(0, ['/msg', 1], ['/msg', 2])
    #     n.send_bundle(0, ['/msg', 1], [1, ['/msg', 2]])
    #     n.send_bundle(0, [1, ['/msg', 1], [2, ['/msg', 2]]])


if __name__ == '__main__':
    unittest.main()
