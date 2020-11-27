
import unittest
import importlib
import pathlib
import sys
import os


class EntryPointTestCase(unittest.TestCase):
    def test_all_nrt(self):
        all_nrt = importlib.import_module('sc3.all_nrt')
        self.assertTrue(hasattr(all_nrt.main, 'process'))

    def test_main(self):
        exe = sys.executable
        parent = pathlib.Path(__file__).parent
        startup = parent / 'data/custom_startup.py'

        # Init rt, async logging, port, range, setup.
        script = parent / 'data/script_rt.py'
        cmd1 = (
            f'{exe} -m sc3 -u 57130 -r 20 -s {startup} '
            f'{script} TEST_ARG_VALUE')
        ret = os.system(cmd1)
        self.assertEqual(ret, 0)

        # Init nrt, bloking logging, ignores por and range.
        script = parent / 'data/script_nrt.py'
        cmd2 = cmd1 = (
            f'{exe} -m sc3 --nrt -u 57130 -r 20 -s {startup} '
            f'{script} TEST_ARG_VALUE')
        ret = os.system(cmd2)
        self.assertEqual(ret, 0)
