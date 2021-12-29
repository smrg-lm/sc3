
import unittest
import shutil

import sc3
sc3.init()

from sc3.base.main import main
from sc3.synth.server import s
from sc3.synth.buffer import Buffer
from sc3.synth.synthdef import synthdef
from sc3.synth.ugens import PlayBuf, RecordBuf


@unittest.skipIf(not shutil.which(s.options.program), 'no server available')
class BufferTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lmbd = lambda: main.resume()
        s.boot(True, lmbd, lmbd)
        main.wait()

    @classmethod
    def tearDownClass(cls):
        lmbd = lambda: main.resume()
        s.quit(True, lmbd, lmbd)
        main.wait()

    def test_load_send(self):
        b1 = b2 = None
        size = 1000
        rsize = 1 / size
        data = [i * rsize for i in range(size)]
        zero = [0.0] * size
        test_ok = False

        # Define test's SynthDef.
        @synthdef
        def test_buf_def(inbuf, outbuf):
            sig = PlayBuf(2, inbuf, done_action=2)
            RecordBuf(sig, outbuf)

        # Send test data to the server.
        b1 = Buffer.new_load_list(data, 2)
        main.sync(s)

        # Set client's data to server's values.
        def setdata(lst):
            nonlocal data
            data = lst

        b1.load_to_list(setdata)
        main.sync(s)

        # Set the test buffer and check initialization to zero.
        b2 = Buffer(size // 2, 2)
        main.sync(s)

        def test_data_initialization(lst):
            nonlocal test_ok
            test_ok = lst == zero
            main.resume()

        b2.load_to_list(test_data_initialization)
        main.wait()
        self.assertTrue(test_ok)
        test_ok = False

        # Process data in the server, write b1 to b2.
        test_buf_def(b1, b2)
        main.wait(0.5)

        # Compare processed data.
        def test_procesed_data(lst):
            nonlocal test_ok
            test_ok = lst == data
            main.resume()

        b2.load_to_list(test_procesed_data)
        main.wait()
        self.assertTrue(test_ok)
        test_ok = False

        # Free buffers.
        b1.free()
        b2.free()

        # Test alternative forms (reusing processed server's data values).

        with self.subTest(case='new_send_list, get_to_list'):
            # Needs action because creates a stream of messages.
            b3 = Buffer.new_send_list(data, 2, action=lambda: main.resume())
            main.wait()
            b3.get_to_list(test_procesed_data)
            main.wait()
            self.assertTrue(test_ok)
            test_ok = False
            b3.free()

        with self.subTest(case='new, load_list, load_to_list'):
            b3 = Buffer(size // 2, 2)
            # '/b_alloc' is async, this form doesn't handles that internally.
            main.sync(s)
            b3.load_list(data)
            main.sync(s)
            b3.load_to_list(test_procesed_data)
            main.wait()
            self.assertTrue(test_ok)
            test_ok = False
            b3.free()

        with self.subTest(case='new, send_list, get_to_list'):
            b3 = Buffer(size // 2, 2)
            # '/b_alloc' is async, this form doesn't handles that internally.
            main.sync(s)
            # Also needs action because creates a stream of messages.
            b3.send_list(data, action=lambda: main.resume())
            main.wait()
            b3.get_to_list(test_procesed_data)
            main.wait()
            self.assertTrue(test_ok)
            test_ok = False
            b3.free()


if __name__ == '__main__':
    unittest.main()
