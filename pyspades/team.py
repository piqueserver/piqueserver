from typing import Tuple
from pyspades.constants import (
    BLUE_FLAG, GREEN_FLAG,
    CTF_MODE,
    BLUE_BASE, GREEN_BASE,
)
from pyspades.entities import Flag, Base
from pyspades.protocol import BaseProtocol


class Team:
    score = None
    flag = None
    base = None
    other = None
    protocol = None
    name = None
    kills = None

    def __init__(self, team_id: int, name: str, color: Tuple[int, int, int],
                 spectator: bool, protocol: BaseProtocol) -> None:
        self.id = team_id
        self.name = name
        self.protocol = protocol
        self.color = color
        self.spectator = spectator

    def get_players(self) -> None:
        for player in self.protocol.players.values():
            if player.team is self:
                yield player

    def count(self) -> int:
        count = 0
        for player in self.protocol.players.values():
            if player.team is self:
                count += 1
        return count

    def initialize(self) -> None:
        if self.spectator:
            return
        self.score = 0
        self.kills = 0
        if self.protocol.game_mode == CTF_MODE:
            self.set_flag()
            self.set_base()

    def set_flag(self) -> Flag:
        entity_id = [BLUE_FLAG, GREEN_FLAG][self.id]
        if self.flag is None:
            self.flag = Flag(entity_id, self.protocol)
            self.flag.team = self
            self.protocol.entities.append(self.flag)
        location = self.get_entity_location(entity_id)
        returned = self.protocol.on_flag_spawn(location[0], location[1],
                                               location[2], self.flag, entity_id)
        if returned is not None:
            location = returned
        self.flag.set(*location)
        self.flag.player = None
        return self.flag

    def set_base(self) -> Base:
        entity_id = [BLUE_BASE, GREEN_BASE][self.id]
        if self.base is None:
            self.base = Base(entity_id, self.protocol)
            self.base.team = self
            self.protocol.entities.append(self.base)
        location = self.get_entity_location(entity_id)
        returned = self.protocol.on_base_spawn(location[0], location[1],
                                               location[2], self.base, entity_id)
        if returned is not None:
            location = returned
        self.base.set(*location)
        return self.base

    def get_entity_location(self, entity_id: int) -> Tuple[int, int, int]:
        return self.get_random_location(True)

    def get_random_location(self, force_land: bool = False) -> Tuple[int, int, int]:
        x_offset = self.id * 384
        return self.protocol.get_random_location(force_land, (
            x_offset, 128, 128 + x_offset, 384))

    def get_entities(self):
        for item in self.protocol.entities:
            if item.team is self:
                yield item

    def __repr__(self):
        return "{}(id={}, name={}, color={}, spectator={}, protocol)".format(
            self.__class__.__name__, self.id,
            self.name, self.color, self.spectator
        )
