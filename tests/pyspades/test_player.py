"""
test pyspades/player.py
"""

from __future__ import print_function
from pyspades import player
from unittest import mock, TestCase
from pyspades.player import ServerConnection
from pyspades.weapon import WEAPONS
from pyspades.constants import *


def get_mock_player(hp=1, blocks=0, tool=WEAPON_TOOL, weapon=RIFLE_WEAPON,
                    empty=False):
    prot = mock.MagicMock()
    peer = mock.MagicMock()
    sc = ServerConnection(prot, peer)
    sc.world_object = mock.MagicMock()
    sc.weapon_object = mock.MagicMock()
    sc.player_id = 0
    sc.hp = hp
    sc.blocks = blocks
    sc.tool = tool
    sc.weapon = weapon
    sc.weapon_object.is_empty = mock.MagicMock(return_value=empty)
    return sc


def get_mock_block_action(x=0, y=0, z=0, value=BUILD_BLOCK):
    cont = mock.MagicMock()
    type(cont).x = mock.PropertyMock(return_value=x)
    type(cont).y = mock.PropertyMock(return_value=y)
    type(cont).z = mock.PropertyMock(return_value=z)
    type(cont).value = mock.PropertyMock(return_value=value)
    return cont


class ServerConnectionTest(TestCase):

    def test_on_block_action_recieved_1(self):
        pass

