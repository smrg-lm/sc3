
import unittest
import shutil
import time

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
    def setUpClass(self):
        lmbd = lambda: main.resume()
        s.boot(True, lmbd, lmbd)
        main.wait()

    @classmethod
    def tearDownClass(self):
        lmbd = lambda: main.resume()
        s.quit(True, lmbd, lmbd)
        main.wait()

    def test_load_send(self):
        size = 1000
        rsize = 1 / size
        data = [i * rsize for i in range(size)]
        zero = [0.0] * size

        # b1a = Buffer.new_load_list(data, 2)
        b1b = Buffer.new_send_list(data, 2)
        # b1c = Buffer(size // 2, 2)
        # b1c.load_list(data)
        # b1d = Buffer(size // 2, 2)
        # b1d.send_list(data)
        b1 = b1b
        b2 = Buffer(size // 2, 2)
        main.sync(s)

        # Set data to server's values.
        def setdata(lst): nonlocal data; data = lst
        b1.get_to_list(setdata)

        @synthdef
        def test_buf(inbuf, outbuf):
            sig = PlayBuf(2, inbuf, done_action=2)
            RecordBuf(sig, outbuf)

        main.sync(s)

        # b2.get_to_list(lambda lst: print(lst == zero))
        b2.load_to_list(lambda lst: print(lst == zero))
        test_buf(b1, b2)

        time.sleep(0.5)
        # b2.get_to_list(lambda lst: print(lst == data))
        b2.load_to_list(lambda lst: print(lst == data))

        time.sleep(0.5)
        b1.free()
        b2.free()
