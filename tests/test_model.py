
import unittest

from sc3.model import NotificationCenter, NotificationRegistration


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

        def b_action(*args):
            b.value = args[0]

        registration = NotificationCenter.register(
            a, 'value_changed', b, b_action
        )

        a.value = 10
        NotificationCenter.notify(a, 'value_changed', a.value)
        self.assertEqual(a.value, b.value, 'notification failure')

    def test_register(self, n=5):
        registrations = []
        actions = []
        msg = 'failed to register'

        for i in range(n):
            obj = self.Object()
            action = lambda: None
            registrations.append(
                NotificationCenter.register(
                    None, 'value_changed', obj, action))
            actions.append(action)

        for r, a in zip(registrations, actions):
            self.assertIs(
                NotificationCenter.registrations[r.obj, r.msg, r.listener],
                a, msg
            )

    # TODO
