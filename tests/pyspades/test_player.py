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
from pyspades.constants import *

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

def get_mock_position(x=11, y=23, z=31):
    cont = mock.MagicMock()
    type(cont).x = mock.PropertyMock(return_value=x)
    type(cont).y = mock.PropertyMock(return_value=y)
    type(cont).z = mock.PropertyMock(return_value=z)
    return cont

class PlayerPosition(TestCase):

    # on_position_update_recieved
    @mock.patch('pyspades.player.position_data')
    def setUp(self, gpd): #global position data
        self.gpd = gpd
        self.gpd_x = mock.PropertyMock(return_value=0)
        type(gpd).x = self.gpd_x
        self.gpd_y = mock.PropertyMock(return_value=0)
        type(gpd).y = self.gpd_y
        self.gpd_z = mock.PropertyMock(return_value=0)
        type(gpd).z = self.gpd_z
        self.gpd_value = mock.PropertyMock(return_value=0)
        type(gpd).value = self.gpd_value
        self.gpd_player_id = mock.PropertyMock(return_value=0)
        type(gpd).player_id = self.gpd_player_id

    # @patch.object(SomeClass, 'class_method')
    # ... def test(mock_method):
    # ...     SomeClass.class_method(3)
    # ...     mock_method.assert_called_with(3)

    @mock.patch.object(ServerConnection, 'on_hack_attempt')
    def test_no_hack(self, hack_method):
        """ Sanitize bad positions to foil hackers.
        """
        player.position_data = self.gpd
        mock_pos = get_mock_position(x=float('nan'))
        mock_player = get_mock_player()
        mock_player.on_position_update_recieved(mock_pos)

        hack_method.assert_called_with('Invalid position data received')

    @mock.patch.object(ServerConnection, 'last_position_update')
    def test_no_move_if_dead(self, last_position_update):
        """ You can't move if you are dead.
        """
        player.position_data = self.gpd
        mock_pos = get_mock_position()
        mock_player = get_mock_player(hp=0)
        mock_player.on_position_update_recieved(mock_pos)
        last_position_update.assert_not_called()

    @mock.patch.object(ServerConnection, 'is_valid_position')
    @mock.patch.object(ServerConnection, 'set_location')
    def test_position_data_remains_unchanged_position_is_invalid(self, set_location, is_valid_position):
        """ If the position data is invalid for any reason your positon isn't changed.
        """
        is_valid_position.return_value = False
        player.position_data = self.gpd
        mock_pos = get_mock_position()
        mock_player = get_mock_player()
        mock_player.on_position_update_recieved(mock_pos)
        set_location.assert_called_with()

    def test_no_set_mode(self):
        """ This path is triggered if neither CTF nor TC mode is set. This is a bug.
        """
        player.position_data = self.gpd
        mock_pos = get_mock_position()
        mock_player = get_mock_player()
        mock_player.on_position_update_recieved(mock_pos)

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
