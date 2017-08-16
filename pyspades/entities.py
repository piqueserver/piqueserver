from pyspades.constants import NEUTRAL_TEAM, TC_CAPTURE_RATE, SPAWN_RADIUS
from pyspades.common import Vertex3
from pyspades import contained as loaders

from twisted.internet import reactor

move_object = loaders.MoveObject()
progress_bar = loaders.ProgressBar()
territory_capture = loaders.TerritoryCapture()

class Entity(Vertex3):
    team = None

    def __init__(self, entity_id, protocol, *arg, **kw):
        Vertex3.__init__(self, *arg, **kw)
        self.id = entity_id
        self.protocol = protocol

    def update(self):
        move_object.object_type = self.id
        if self.team is None:
            state = NEUTRAL_TEAM
        else:
            state = self.team.id
        move_object.state = state
        move_object.x = self.x
        move_object.y = self.y
        move_object.z = self.z
        self.protocol.send_contained(move_object, save=True)


class Flag(Entity):
    player = None

    def update(self):
        if self.player is not None:
            return
        Entity.update(self)


class Territory(Flag):
    progress = 0.0
    players = None
    start = None
    rate = 0
    rate_value = 0.0
    finish_call = None
    capturing_team = None

    def __init__(self, *arg, **kw):
        Flag.__init__(self, *arg, **kw)
        self.players = set()

    def add_player(self, player):
        self.get_progress(True)
        self.players.add(player)
        self.update_rate()

    def remove_player(self, player):
        self.get_progress(True)
        self.players.discard(player)
        self.update_rate()

    def update_rate(self):
        rate = 0
        for player in self.players:
            if player.team.id:
                rate += 1
            else:
                rate -= 1
        progress = self.progress
        if ((progress == 1.0 and (rate > 0 or rate == 0)) or
                (progress == 0.0 and (rate < 0 or rate == 0))):
            return
        self.rate = rate
        self.rate_value = rate * TC_CAPTURE_RATE
        if self.finish_call is not None:
            self.finish_call.cancel()
            self.finish_call = None
        if rate != 0:
            self.start = reactor.seconds()
            rate_value = self.rate_value
            if rate_value < 0:
                self.capturing_team = self.protocol.blue_team
                end_time = progress / -rate_value
            else:
                self.capturing_team = self.protocol.green_team
                end_time = (1.0 - progress) / rate_value
            if self.capturing_team is not self.team:
                self.finish_call = reactor.callLater(end_time, self.finish)
        self.send_progress()

    def send_progress(self):
        progress_bar.object_index = self.id
        if self.team is None:
            capturing_team = self.capturing_team
            team = capturing_team.other
        else:
            capturing_team = self.team.other
            team = self.team
        progress_bar.capturing_team = capturing_team.id
        rate = self.rate
        progress = self.get_progress()
        if team.id:
            rate = -rate
            progress = 1 - progress
        progress_bar.progress = progress
        progress_bar.rate = rate
        self.protocol.send_contained(progress_bar)

    def finish(self):
        self.finish_call = None
        protocol = self.protocol
        if self.rate > 0:
            team = protocol.green_team
        else:
            team = protocol.blue_team
        team.score += 1
        if self.team is not None:
            self.team.score -= 1
        self.team = team
        protocol.on_cp_capture(self)
        if team.score >= protocol.max_score:
            protocol.reset_game(territory=self)
            protocol.on_game_end()
        else:
            territory_capture.object_index = self.id
            territory_capture.state = self.team.id
            territory_capture.winning = False
            protocol.send_contained(territory_capture)

    def get_progress(self, set=False):
        """
        Return progress (between 0 and 1 - 0 is full blue control,
        1 is full green control) and optionally set the current
        progress.
        """
        # TODO: wtf is this thing, and why are we setting values in
        # a getter. Should this be refactored into two functions
        # called `update_progress` and `get_progress` instead?
        rate = self.rate_value
        if rate == 0.0 or self.start is None:
            return self.progress
        dt = reactor.seconds() - self.start
        progress = max(0, min(1, self.progress + rate * dt))
        if set:
            self.progress = progress
        return progress

    def get_spawn_location(self):
        x1 = max(0, self.x - SPAWN_RADIUS)
        y1 = max(0, self.y - SPAWN_RADIUS)
        x2 = min(512, self.x + SPAWN_RADIUS)
        y2 = min(512, self.y + SPAWN_RADIUS)
        return self.protocol.get_random_location(True, (x1, y1, x2, y2))


class Base(Entity):
    pass
