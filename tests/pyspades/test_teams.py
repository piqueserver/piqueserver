# -*- encoding: utf-8 -*-
"""
test pyspades/teams.pyx
"""
from pyspades.constants import CTF_MODE

from pyspades.protocol import BaseProtocol

from pyspades.server import ServerProtocol
from twisted.trial import unittest

from pyspades.team import Team


class TestTeams(unittest.TestCase):
    name = "Team name"
    color = (255, 0, 255)

    def test_initial_values(self):
        team = Team(0, self.name, self.color, False, MockServerProtocol())
        self.assertEquals(0, team.kills)
        self.assertEquals(0, team.score)

    def test_team_from_team(self):
        team_template = Team(0, self.name, self.color, False, MockServerProtocol())
        team_template.kills = 9
        team_template.score = 5
        team = Team(*team_template.get_init_values())
        self.assertEquals(0, team.kills)
        self.assertEquals(0, team.score)
        self.assertEquals(team_template.name, team.name)
        self.assertEquals(team_template.color, team.color)

    def test_team_others(self):
        # Team.get_init_values() should not return values of field "other"
        team_1 = Team(0, "team_1", (255, 0, 255), False, MockServerProtocol())
        team_2 = Team(1, "team_2", (127, 127, 127), False, MockServerProtocol())
        team_1.other = team_2
        team_2.other = team_1
        team_1 = Team(*team_1.get_init_values())
        self.assertEquals(None, team_1.other)


# Dummy class mocking the behavior of ServerProtocol
class MockServerProtocol:
    game_mode = None
    entities = None
    map_info = None

    def __init__(self):
        self.game_mode = CTF_MODE
        self.entities = []
        self.map_info = True

    def get_random_location(self, a, b):
        return 0, 0, 0

    def on_flag_spawn(self, x, y, z, a, b):
        return None

    def on_base_spawn(self, a, b, c, d, e):
        return None
