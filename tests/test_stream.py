
import unittest
from threading import Thread, Barrier

import sc3
from sc3.base.stream import (
    Routine, routine, StopStream, PausedStream, AlwaysYield,
    YieldAndReset, Condition, FlowVar)
from sc3.base.clock import TempoClock, defer

sc3.init()


class RoutineTestCase(unittest.TestCase):
    def test_common_function(self):
        '''Common functions are infinite None streams.'''

        @routine
        def rout():
            return 1

        for i in range(3):
            self.assertIs(next(rout), None)

    def test_generator_stop(self):
        '''Routines raise StopStream.'''
        @routine
        def rout():
            for i in range(3):
                yield i

        for i in range(3):
            self.assertEqual(next(rout), i)
        self.assertRaises(StopStream, next, rout)

    def test_generator_return(self):
        '''Routines raise StopStream.'''
        @routine
        def rout():
            for i in range(3):
                yield i
            return

        for i in range(3):
            self.assertEqual(next(rout), i)
        self.assertRaises(StopStream, next, rout)

    def test_states(self):
        r = Routine(lambda: 1)
        self.assertEqual(r.state, r.State.Init)
        r.next()
        self.assertEqual(r.state, r.State.Done)
        r.reset()
        self.assertEqual(r.state, r.State.Init)
        self.assertIs(next(r), None)
        self.assertEqual(r.state, r.State.Done)

        def r():
            return 1
        r = Routine(r)
        self.assertIs(next(r), None) # Infinite None
        self.assertIs(r.next(123), None)

        def r():
            self.assertEqual(r.state, r.State.Running)
            yield 1
            self.assertEqual(r.state, r.State.Running)
        r = Routine(r)
        r.pause()
        self.assertEqual(r.state, r.State.Paused)
        self.assertRaises(PausedStream, r.next)
        self.assertEqual(r.state, r.State.Paused)
        r.resume()
        self.assertEqual(r.state, r.State.Suspended)
        r.next()
        self.assertEqual(r.state, r.State.Suspended)
        self.assertRaises(StopStream, r.next)
        self.assertEqual(r.state, r.State.Done)
        r.reset()
        r.stop()
        self.assertEqual(r.state, r.State.Done)

        @routine
        def rout():
            self.assertEqual(rout.state, rout.state.Running)
            for i in range(2):
                yield i

        self.assertEqual(rout.state, rout.State.Init)
        self.assertEqual(next(rout), 0)
        self.assertEqual(rout.state, rout.State.Suspended)
        self.assertEqual(next(rout), 1)
        self.assertEqual(rout.state, rout.State.Suspended)
        self.assertRaises(StopStream, next, rout)
        self.assertEqual(rout.state, rout.state.Done)

    def test_stop_reset(self):
        @routine
        def rout():
            for i in range(2):
                yield i

        self.assertEqual(next(rout), 0)

        rout.stop()
        self.assertEqual(rout.state, rout.state.Done)
        self.assertRaises(StopStream, next, rout)

        rout.reset()
        self.assertEqual(rout.state, rout.State.Init)
        self.assertEqual(next(rout), 0)
        self.assertEqual(next(rout), 1)
        self.assertEqual(rout.state, rout.State.Suspended)

        self.assertRaises(StopStream, next, rout)
        self.assertEqual(rout.state, rout.state.Done)

        rout.reset()
        self.assertEqual(rout.state, rout.State.Init)
        self.assertEqual(next(rout), 0)

    def test_always_yield(self):
        @routine
        def rout():
            raise AlwaysYield(123)

        for i in range(3):
            self.assertEqual(next(rout), 123)

    def test_yield_and_reset(self):
        @routine
        def rout():
            yield None
            raise YieldAndReset(123)

        self.assertEqual(rout.state, rout.State.Init)
        self.assertIs(next(rout), None)
        self.assertEqual(rout.state, rout.State.Suspended)
        self.assertEqual(next(rout), 123)
        self.assertEqual(rout.state, rout.State.Init)
        self.assertIs(next(rout), None)

    def test_condition_same_clock(self):
        # The test has to wait.
        barrier = Barrier(2, timeout=1)
        # Clock threads can't be blocked.
        unlock = Thread(target=lambda: barrier.wait(), daemon=True)

        @routine.run()
        def test():
            test_value = 0
            cond = Condition()

            @routine
            def r():
                nonlocal test_value
                self.assertEqual(test_value, 1)
                test_value = 2
                yield from cond.wait()
                self.assertEqual(test_value, 3)
                test_value = 4

            # Schedule r in the same (default) clock.
            r.play()
            self.assertEqual(test_value, 0)
            test_value = 1
            # test has to way here (to get out of the queue) for r to
            # be in and out of the clock's queue (code after r.play()
            # excecutes before the content of r).
            yield 0
            self.assertEqual(test_value, 2)
            test_value = 3
            cond.unhang()
            # Allow r to resume.
            yield 0
            self.assertEqual(test_value, 4)
            unlock.start()

        barrier.wait()

    def test_condition_different_clocks(self):
        # The test has to wait.
        barrier = Barrier(3, timeout=1)
        # Clock threads can't be blocked.
        unlock1 = Thread(target=lambda: barrier.wait(), daemon=True)
        unlock2 = Thread(target=lambda: barrier.wait(), daemon=True)

        finish_value = 0
        clock1 = TempoClock()
        clock2 = TempoClock()

        @routine.run(clock1)
        def test():
            nonlocal finish_value
            test_value = 0
            cond1 = Condition()
            cond2 = Condition()

            # Schedule r in a different clock.
            @routine.run(clock2)
            def r():
                nonlocal finish_value
                nonlocal test_value
                self.assertEqual(test_value, 1)
                test_value = 2
                cond1.test = True
                cond1.signal()
                yield from cond2.wait()
                finish_value += 1
                unlock1.start()

            self.assertEqual(test_value, 0)
            test_value = 1
            yield 0
            cond2.test = True
            cond2.signal()
            yield from cond1.wait()
            self.assertEqual(test_value, 2)
            finish_value += 1
            unlock2.start()

        barrier.wait()
        self.assertEqual(finish_value, 2)  # FIXME: Barrier will be broken if not.

    def test_flowvar(self):
        # The test has to wait.
        barrier = Barrier(2, timeout=1)
        # Clock threads can't be blocked.
        unlock = Thread(target=lambda: barrier.wait(), daemon=True)
        test_var = FlowVar()

        @routine.run()
        def r1():
            value = (yield from test_var.value)
            self.assertEqual(value, 123)
            unlock.start()

        @routine.run()
        def r2():
            yield 0
            test_var.value = 123

        barrier.wait()

    # def test_rgen(self):
    #     ...


if __name__ == '__main__':
    unittest.main()
