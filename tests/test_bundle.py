
import unittest

import sc3
from sc3.base.netaddr import NetAddr
from sc3.base.responsedefs import OscFunc

sc3.init()


class BundleTestCase(unittest.TestCase):
    def test_sc3_special_cases(self):
        # blob from arrays, arrays, special cases like None, etc.
        ...

    def test_nested_bundle_time(self):
        # ValueError('nested bundle time must be >= enclosing bundle time').
        n = NetAddr('127.0.0.1', NetAddr.lang_port())
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(1, ['/msg', 1], [0.5, ['/msg', 2]]), n);
        self.assertRaises(
            ValueError,
            lambda n: n.send_bundle(0, ['/msg', 1], [None, ['/msg', 2]]), n);

    # BUG: Messages should have exactly the same decimal part (as in sclang).
    # This is needed for nested bundle times. Requires low level change
    # to UDP/TCP code. Is not critical.
    # def test_processing_time(self):
    #     n = NetAddr('127.0.0.1', 57120)
    #     o = OscFunc(lambda *args: print(args), '/msg')
    #     # Same time of arrival.
    #     n.send_bundle(0, ['/msg', 1], ['/msg', 2])
    #     n.send_bundle(0, ['/msg', 1], [1, ['/msg', 2]])
    #     n.send_bundle(0, [1, ['/msg', 1], [2, ['/msg', 2]]])


if __name__ == '__main__':
    unittest.main()
