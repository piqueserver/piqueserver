"""
test pyspades/player.py
"""

from __future__ import print_function
from unittest import mock, TestCase
from pyspades import player
from pyspades.player import ServerConnection
from pyspades.constants import SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, \
                               RIFLE_WEAPON, BUILD_BLOCK, DESTROY_BLOCK,\
                               SPADE_DESTROY


def get_mock_player(hp=101, blocks=29, tool=BLOCK_TOOL, weapon=None,
                    empty=True):
    prot = mock.MagicMock()
    peer = mock.MagicMock()
    sc = ServerConnection(prot, peer)
    sc.world_object = mock.MagicMock()
    sc.weapon_object = mock.MagicMock()
    sc.player_id = 42
    sc.hp = hp
    sc.blocks = blocks
    sc.tool = tool
    sc.weapon = weapon
    sc.weapon_object.is_empty = mock.MagicMock(return_value=empty)
    return sc


def get_mock_block_action(x=11, y=23, z=31, value=BUILD_BLOCK):
    cont = mock.MagicMock()
    type(cont).x = mock.PropertyMock(return_value=x)
    type(cont).y = mock.PropertyMock(return_value=y)
    type(cont).z = mock.PropertyMock(return_value=z)
    type(cont).value = mock.PropertyMock(return_value=value)
    return cont


class ServerConnectionTest(TestCase):

    @mock.patch('pyspades.player.block_action')
    def setUp(self, gba):
        self.gba = gba
        self.gba_x = mock.PropertyMock(return_value=0)
        type(gba).x = self.gba_x
        self.gba_y = mock.PropertyMock(return_value=0)
        type(gba).y = self.gba_y
        self.gba_z = mock.PropertyMock(return_value=0)
        type(gba).z = self.gba_z
        self.gba_value = mock.PropertyMock(return_value=0)
        type(gba).value = self.gba_value
        self.gba_player_id = mock.PropertyMock(return_value=0)
        type(gba).player_id = self.gba_player_id

    def test_on_block_action_recieved_no_hp(self):
        """ If a player has no HP nothing should change since the player is
        dead.
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=BUILD_BLOCK)
        p = get_mock_player(hp=0, blocks=29)
        p.on_block_action_recieved(ba)
        assert p.blocks == 29
        self.gba_x.assert_not_called()
        self.gba_y.assert_not_called()
        self.gba_z.assert_not_called()
        self.gba_value.assert_not_called()
        self.gba_player_id.assert_not_called()

    def test_on_block_action_recieved_empty_weapon(self):
        """ If a player has a weapon equipped and the weapon is empty, nothing
        should change since no action will be taken.
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=DESTROY_BLOCK)
        p = get_mock_player(blocks=29, tool=WEAPON_TOOL,
                            weapon=RIFLE_WEAPON, empty=True)
        p.on_block_action_recieved(ba)
        assert p.blocks == 29
        self.gba_x.assert_not_called()
        self.gba_y.assert_not_called()
        self.gba_z.assert_not_called()
        self.gba_value.assert_not_called()
        self.gba_player_id.assert_not_called()

    def test_on_block_action_recieved_working_weapon(self):
        """ If a player has a weapon equipped and the weapon is working, they
        can pick up blocks. Make sure that the players blocks and the
        block_action are updated correctly if they target a valid block.
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=DESTROY_BLOCK)
        p = get_mock_player(blocks=29, tool=WEAPON_TOOL,
                            weapon=RIFLE_WEAPON, empty=False)
        p.on_block_action_recieved(ba)
        assert p.blocks == 30
        self.gba_x.assert_called_once_with(11)
        self.gba_y.assert_called_once_with(23)
        self.gba_z.assert_called_once_with(31)
        self.gba_value.assert_called_once_with(DESTROY_BLOCK)
        self.gba_player_id.assert_called_once_with(42)

    def test_on_block_action_recieved_with_spade(self):
        """ If a player has a spade equipped they can pick up blocks. Make sure.
        sure that the players blocks and the block_action are updated correctly
        if they target a valid block.
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=SPADE_DESTROY)
        p = get_mock_player(blocks=29, tool=SPADE_TOOL,
                            weapon=None, empty=False)
        p.on_block_action_recieved(ba)
        assert p.blocks == 29
        self.gba_x.assert_called_once_with(11)
        self.gba_y.assert_called_once_with(23)
        self.gba_z.assert_called_once_with(31)
        self.gba_value.assert_called_once_with(SPADE_DESTROY)
        self.gba_player_id.assert_called_once_with(42)

    def test_on_block_action_recieved_block_tool(self):
        """ If the player has the block tool equipped they can place blocks.
        Make sure that the players blocks as well as the block_action is
        updated  correctly when puting a block in a valid position
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=BUILD_BLOCK)
        p = get_mock_player(blocks=29, tool=BLOCK_TOOL)
        p.on_block_action_recieved(ba)
        assert p.blocks == 28
        self.gba_x.assert_called_once_with(11)
        self.gba_y.assert_called_once_with(23)
        self.gba_z.assert_called_once_with(31)
        self.gba_value.assert_called_once_with(BUILD_BLOCK)
        self.gba_player_id.assert_called_once_with(42)

    def test_on_block_action_recieved_too_few_blocks(self):
        """ When placing blocks the player must have enogh blocks available.
        Make sure that that the players blocks and the block_action are updated
        correctly when placing a block in a valid position with a valid tool
        but with too few blocks.
        """

        player.block_action = self.gba
        ba = get_mock_block_action(value=BUILD_BLOCK)
        p = get_mock_player(blocks=-6, tool=BLOCK_TOOL)
        p.on_block_action_recieved(ba)
        assert p.blocks == -7
        self.gba_x.assert_not_called()
        self.gba_y.assert_not_called()
        self.gba_z.assert_not_called()
        self.gba_value.assert_not_called()
        self.gba_player_id.assert_not_called()
