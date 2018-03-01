from .networking import loaders
from .world.collision import vector_collision, collision_3d
from .constants import TC_CAPTURE_DISTANCE

ctf_data = loaders.CTFState()
tc_data = loaders.TCState()

class IntelBasedGamemode(object):
    name = "ctf"
    def __init__(self, protocol):
        self.protocol = protocol
        self.green_flag = protocol.green_team.flag
        self.blue_flag = protocol.blue_team.flag

        self.state_loader = loaders.CTFState()
        self.drop_intel_loader = loaders.IntelDrop()
        self.drop_pickup_loader = loaders.IntelPickup()
        self.drop_capture_loader = loaders.IntelCapture()

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

    def get_state_packet(self):
        return

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
        intel_drop =
        intel_drop.player_id = self.player_id
        intel_drop.x = flag.x
        intel_drop.y = flag.y
        intel_drop.z = flag.z
        self.protocol.send_contained(intel_drop, save=True)
        self.on_flag_drop()

    def get_player_flag(self, player):
        for flag in (self.blue_flag, self.green_flag):
            if flag.player is self:
                return flag

        return None

    def get_target_flag(self, connection):
        return connection.team.other_flag

class TerritoryBasedGamemode(object):
    name = "tc"
    def __init__(self, protocol):
        self.protocol = protocol
        self.state_loader = loaders.TCState()

    def get_state_packet(self):
        return

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
