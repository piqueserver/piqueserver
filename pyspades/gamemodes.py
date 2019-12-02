import abc

from pyspades import contained as loaders
from pyspades.collision import vector_collision, collision_3d
from pyspades.constants import TC_CAPTURE_DISTANCE


class BaseGamemode(metaclass=abc.ABCMeta):
    """Base Game Mode. You should probably not inherit directly from this,
    unless you enjoy doing low-level protocol fumbling."""

    @abc.abstractmethod
    def get_state_loader(self):
        """called to get the loader that contains the data to be sent after the
        state data, informing the client of the game mode and it's state"""


class IntelBasedGamemode(BaseGamemode):
    """A game mode where two team each have an intel briefcase and a tent.
    Often, the goal is to bring the enemy teams intel to the tent. This class
    only implements the required packet sending, not any actual game mode
    logic"""
    name = "ctf"

    def __init__(self, protocol):
        self.protocol = protocol
        self.team_1 = protocol.team_1
        self.team_2 = protocol.team_2

        self.state_loader = loaders.CTFState()
        self.intel_drop_loader = loaders.IntelDrop()
        self.intel_pickup_loader = loaders.IntelPickup()
        self.intel_capture_loader = loaders.IntelCapture()

        # player carrying team_1's intel, not the team_1 member carrying the
        # intel
        # This should probably be reversed as it's pretty confusing
        self.team_1_carrier = None
        self.team_2_carrier = None

    def on_position_update(self, player):
        target_flag = self.get_target_flag(player)
        if vector_collision(player.world_object.position,
                            player.team.base):
            if target_flag.player is self:
                player.capture_flag()
            player.check_refill()
        if target_flag.player is None and vector_collision(
                player.position, target_flag):
            player.take_flag()

    def get_state_loader(self):
        ctf_data = self.state_loader
        ctf_data.cap_limit = self.capture_limit
        ctf_data.team1_score = self.team_1.score
        ctf_data.team2_score = self.team_2.score

        team_1_base = self.team_1.base
        team_2_base = self.team_2.base

        ctf_data.team1_base_x = team_1_base.x
        ctf_data.team1_base_y = team_1_base.y
        ctf_data.team1_base_z = team_1_base.z

        ctf_data.team2_base_x = team_2_base.x
        ctf_data.team2_base_y = team_2_base.y
        ctf_data.team2_base_z = team_2_base.z

        team_1_intel = self.team_1.intel
        team_2_intel = self.team_2.intel

        if self.team_1_carrier is None:
            ctf_data.team1_has_intel = 0
            ctf_data.team2_flag_x = team_1_intel.x
            ctf_data.team2_flag_y = team_1_intel.y
            ctf_data.team2_flag_z = team_1_intel.z
        else:
            ctf_data.team1_has_intel = 1
            ctf_data.team2_carrier = self.team_2_carrier.player_id

        if self.team_2_carrier is None:
            ctf_data.team2_has_intel = 0
            ctf_data.team1_flag_x = team_2_intel.x
            ctf_data.team1_flag_y = team_2_intel.y
            ctf_data.team1_flag_z = team_2_intel.z
        else:
            ctf_data.team2_has_intel = 1
            ctf_data.team1_carrier = self.team_1_carrier.player_id

        return ctf_data

    @property
    @abc.abstractmethod
    def capture_limit(self):
        pass

    def on_player_reset(self, player):
        flag = self.get_player_flag(player)

        if flag is None:
            return

        position = player.position
        x = int(position.x)
        y = int(position.y)
        z = max(0, int(position.z))
        z = self.protocol.map.get_z(x, y, z)
        flag.set(x, y, z)
        flag.player = None
        intel_drop = loaders.IntelDrop()
        intel_drop.player_id = player.player_id
        intel_drop.x = flag.x
        intel_drop.y = flag.y
        intel_drop.z = flag.z
        self.protocol.broadcast_contained(intel_drop, save=True)
        player.on_flag_drop()

    def get_player_flag(self, player):
        for flag in (self.blue_flag, self.green_flag):
            if flag.player is self:
                return flag

        return None

    def get_target_flag(self, connection):
        return connection.team.other_flag


class TerritoryBasedGamemode(BaseGamemode):
    name = "tc"

    def __init__(self, protocol):
        self.protocol = protocol
        self.control_points = self.make_control_points()
        self.state_loader = loaders.TCState()

    @abc.abstractmethod
    def make_control_points():
        pass

    def get_state_packet(self):
        tc_data = self.state_loader
        tc_data.set_entities(self.control_points)
        return tc_data

    def on_position_update(self, connection):
        for entity in self.protocol.entities:
            collides = vector_collision(
                entity, connection.world_object.position, TC_CAPTURE_DISTANCE)
            if self in entity.players:
                if not collides:
                    entity.remove_player(self)
            else:
                if collides:
                    entity.add_player(self)
            if collides and vector_collision(entity,
                                             connection.world_object.position):
                connection.check_refill()
