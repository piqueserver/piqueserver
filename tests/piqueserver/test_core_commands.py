import unittest
from unittest.mock import MagicMock
from piqueserver.core_commands.moderation import get_ban_arguments, has_digits
from piqueserver.core_commands.movement import do_move
from piqueserver.commands import (PermissionDenied)

class TestCoreCommands(unittest.TestCase):
    def test_has_digits(self):
        test_cases = [("1day", True), ("day", False), ("  1", True)]
        for case in test_cases:
            input, expect = case
            self.assertEqual(has_digits(input), expect)

    def test_get_ban_arguments(self):
        connection = MagicMock()
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




    # Tests for do_move

    def setUp(self):
        """
        Setup a mock connection object before testing.
        """
        self.mock_connection = MagicMock()
        self.mock_connection.name = "Mock_Player"
        self.mock_connection.admin = False
        self.mock_connection.rights.move_others = False
        self.mock_connection.invisible = False
        self.mock_connection.protocol.players = {"Mock_Player": self.mock_connection}
        self.mock_connection.protocol.map.get_height.return_value = 50


    def test_move_self_sector(self):
        """
        Test moving self to a sector.
        """

        do_move(self.mock_connection, ["A1"])

    def test_move_self_coordinates(self):
        """
        Test moving self to specific coordinates.
        """

        do_move(self.mock_connection, ["50", "50", "10"])

    def test_move_other_player_without_permission(self):
        """
        Test case where a player tries to move another player without permission.
        """

        with self.assertRaises(PermissionDenied):
            do_move(self.mock_connection, ["OtherPlayer", "50", "50", "10"])


    def test_invalid_argument_count(self):
        """
        Test case where an invalid number of arguments is provided.
        """

        with self.assertRaises(ValueError):
            do_move(self.mock_connection, ["A1", "extra_arg"])

    def test_silent_move(self):
        """
        Test case where a player is invisible and moves.
        """

        self.mock_connection.invisible = True

        do_move(self.mock_connection, ["A1"])

    
if __name__ == "__main__":
    unittest.main()