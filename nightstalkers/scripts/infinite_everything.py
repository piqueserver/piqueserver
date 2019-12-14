"""
Derived from two scripts:
- infiniclip.py written by Leif_The_Head
- infiblocks.py written by ???

Frankenmerged and ported to piqueserver by GreaseMonkey in 2019
"""

from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type

from piqueserver.commands import command
from pyspades import contained as loaders # type: ignore

from pyspades.player import ServerConnection
from pyspades.server import ServerProtocol


class InfiniteEverythingConnectionInterface(ServerConnection, metaclass=ABCMeta):
    infinite_everything = True


@command()
def toggle_infinite(connection: InfiniteEverythingConnectionInterface) -> Optional[str]:
    protocol = connection.protocol
    if connection.player_id in protocol.players:
        connection.infinite_everything = not connection.infinite_everything
        return "You are {} infinite mode.".format(["out of", "now in"][int(connection.infinite_everything)])

    return None


def apply_script(protocol: Type["ServerProtocol"], connection: Type["ServerConnection"], config: Any) -> Tuple[Type["ServerProtocol"], Type["ServerConnection"]]:

    class InfiniteEverythingConnection(InfiniteEverythingConnectionInterface, connection):
        def on_block_build(self, x: int, y: int, z: int) -> None:
            if self.infinite_everything:
                self.refill()
            return super().on_block_build(x, y, z)

        def on_line_build(self, points: Sequence[Tuple[int, int, int]]) -> None:
            if self.infinite_everything:
                self.refill()
            return super().on_line_build(points)

        def on_shoot_set(self, fire: int) -> None:
            if self.infinite_everything:
                weapon = self.weapon_object
                if weapon is not None:
                    was_shooting = weapon.shoot
                    weapon.reset()
                    weapon_reload = loaders.WeaponReload()
                    weapon_reload.player_id = self.player_id
                    weapon_reload.clip_ammo = weapon.ammo
                    weapon_reload.reserve_ammo = weapon.stock
                    weapon.set_shoot(was_shooting)
                    self.send_contained(weapon_reload)
            return super().on_shoot_set(fire)

        def on_grenade(self, time_left: float) -> Optional[bool]:
            if self.infinite_everything:
                self.refill()
            return super().on_grenade(time_left)

    return protocol, InfiniteEverythingConnection

