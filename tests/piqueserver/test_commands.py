import unittest
from unittest.mock import Mock
from piqueserver.commands import command, _alias_map, target_player


class TestCommandDecorator(unittest.TestCase):
    def test_admin_only(self):
        @command(admin_only=True)
        def test():
            pass
        want = set()
        want.add('admin')
        self.assertEqual(test.user_types, want)

    def test_command_name(self):
        @command()
        def test():
            pass
        self.assertEqual(test.command_name, 'test')

    def test_command_rename(self):
        @command('notatest')
        def test():
            pass
        self.assertEqual(test.command_name, 'notatest')

    def test_command_alias(self):
        @command('name', 'n')
        def test():
            pass
        self.assertEqual(_alias_map['n'], 'name')


class TestTargetPlayerDecorator(unittest.TestCase):
    def test_no_arg_non_player(self):
        @command()
        @target_player
        def test(connection, player):
            pass

        connection = Mock()
        connection.protocol.players.values = lambda: []

        with self.assertRaises(ValueError):
            test(connection, player=None)

    def test_no_arg_player(self):
        @command()
        @target_player
        def test(connection, player):
            self.assertEqual(connection, player)

        connection = Mock()
        connection.protocol.players.values = lambda: [connection]

        test(connection)
