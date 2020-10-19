
import unittest
import time

import sc3
from sc3.base.netaddr import NetAddr
from sc3.base.responsedefs import OscFunc

sc3.init()

from sc3.base.main import main


class OscFuncTestCase(unittest.TestCase):
    def test_bundle_atomicity(self):
        n = NetAddr("127.0.0.1", NetAddr.lang_port());
        messages = ['/msg1', '/msg2', '/msg3', '/msg4']
        scrambled = ['/msg4', '/msg2', '/msg1', '/msg3']
        results = []
        funcs = []

        def make_func(path):
            return lambda: results.append([path, main.elapsed_time()])

        for p in scrambled:
            f = make_func(p)
            funcs.append(OscFunc(f, p))

        n.send_bundle(0, *[[m] for m in messages]);
        time.sleep(0.1)  # TIENE QUE SER ASYNC.
        # for f in funcs:
        #     f.free()

        # The order of evaluation should always be 1, 2, 3, 4.
        prev_time = 0
        for m, r in zip(messages, results):
            self.assertEqual(m, r[0])
            self.assertTrue(r[1] >= prev_time, f'{r[1]} >= {prev_time}')
            prev_time = r[1]

    def test_bndl_msg_recv_time(self):
        n = NetAddr("127.0.0.1", 57120);

        # # Bundle: with no latency should be always be *true* because client time (Main.elapsedTime) is read twice, low level and within the OSCFunc, this is something to bear in mind.
        # o = OscFunc({ arg ...args; (args[1] < Main.elapsedTime).postln; }, "/msg");
        # n.sendBundle(0, ["/msg"]);
        # o.free;
        #
        # # Message: should be always be *true* due to processing time.
        # o = OscFunc({ arg ...args; (args[1] < Main.elapsedTime).postln; }, "/msg");
        # n.sendMsg("/msg");
        # o.free;
        #
        # # Bundle: should be always be *false* with enough latency (network + processing).
        # o = OscFunc({ arg ...args; (args[1] < Main.elapsedTime).postln; }, "/msg");
        # n.sendBundle(1, ["/msg"]);
        # o.free;


if __name__ == '__main__':
    unittest.main()
