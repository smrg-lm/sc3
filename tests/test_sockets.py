
import unittest
import shutil

import sc3
sc3.init()

from sc3.base.main import main
from sc3.synth.server import s
from sc3.base.netaddr import NetAddr
from sc3.base.responders import OscFunc


class SocketsTestCase(unittest.TestCase):
    @unittest.skipIf(not shutil.which(s.options.program), 'no server available')
    def test_tcpserver(self):
        lang_port = NetAddr.lang_port()
        new_port = lang_port + 1
        endpoints = [('127.0.0.1', lang_port, 'udp'), ('127.0.0.1', new_port, 'tcp')]
        lmbd = lambda: main.resume()

        s.options.protocol = 'tcp'
        s.boot(True, lmbd, lmbd)
        main.wait()

        # NetAddr creates only client TCP connections.
        self.assertTrue(s.addr.is_connected)
        self.assertTrue(all(e in NetAddr.lang_endpoints() for e in endpoints))

        s.quit(True, lmbd, lmbd)
        main.wait()

    def test_oscfunc_recv_port(self):
        lang_port = NetAddr.lang_port()
        new_port = 57140
        endpoints = [('127.0.0.1', lang_port, 'udp'), ('127.0.0.1', new_port, 'udp')]

        def test(*args):
            self.assertEqual(args[3], new_port)
            main.resume()

        # OscFunc creates a new UDP interface for recv_port.
        f = OscFunc(test, '/', recv_port=new_port)
        # self.assertEqual(NetAddr.lang_endpoints(), endpoints)
        self.assertTrue(all(e in NetAddr.lang_endpoints() for e in endpoints))
        NetAddr('127.0.0.1', new_port).send_msg('/')
        main.wait()
        main.close_udp_port(new_port)
        f.free()

    def test_open_udp_port(self):
        lang_port = NetAddr.lang_port()
        new_port = 57150
        endpoints = [('127.0.0.1', lang_port, 'udp'), ('127.0.0.1', new_port, 'udp')]
        main.open_udp_port(new_port)
        self.assertTrue(all(e in NetAddr.lang_endpoints() for e in endpoints))
        main.close_udp_port(new_port)
        # threading...

    def test_netaddr_change_output_port(self):
        lang_port = NetAddr.lang_port()
        change_port = 57160
        addr = NetAddr('127.0.0.1', lang_port)

        with self.assertRaises(Exception, msg=f'port {change_port} is not open'):
            addr.change_output_port(change_port)
        self.assertEqual(addr.port, lang_port)

        main.open_udp_port(change_port)
        addr.change_output_port(change_port)
        self.assertEqual(addr.port, change_port)
        main.close_udp_port(change_port)


if __name__ == '__main__':
    unittest.main()
