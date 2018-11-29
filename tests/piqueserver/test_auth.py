import unittest
from piqueserver.config import config
from piqueserver.auth import ConfigAuthBackend, AuthError
from piqueserver.player import FeatureConnection
from pyspades.types import AttributeSet


class MockConnection(object):
    admin = False
    rights = AttributeSet()


class TestConfigAuthBackend(unittest.TestCase):
    def test_login_ok(self):
        config.update_from_dict({
            "passwords": {
                "moderator": ["mod1", "mod2"],
                "guard": ["guard1", "guard2"]
            }
        })
        auth = ConfigAuthBackend()
        self.assertEqual(auth.login(("", "mod2")), "moderator")
        self.assertEqual(auth.login(("", "guard1")), "guard")
        self.assertRaises(AuthError, lambda: auth.login(("", "mod3")))
        self.assertRaises(AuthError, lambda: auth.login(("", "guard5")))

    def test_has_permission_admin(self):
        connection = MockConnection()
        connection.admin = True
        auth = ConfigAuthBackend()
        has = auth.has_permission(connection, "ban")
        self.assertTrue(has)

    def test_has_permission_rights(self):
        connection = MockConnection()
        connection.rights = AttributeSet(['hban', 'kick'])
        auth = ConfigAuthBackend()
        for case in [("ban", False), ("hban", True), ("kick", True)]:
            action, expected = case
            got = auth.has_permission(connection, action)
            self.assertEqual(got, expected)
