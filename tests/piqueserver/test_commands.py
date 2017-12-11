from piqueserver.commands import command
import unittest


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
