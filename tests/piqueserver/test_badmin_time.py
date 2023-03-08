import unittest
from unittest.mock import MagicMock
from time import monotonic

from piqueserver.scripts import badmin

class TestBadminTime(unittest.TestCase):

    def test_score_grief_leap_negative(self):
        """Asserts that score_grief gives the expected result regardless of a 
        negative leap second.
        """

        connection = MagicMock()
        player = MagicMock()
        player.name = "othername"
        player.team.id = "team"
        player.blocks_removed = [(monotonic() - i, ("name", "team")) for i in range(115, 120)]

        # The returned gscore should be 6 according to the rules in badmin.
        # This is based on the fact that there are exactly 5 blocks within the timeframe.
        # See player.blocks_remved above.
        # Indirectly tests that the monotonic() call happening inside of score_grief()
        # always results in 5 blocks.

        # Asserts that score is always 6, if a negative leap second would affect the time
        # (which it shouldn't since we use monotonic() now in score_grief()), then the score would
        # increase to 7 since one more block would be included.
        assert badmin.score_grief(connection, player, time = 2) == 6

    
    def test_score_grief_leap_positive(self):
        """Asserts that score_grief gives the expected result regardless of a 
        positive leap second.
        """
        connection = MagicMock()
        player = MagicMock()
        player.name = "othername"
        player.team.id = "team"
        player.blocks_removed = [(monotonic() - i, ("name", "team")) for i in range(114, 120)]

        # The returned gscore should be 7 according to the rules in badmin.
        # This is based on the fact that there are exactly 6 blocks within the timeframe.
        # See player.blocks_remved above.
        # Indirectly tests that the monotonic() call happening inside of score_grief()
        # always results in 6 blocks.

        # Asserts that score is always 7, if a positive leap second would affect the time
        # (which it shouldn't since we use monotonic() now in score_grief()), then the score would
        # decrease to 6.
        assert badmin.score_grief(connection, player, time = 2) == 7