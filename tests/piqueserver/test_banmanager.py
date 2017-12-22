import unittest
from piqueserver.banmanager import BanManager


class TestBanManager(unittest.TestCase):
    def test_ban(self):
        ban_manager = BanManager()
        ban_manager.ban('127.0.0.1', 1, 'test', 'panic')
        ban_manager.ban('127.0.0.1/24', 1, 'test', 'panic')
        self.assertEqual(len(ban_manager.bans), 2)

    def test_unban(self):
        ban_manager = BanManager()
        ban_manager.ban('127.0.0.1', 1, 'test', 'panic')
        ban_manager.ban('127.0.0.1/24', 1, 'test', 'panic')
        ban_manager.unban('127.0.0.1')
        self.assertEqual(len(ban_manager.bans), 0)

    def test_freeup_bans(self):
        ban_manager = BanManager()
        ban_manager.ban('127.0.0.1', 1, 'test', 'panic')
        ban_manager.ban('127.0.5.1', 0, 'test', 'panic')
        ban_manager.freeup_bans()
        self.assertEqual(len(ban_manager.bans), 1)

    def test_undo_ban(self):
        ban_manager = BanManager()
        ban_manager.ban('127.0.0.1', 1, 'test', 'panic')
        ban_manager.ban('127.0.5.1', 1, 'test', 'panic')
        ban_manager.undo_ban()
        self.assertEqual(len(ban_manager.bans), 1)
        self.assertEqual(str(ban_manager.bans[0]['network']), '127.0.0.1/32')

    def test_is_banned(self):
        ban_manager = BanManager()
        ban_manager.ban('127.0.0.1', 20, 'test', 'panic')
        ban_manager.ban('127.0.5.1', 0, 'test', 'panic')
        self.assertEqual(ban_manager.is_banned('127.0.0.1'), True)
        self.assertEqual(ban_manager.is_banned('127.0.5.1'), False)
