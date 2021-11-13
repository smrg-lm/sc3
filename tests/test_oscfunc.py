
import unittest

import sc3
sc3.init()

from sc3.base.main import main
from sc3.base.netaddr import NetAddr
from sc3.base.responders import OscFunc


class OscFuncTestCase(unittest.TestCase):
    TEST_TIME = 2

    def test_args(self):
        osc_addr = '/args_msg'
        osc_msg = [osc_addr, 123]
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])

        def recvf(msg, time, addr, recv_port):
            self.assertEqual(msg, osc_msg)
            self.assertIsInstance(time, float)
            self.assertEqual(addr, addr)
            self.assertEqual(recv_port, addr.port)
            main.resume()

        oscf = OscFunc(recvf, osc_addr)
        addr.send_msg(*osc_msg)
        addr.send_bundle(None, osc_msg)
        test_ok = main.wait(self.TEST_TIME, tasks=2)
        oscf.free()
        self.assertTrue(test_ok, 'test time expired')

    def test_path(self):
        # NOTE: I think it should trow an error anyway.
        osc_addr = '/bad_path_msg'
        non_compliant_addr = osc_addr[1:]
        osc_msg = [osc_addr, 123]
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])

        def recvf(msg):
            self.assertEqual(msg[0], osc_addr)
            main.resume()

        oscf = OscFunc(recvf, non_compliant_addr)
        addr.send_msg(*osc_msg)
        test_ok = main.wait(self.TEST_TIME)
        oscf.free()
        self.assertTrue(test_ok, 'test time expired')

    def test_src_id(self):
        osc_addr = '/src_id_msg'
        osc_msg = [osc_addr]

        newport = NetAddr.lang_port() + 10
        main.open_udp_port(newport)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        test_addr = NetAddr('127.0.0.1', newport)

        def recvf(_1, _2, sender_addr, recv_port):
            self.assertEqual(sender_addr, test_addr)
            self.assertEqual(NetAddr.lang_port(), recv_port)
            main.resume()

        oscf = OscFunc(recvf, osc_addr, test_addr)
        addr.send_msg(*osc_msg)  # Ignored msg from lang port.
        addr.change_output_port(newport)
        addr.send_msg(*osc_msg)
        test_ok = main.wait(self.TEST_TIME)
        oscf.free()
        main.close_udp_port(newport)
        self.assertTrue(test_ok, 'test time expired')

    def test_recv_port(self):
        osc_addr = '/recv_port_msg'
        osc_msg = [osc_addr]
        newport = NetAddr.lang_port() + 20

        def recvf(_1, _2, _3, recv_port):
            self.assertEqual(newport, recv_port)
            main.resume()

        oscf = OscFunc(recvf, osc_addr, recv_port=newport)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        addr.send_msg(*osc_msg)  # Ignored msg to default lang port.
        addr = NetAddr(NetAddr.lang_endpoints()[0][0], newport)
        addr.send_msg(*osc_msg)
        test_ok = main.wait(self.TEST_TIME)
        oscf.free()
        main.close_udp_port(newport)
        self.assertTrue(test_ok, 'test time expired')

    def test_arg_template(self):
        osc_addr = '/arg_template_msg'
        values_template = ['string', 0.5, lambda x: x > 5]
        osc_values = ['string', 0.5, 10, 'extra']

        def recvf(msg):
            self.assertEqual(msg[1:], osc_values)
            main.resume()

        oscf = OscFunc(recvf, osc_addr, arg_template=values_template)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        addr.send_msg(osc_addr, '/wrong', 123)  # Ignored, not matching template.
        addr.send_msg(osc_addr, *osc_values)
        test_ok = main.wait(self.TEST_TIME)
        oscf.free()
        self.assertTrue(test_ok, 'test time expired')

    def test_matching(self):
        glob_addr = '/m?t{ch,Ch}[a-z]n[!a-f]_*'
        osc_addr = '/matChing_msg'

        def recvf(msg):
            self.assertEqual(msg[0], glob_addr)
            main.resume()

        oscf = OscFunc.matching(recvf, osc_addr)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        addr.send_msg(glob_addr)
        test_ok = main.wait(self.TEST_TIME)
        oscf.free()
        self.assertTrue(test_ok, 'test time expired')

    def test_enable_disable(self):
        osc_addr = '/enable_disable_msg'

        def recvf():
            oscf.disable()
            main.resume()

        oscf = OscFunc.matching(recvf, osc_addr)
        self.assertTrue(oscf.enabled)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        addr.send_msg(osc_addr)
        test_ok = main.wait(self.TEST_TIME)
        self.assertTrue(test_ok, 'test time expired')
        self.assertFalse(oscf.enabled)

        oscf.enable()
        self.assertTrue(oscf.enabled)
        addr.send_msg(osc_addr)
        test_ok = main.wait(self.TEST_TIME)
        self.assertTrue(test_ok, 'test time expired')
        self.assertFalse(oscf.enabled)

    def test_one_shot(self):
        osc_addr = '/one_shot_msg'

        def recvf(msg):
            self.assertEqual(msg[0], osc_addr)
            main.resume()

        oscf = OscFunc.matching(recvf, osc_addr)
        oscf.one_shot()
        self.assertTrue(oscf.enabled)
        addr = NetAddr(*NetAddr.lang_endpoints()[0][:2])
        addr.send_msg(osc_addr)
        test_ok = main.wait(self.TEST_TIME)
        self.assertFalse(oscf.enabled)
        self.assertTrue(test_ok, 'test time expired')

    # def test_trace(self):
    #     ...


if __name__ == '__main__':
    unittest.main()
