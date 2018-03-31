import unittest
from piccolo.commands import command, _alias_map


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
