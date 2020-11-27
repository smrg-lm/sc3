
import unittest
import importlib
import sys
import os


class EntryPointTestCase(unittest.TestCase):
    def test_all_nrt(self):
        all_nrt = importlib.import_module('sc3.all_nrt')
        self.assertTrue(hasattr(all_nrt.main, 'process'))

    def test_main(self):
        exe = sys.executable
        startup = r'./data/custom_startup.py'

        # Init rt, async logging, port, range, setup.
        cmd1 = (
            rf'{exe} -m sc3 -u 57130 -r 20 -s {startup} '
            r'./data/script_rt.py TEST_ARG_VALUE')
        ret = os.system(cmd1)
        self.assertEqual(ret, 0)

        # Init nrt, bloking logging, ignores por and range.
        cmd2 = cmd1 = (
            rf'{exe} -m sc3 --nrt -u 57130 -r 20 -s {startup} '
            r' ./data/script_nrt.py TEST_ARG_VALUE')
        ret = os.system(cmd2)
        self.assertEqual(ret, 0)
