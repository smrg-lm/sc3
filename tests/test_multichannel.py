
import unittest

from sc3.utils import list_unop, list_binop, list_narop
from sc3.ugen import ChannelList, UGen, BinaryOpUGen
from sc3.ugens.osc import SinOsc
import sc3.builtins as bi


class SeqOpTestCase(unittest.TestCase):
    def test_unop(self):
        # scalar
        case = list_unop('neg', 10)
        self.assertIs(type(case), int)
        self.assertEqual(case, -10)

        # list of scalars
        case = list_unop('neg', [10, 20])
        self.assertIs(type(case), list)
        self.assertEqual(case, [-10, -20])

        # tuple of scalars, default type
        case = list_unop('neg', (10, 20))
        self.assertIs(type(case), list)
        self.assertEqual(case, [-10, -20])

        # tuple of scalars as type
        case = list_unop('neg', (10, 20), tuple)
        self.assertIs(type(case), tuple)
        self.assertEqual(case, (-10, -20))

        # tuple list
        case = list_unop('neg', [(10, 20)])
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (-10, -20))

        # list of tuple and scalar
        case = list_unop('neg', [(10, 20), 30])
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (-10, -20))
        self.assertEqual(case[1], -30)

        # nested tuples and lists
        case = list_unop(
            'neg', [(10, 20, [30, 40]), 50, [60, [[70], (80,)], 90]])
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertIs(type(case[0][2]), list)
        self.assertIs(type(case[1]), int)
        self.assertIs(type(case[2]), list)
        self.assertIs(type(case[2][0]), int)
        self.assertIs(type(case[2][1]), list)
        self.assertIs(type(case[2][1][0]), list)
        self.assertIs(type(case[2][1][1]), tuple)
        self.assertIs(type(case[2][2]), int)
        self.assertEqual(
            case, [(-10, -20, [-30, -40]), -50, [-60, [[-70], (-80,)], -90]])

        # case builtins

    def test_binop(self):
        # scalars
        case = list_binop('mul', 10, -1)
        self.assertIs(type(case), int)
        self.assertEqual(case, -10)

        # list and scalar
        case = list_binop('mul', [10, 20], -1)
        self.assertIs(type(case), list)
        self.assertEqual(case, [-10, -20])

        # scalar and list
        case = list_binop('mul', -1, [10, 20])
        self.assertIs(type(case), list)
        self.assertEqual(case, [-10, -20])

        # tuple and scalar
        case = list_binop('mul', (10, 20), -1)
        self.assertIs(type(case), list)  # default type
        self.assertEqual(case, [-10, -20])

        # scalar and tuple
        case = list_binop('mul', -1, (10, 20), tuple)
        self.assertIs(type(case), tuple)
        self.assertEqual(case, (-10, -20))

        # tuple list and scalar
        case = list_binop('mul', [(10, 20)], -1)
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (-10, -20))

        # list of tuple and scalar
        case = list_binop('mul', -1, [(10, 20), 30])
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (-10, -20))
        self.assertEqual(case[1], -30)

        # nested tuples and lists
        case = list_binop(
            'mul', [(10, 20, [30, 40]), 50, [60, [[70], (80,)], 90]], -1)
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertIs(type(case[0][2]), list)
        self.assertIs(type(case[1]), int)
        self.assertIs(type(case[2]), list)
        self.assertIs(type(case[2][0]), int)
        self.assertIs(type(case[2][1]), list)
        self.assertIs(type(case[2][1][0]), list)
        self.assertIs(type(case[2][1][1]), tuple)
        self.assertIs(type(case[2][2]), int)
        self.assertEqual(
            case, [(-10, -20, [-30, -40]), -50, [-60, [[-70], (-80,)], -90]])

        # cases seq op seq mixed list and tuple
        case = list_binop(
            'add', [[1], (2, (2,)), 3], (([10], (10,)), [20], [30, [30]]))
        self.assertIs(type(case), list)  # default type
        self.assertIs(type(case[0]), tuple)
        self.assertIs(type(case[1]), tuple)
        self.assertIs(type(case[2]), list)
        self.assertEqual(case, [([11], (11,)), (22, (22,)), [33, [33]]])

        # cases seq op seq type conversion in three levels
        case = list_binop(
            'sub', [([(1,)], ([1],)), [([2],), [(2,)]]], [[1], (2,)])
        self.assertIs(type(case), list)  # default type
        self.assertIs(type(case[0]), tuple)
        self.assertIs(type(case[0][0]), list)
        self.assertIs(type(case[0][0][0]), tuple)
        self.assertIs(type(case[0][1]), tuple)
        self.assertIs(type(case[0][1][0]), list)
        self.assertIs(type(case[1]), tuple)
        self.assertIs(type(case[1][0]), tuple)
        self.assertIs(type(case[1][0][0]), list)
        self.assertIs(type(case[1][1]), list)
        self.assertIs(type(case[1][1][0]), tuple)
        self.assertEqual(case, [([(0,)], ([0],)), (([0],), [(0,)])])

        # case builtins

    def test_narop(self):
        # scalar
        case = list_narop(bi.clip, 10, 0, 9)
        self.assertIs(type(case), int)
        self.assertEqual(case, 9)

        # list
        case = list_narop(bi.clip, [10, 20], 0, 9)
        self.assertIs(type(case), list)
        self.assertEqual(case, [9, 9])

        # tuple, default type
        case = list_narop(bi.clip, (10, 20), 0, 9)
        self.assertIs(type(case), list)
        self.assertEqual(case, [9, 9])

        # tuple as type
        case = list_narop(bi.clip, (10, 20), 0, 9, t=tuple)
        self.assertIs(type(case), tuple)
        self.assertEqual(case, (9, 9))

        # tuple list
        case = list_narop(bi.clip, [(10, 20)], 0, 9)
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (9, 9))

        # list of tuple and scalar
        case = list_narop(bi.clip, [(10, 20), 30], 0, 9)
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertEqual(case[0], (9, 9))
        self.assertEqual(case[1], 9)

        # nested tuples and lists
        case = list_narop(
            bi.clip, [(10, 20, [30, 40]), 50, [60, [[70], (80,)], 90]], 0, 9)
        self.assertIs(type(case), list)
        self.assertIs(type(case[0]), tuple)
        self.assertIs(type(case[0][2]), list)
        self.assertIs(type(case[1]), int)
        self.assertIs(type(case[2]), list)
        self.assertIs(type(case[2][0]), int)
        self.assertIs(type(case[2][1]), list)
        self.assertIs(type(case[2][1][0]), list)
        self.assertIs(type(case[2][1][1]), tuple)
        self.assertIs(type(case[2][2]), int)
        self.assertEqual(
            case, [(9, 9, [9, 9]), 9, [9, [[9], (9,)], 9]])

        # other cases


class ChannelListTestCase(unittest.TestCase):
    def test_constructor(self):
        # int
        l1c_from_scalar = ChannelList(123)
        self.assertIs(type(l1c_from_scalar), ChannelList)
        self.assertEqual(len(l1c_from_scalar), 1)
        self.assertIs(type(l1c_from_scalar[0]), int)
        self.assertEqual(l1c_from_scalar[0], 123)

        # float
        l1c_from_scalar = ChannelList(123.123)
        self.assertIs(type(l1c_from_scalar), ChannelList)
        self.assertEqual(len(l1c_from_scalar), 1)
        self.assertIs(type(l1c_from_scalar[0]), float)
        self.assertEqual(l1c_from_scalar[0], 123.123)

        # string is scalar for graphs
        l1c_from_scalar = ChannelList("123")
        self.assertIs(type(l1c_from_scalar), ChannelList)
        self.assertEqual(len(l1c_from_scalar), 1)
        self.assertIs(type(l1c_from_scalar[0]), str)
        self.assertEqual(l1c_from_scalar[0], "123")

        # tuple is scalar (vector parameter) for graphs, no expansion
        l1c_from_scalar = ChannelList((123, 123))
        self.assertIs(type(l1c_from_scalar), ChannelList)
        self.assertEqual(len(l1c_from_scalar), 1)
        self.assertIs(type(l1c_from_scalar[0]), tuple)
        self.assertEqual(l1c_from_scalar[0], (123, 123))

        # list
        l1c_from_seq = ChannelList([123])
        self.assertIs(type(l1c_from_seq), ChannelList)
        self.assertEqual(len(l1c_from_seq), 1)
        self.assertIs(type(l1c_from_seq[0]), int)
        self.assertEqual(l1c_from_seq[0], 123)

        # tuple list
        l1c_from_seq = ChannelList([(123, 123)])
        self.assertIs(type(l1c_from_seq), ChannelList)
        self.assertEqual(len(l1c_from_seq), 1)
        self.assertIs(type(l1c_from_seq[0]), tuple)
        self.assertEqual(l1c_from_seq[0], (123, 123))

        # range
        l1c_from_seq = ChannelList(range(1))
        self.assertIs(type(l1c_from_seq), ChannelList)
        self.assertEqual(len(l1c_from_seq), 1)
        self.assertIs(type(l1c_from_seq[0]), int)
        self.assertEqual(l1c_from_seq[0], 0)

        # generator
        l1c_from_seq = ChannelList(i for i in range(1))
        self.assertIs(type(l1c_from_seq), ChannelList)
        self.assertEqual(len(l1c_from_seq), 1)
        self.assertIs(type(l1c_from_seq[0]), int)
        self.assertEqual(l1c_from_seq[0], 0)

        # multichannel

        # from list of scalars
        l2c = ChannelList([1, '234'])
        self.assertIs(type(l2c), ChannelList)
        self.assertEqual(len(l2c), 2)
        self.assertIs(type(l2c[0]), int)
        self.assertEqual(l2c[0], 1)
        self.assertIs(type(l2c[1]), str)
        self.assertEqual(l2c[1], '234')

        # from list of tuples (as if were scalars)
        l2c = ChannelList([(1, 2, 3), (4, 5, 6)])
        self.assertIs(type(l2c), ChannelList)
        self.assertEqual(len(l2c), 2)
        self.assertIs(type(l2c[0]), tuple)
        self.assertEqual(l2c[0], (1, 2, 3))
        self.assertIs(type(l2c[1]), tuple)
        self.assertEqual(l2c[1], (4, 5, 6))

        # from list with list (as if were scalars, only base level matters)
        l2c = ChannelList(['123', [4, 5, 6]])
        self.assertIs(type(l2c), ChannelList)
        self.assertEqual(len(l2c), 2)
        self.assertIs(type(l2c[0]), str)
        self.assertEqual(l2c[0], '123')
        self.assertIs(type(l2c[1]), list)
        self.assertEqual(l2c[1], [4, 5, 6])

        # other cases?

    def test_as_ugen_result(self):
        ugen = SinOsc.ar(440)
        self.assertIs(type(ugen), SinOsc)

        ugen = SinOsc.ar((440, 441))  # valid for other UGens
        self.assertIs(type(ugen), SinOsc)  # no expansion
        self.assertEqual(ugen.inputs, ((440, 441), 0.0))

        l1c = SinOsc.ar([440])  # is valid use case
        self.assertIs(type(l1c), ChannelList)  # list in list out
        self.assertEqual(len(l1c), 1)
        self.assertIs(type(l1c[0]), SinOsc)

        l2c = SinOsc.ar([440, 441])
        self.assertIs(type(l2c), ChannelList)
        self.assertEqual(len(l2c), 2)
        self.assertIs(type(l2c[0]), SinOsc)
        self.assertIs(type(l2c[1]), SinOsc)

        # other cases?

    def test_binary_operations(self):
        l2c = ChannelList([UGen(), [40, 50, 60]])
        l2c = l2c * 2
        self.assertIs(type(l2c), ChannelList)
        self.assertIs(type(l2c[0]), BinaryOpUGen)
        self.assertIs(type(l2c[1]), list)
        self.assertEqual(l2c[1], [80, 100, 120])

        # in place
        l2c = ChannelList([UGen(), [40, 50, 60]])
        l2c *= 2
        self.assertIs(type(l2c), ChannelList)
        self.assertIs(type(l2c[0]), BinaryOpUGen)
        self.assertIs(type(l2c[1]), list)
        self.assertEqual(l2c[1], [80, 100, 120])

        # with tuple (operations are performed as if were lists)
        l2c = ChannelList([UGen(), (40, 50, 60)])
        l2c = l2c * 2
        self.assertIs(type(l2c), ChannelList)
        self.assertIs(type(l2c[0]), BinaryOpUGen)
        self.assertIs(type(l2c[1]), tuple)
        self.assertEqual(l2c[1], (80, 100, 120))

        # nested list (not really a use case in graphs)
        l2c = ChannelList([[10, 20, 30, [40, 50, 60]], UGen()])
        l2c = l2c * 2
        self.assertIs(type(l2c), ChannelList)
        self.assertIs(type(l2c[0]), list)
        self.assertEqual(len(l2c[0]), 4)
        self.assertEqual(l2c[0][:3], [20, 40, 60])
        self.assertIs(type(l2c[0][3]), list)
        self.assertEqual(l2c[0][3], [80, 100, 120])
        self.assertIs(type(l2c[1]), BinaryOpUGen)

        # nested tuple (not really a use case in graphs), in place
        l2c = ChannelList([[10, 20, 30, (40, 50, 60)], UGen()])
        l2c *= 2
        self.assertIs(type(l2c), ChannelList)
        self.assertIs(type(l2c[0]), list)
        self.assertEqual(len(l2c[0]), 4)
        self.assertEqual(l2c[0][:3], [20, 40, 60])
        self.assertIs(type(l2c[0][3]), tuple)
        self.assertEqual(l2c[0][3], (80, 100, 120))
        self.assertIs(type(l2c[1]), BinaryOpUGen)

        # other cases/op


if __name__ == '__main__':
    unittest.main()
