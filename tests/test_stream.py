
import unittest

from sc3.stream import routine, StopStream, AlwaysYield, YieldAndReset


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

    def test_status(self):
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

    # TODO ...


if __name__ == '__main__':
    unittest.main()
