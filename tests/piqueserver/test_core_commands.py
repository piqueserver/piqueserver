import unittest
from unittest.mock import Mock
from piqueserver.core_commands.moderation import get_ban_arguments, has_digits


class TestCoreCommands(unittest.TestCase):
    def test_has_digits(self):
        test_cases = [("1day", True), ("day", False), ("  1", True)]
        for case in test_cases:
            input, expect = case
            self.assertEqual(has_digits(input), expect)

    def test_get_ban_arguments(self):
        connection = Mock()
        connection.protocol.default_ban_time = 9001
        self.assertEqual(connection.protocol.default_ban_time, 9001)
        test_cases = [
            {
                "name": "Simple",
                "expect": (20 * 60, "too twenty"),
                "args": ["20", "too twenty"]
            },
            {
                "name": "Only reason",
                "expect": (9001, "blah blah blah blah"),
                "args": ["blah", "blah", "blah", "blah"]
            },
            {
                "name": "Perma",
                "expect": (None, "tabs"),
                "args": ["perma", "tabs"]
            },
            {
                "name": "No args",
                "expect": (9001, None),
                "args": []
            },
            {
                "name": "Simple duration",
                "expect": (60 * 60, "ab"),
                "args": ["1hour", "ab"]
            },
            {
                "name": "Invalid duration",
                "expect": (),
                "args": ["1dia", "?"],
                "ex": ValueError
            },
        ]
        for case in test_cases:
            print(case["name"])
            if "ex" in case:
                with self.assertRaises(case["ex"]):
                    get_ban_arguments(connection, case["args"])
                continue
            got = get_ban_arguments(connection, case["args"])
            self.assertTupleEqual(got, case["expect"])
