
import unittest
import math

import sc3
sc3.init('rt')

from sc3.base.main import main
from sc3.base.clock import SystemClock, TempoClock
from sc3.base.stream import routine
from sc3.base.netaddr import NetAddr
from sc3.base.responders import OscFunc


# NOTE: These tests are duplicated for test_clock_nrt.py and need sync.

class ClockTestCase(unittest.TestCase):
    def test_time_unit_conversion(self):
        for _ in range(100):
            et = main.elapsed_time()
            eto = SystemClock.elapsed_time_to_osc(et)
            ote = SystemClock.osc_to_elapsed_time(eto)
            self.assertTrue(math.isclose(et, ote, abs_tol=1e-9))
            self.assertTrue(math.isclose(0.0, et - ote, abs_tol=1e-9))

    def test_logical_time_delta(self):
        tempo = 1000  # Float point resolution may affect tests if big.
        delta = 1

        @routine
        def test():
            # Clock is created inside a main routine to avoid
            # timing offset relative to elapsed time updates.
            clock = TempoClock(tempo)

            @routine
            def r():
                nonlocal clock
                beats = clock.beats
                elapsed_delta = 0
                t1 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t2 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t3 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                self.assertTrue(math.isclose(t2 - t1, t3 - t2))
                main.resume()

            r.play(clock)
            main.resume()

        test.play()
        main.wait(tasks=2)

    def test_initial_values(self):

        @routine
        def example():
            offset = 5
            # Starts from zero by default.
            t = TempoClock(1)
            self.assertTrue(math.isclose(t.beats, 0))
            # Starts counting beats from 'offset'.
            t = TempoClock(1, offset)
            self.assertTrue(math.isclose(t.beats, offset))
            # Counting beats as if it started 'offset' seconds ago from 0.
            t = TempoClock(1, 0, main.current_tt._seconds - offset)
            self.assertTrue(math.isclose(t.beats, offset))
            main.resume()

        example.play()
        main.wait()

    def test_logical_and_bundle_time(self):
        ltime = []
        btime = []
        naddr = NetAddr('127.0.0.1', NetAddr.lang_port())
        ofunc = OscFunc(lambda *args: btime.append(args[1]), '/test')

        @routine
        def r(inval):
            _, clock = inval
            for _ in range(100):
                ltime.append(clock.seconds)
                naddr.send_bundle(0, ['/test'])
                yield 0.0001
            main.resume()

        r.play()
        main.wait()
        # Must be almost the same time of the bundle, counting floating
        # point error in conversion (_SECONDS_TO_OSC factor and rouding
        # back). I guess 1 nanosecond should be the actual safe resolution,
        # not sure though. # TODO.
        for i, (l, b) in enumerate(zip(ltime, btime)):
            with self.subTest(case=i):
                self.assertTrue(math.isclose(l, b, abs_tol=1e-9))
        ofunc.free()


if __name__ == '__main__':
    unittest.main()
