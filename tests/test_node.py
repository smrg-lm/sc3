
import unittest
import shutil

import sc3
sc3.init()

from sc3.base.main import main
from sc3.synth.server import s
from sc3.synth.node import Group, Synth
from sc3.synth.synthdef import synthdef
from sc3.synth.ugens import Out, SinOsc


@unittest.skipIf(not shutil.which(s.options.program), 'no server available')
class NodeTestCase(unittest.TestCase):
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

    def test_node(self):
        data = None

        def load_info(dct):
            nonlocal data
            data = dct
            main.resume()

        g = Group()
        x = Synth('default', {'amp': 0}, g)
        test = {
            'Group(0)': {
                'Group(1)': {
                    f'Group({g.node_id})': {
                        f'Synth({x.node_id}, default)': {} }}}}

        s.query_tree(action=load_info)
        main.wait()
        self.assertEqual(data, test)
        s.free_nodes()

        # (un)retister, is_playing, is_running, basic_new, free, run, map,
        # set, setn, fill, release, query, on_free, wait_for_free, move_*

    #     data = None
    #     ...
    #     test = { ... }

    #     s.query_tree(action=load_info)
    #     main.wait()
    #     self.assertEqual(data, test)
    #     s.free_nodes()

    # def test_group(self):
    #     data = None

    #     def load_info(dct):
    #         nonlocal data
    #         data = dct
    #         main.resume()

    #     ...
    #     test = { ... }

    #     s.query_tree(action=load_info)
    #     main.wait()
    #     self.assertEqual(data, test)
    #     s.free_nodes()

    #     # after, before, head, tail, replace, free_all, deep_free

    #     data = None
    #     ...
    #     test = { ... }

    #     s.query_tree(action=load_info)
    #     main.wait()
    #     self.assertEqual(data, test)
    #     s.free_nodes()


    def test_synth(self):
        data = None

        def load_info(dct):
            nonlocal data
            data = dct
            main.resume()

        # ...
        # test = { ... }

        # s.query_tree(action=load_info)
        # main.wait()
        # self.assertEqual(data, test)
        # s.free_nodes()

        # Arrayed controls, seti.

        data = None
        with s.bind():
            @synthdef
            def testdef(freq=(220, 330, 440), amp=0):
                Out.ar(0, SinOsc.ar(freq).sum() * amp)
            yield s.sync()
            x = testdef()
            x.seti('freq', 0, [110, 220, 330, 440], 'amp', 0, 1)  # One more freq.
            s.query_tree(True, action=load_info)

        test = {
            'Group(0)': {
                'Group(1)': {
                    f'Synth({x.node_id}, {x.def_name})': {
                        'freq': 110.0, '1': 220.0, '2': 330.0, 'amp': 1.0}}}}

        main.wait()
        self.assertEqual(data, test)
        s.free_nodes()

        # basic_new, new_paused, grain, after ..., get, getn, seti.

        # data = None
        # ...
        # test = { ... }

        # s.query_tree(action=load_info)
        # main.wait()
        # self.assertEqual(data, test)
        # s.free_nodes()


if __name__ == '__main__':
    unittest.main()
