
import unittest

import sc3
from sc3.base.model import NotificationCenter

sc3.init()


class NotificationCenterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Object():
            pass

        cls.Object = Object

    # @classmethod
    # def tearDownClass(cls):
    #     pass

    # def setUp(self):
    #     pass

    # def tearDown(self):
    #     pass

    def test_notify(self):
        a = self.Object()
        b = self.Object()
        a.value = 1
        b.value = 2

        def b_action(obj, msg, listener, *args):
            b.value = args[0]

        registration = NotificationCenter.register(
            a, 'value_changed', b, b_action)

        a.value = 10
        NotificationCenter.notify(a, 'value_changed', a.value)
        self.assertEqual(a.value, b.value, 'notification failure')

    def test_register(self, n=5):
        registrations = []
        actions = []
        msg = 'failed to register'

        for i in range(n):
            obj = self.Object()
            listener = self.Object()
            action = lambda: None
            actions.append(action)
            registrations.append([obj, 'changed', listener])
            NotificationCenter.register(obj, 'changed', listener, action)

        for (o, m, l), a in zip(registrations, actions):
            self.assertIs(NotificationCenter._registrations[o][m][l], a, msg)

    # TODO


if __name__ == '__main__':
    unittest.main()
