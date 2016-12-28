"""
Pinpoint players and bookmark tunnels without making the enemy aware.
Markers attempt to help teams communicate and so, cooperate.

Markers are just symbols built with blocks at the very top of the map, which
only your team can see. They'll show up on your teammates' map and minimap,
and can be brought up in a number of ways.

* Double-tapping the SNEAK key lets you quickly spot an enemy's location.
* When your intel is stolen a marker is dropped where it just was, shadowing
  its position and eliminating "I forgot where it was" situations.
* Enemy positions are automatically revealed when the intel is captured,
  mimicking the old 'radar' reward.
* Say !tunnel in teamchat to make an arrow where you're standing, instruct other
  players to do something for a change with !build, or meet up with someone
  else using !here.

Players can type /clear to get rid of markers on their own screen.
Admins can disable or enable placing of new markers using /togglemarkers.
/togglemarkers <player> toggles only that player's ability to do so.

Any functionality can be disabled switching off SHADOW_INTEL, REVEAL_ENEMIES,
VV_ENABLED and CHAT_MARKERS below.

Maintainer: hompy
"""

import csv
from StringIO import StringIO
from collections import deque, defaultdict
from functools import partial
from itertools import izip, islice, chain
from random import choice
from twisted.internet.reactor import callLater, seconds
from pyspades.world import cube_line
from pyspades.server import block_action, block_line, set_color, chat_message
from pyspades.common import make_color, to_coordinates
from pyspades.constants import *
from commands import add, admin, get_player, name

SHADOW_INTEL = True # if True, shows where the intel used to be before taken
REVEAL_ENEMIES = True # if True, mimics old intel reveal behavior when captured
VV_ENABLED = True # if True, enables spotting by pressing SNEAK two times
CHAT_MARKERS = True # if True, enables !build !tunnel etc teamchat triggers

S_SPOTTED = '(enemy spotted at {coords}!)'
S_CLEARED = 'Markers cleared'
S_FAIL = "Couldn't place the remote marker because you were looking at the sky"
S_WAIT = 'You must wait until you can place another marker'
S_PLAYER_ENABLED = '{player} can place markers again'
S_PLAYER_DISABLED = '{player} is disallowed from placing markers'
S_ENABLED = 'Markers have been enabled'
S_DISABLED = 'Markers have been disabled'
S_TEAMCHAT = 'Markers work only IN TEAMCHAT! Type /markers for more info'
S_REACHED_LIMIT = 'Your team has too many markers of that kind!'
S_HELP = [
    "* Press V twice to SPOT an enemy, showing it on your teammates' map",
    '* You can also say "!help" IN TEAMCHAT to drop a marker where you are',
    '* (other markers: !build !tunnel !here)'
]

COOLDOWN = 10.0
VV_TIMEFRAME = 0.5
THERE_RAY_LENGTH = 192.0
ENEMY_EXPIRE_DISTANCE_SQUARED = 18.0 ** 2

def clear(connection):
    if connection not in connection.protocol.players:
        raise ValueError()
    connection.destroy_markers()
    return S_CLEARED

@name('togglemarkers')
@admin
def toggle_markers(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
        player.allow_markers = not player.allow_markers
        message = S_PLAYER_ENABLED if player.allow_markers else S_PLAYER_DISABLED
        message = message.format(player = player.name)
        protocol.send_chat(message, irc = True)
    else:
        protocol.allow_markers = not protocol.allow_markers
        message = S_ENABLED if protocol.allow_markers else S_DISABLED
        connection.protocol.send_chat(message, irc = True)

def markers(connection):
    if connection not in connection.protocol.players:
        raise ValueError()
    connection.send_lines(S_HELP)

add(clear)
add(toggle_markers)
add(markers)

class BaseMarker():
    name = 'Marker'
    triggers = []
    background = None
    background_class = None
    duration = None
    color = None
    random_colors = None
    team_color = False
    lines = []
    points = []
    always_there = False
    maximum_instances = None
    expire_call = None
    z = 0
    
    def __init__(self, protocol, team, x, y):
        self.protocol = protocol
        self.team = team
        self.x = x
        self.y = y
        if self.random_colors:
            self.color = choice(self.random_colors)
        elif self.team_color:
            self.color = make_color(*team.color)
        self.blocks = set()
        base_lines, base_points = self.lines, self.points
        self.lines, self.points = [], []
        for line in base_lines:
            self.make_line(*line)
        for point in base_points:
            self.make_block(*point)
        # find markers we're colliding with
        has_timer = self.duration is not None
        collisions = []
        current_time = seconds()
        worst_time = current_time + self.duration if has_timer else None
        for marker in protocol.markers:
            intersect = marker.blocks & self.blocks
            if intersect:
                self.blocks -= intersect
                collisions.append(marker)
                if has_timer and marker.expire_call:
                    worst_time = min(worst_time, marker.expire_call.getTime())
        # forward expiration time so that colliding markers vanish all at once
        if has_timer:
            delay = worst_time - current_time
            self.expire_call = callLater(delay, self.expire)
        self.build()
        team.marker_count[self.__class__] += 1
        protocol.markers.append(self)
        if self.background_class:
            self.background = self.background_class(protocol, team, x, y)
    
    def release(self):
        if self.expire_call and self.expire_call.active():
            self.expire_call.cancel()
        self.expire_call = None
        self.team.marker_count[self.__class__] -= 1
        self.protocol.markers.remove(self)
    
    def expire(self):
        self.destroy()
        self.release()
        if self.background:
            self.background.expire()
    
    @classmethod
    def is_triggered(cls, chat):
        return any(word in chat for word in cls.triggers)
    
    def make_block(self, x, y):
        x += self.x
        y += self.y
        if x < 0 or y < 0 or x >= 512 or y >= 512:
            return
        block = (x, y, self.z)
        self.blocks.add(block)
        self.points.append(block)
    
    def make_line(self, x1, y1, x2, y2):
        x1 = max(0, min(511, self.x + x1))
        y1 = max(0, min(511, self.y + y1))
        x2 = max(0, min(511, self.x + x2))
        y2 = max(0, min(511, self.y + y2))
        z = self.z
        line = (x1, y1, z, x2, y2, z)
        self.blocks.update(cube_line(*line))
        self.lines.append(line)
    
    def build(self, sender = None):
        sender = sender or self.protocol.send_contained
        self.send_color(sender)
        for line in self.lines:
            self.send_line(sender, *line)
        for point in self.points:
            self.send_block(sender, *point)
    
    def destroy(self, sender = None):
        # breaking a single block would make it come tumbling down, so we have
        # to destroy them all at once
        sender = sender or self.protocol.send_contained
        for block in self.blocks:
            self.send_block_remove(sender, *block)
    
    def send_color(self, sender):
        set_color.value = self.color
        set_color.player_id = 32
        sender(set_color, team = self.team)
    
    def send_block(self, sender, x, y, z, value = BUILD_BLOCK):
        block_action.value = value
        block_action.player_id = 32
        block_action.x = x
        block_action.y = y
        block_action.z = z
        sender(block_action, team = self.team)
    
    def send_line(self, sender, x1, y1, z1, x2, y2, z2):
        block_line.player_id = 32
        block_line.x1 = x1
        block_line.y1 = y1
        block_line.z1 = z1
        block_line.x2 = x2
        block_line.y2 = y2
        block_line.z2 = z2
        sender(block_line, team = self.team)
    
    def send_block_remove(self, sender, x, y, z):
        self.send_block(sender, x, y, z, DESTROY_BLOCK)

def parse_string_map(xs_and_dots):
    # greedily attempt to get the least amount of lines and blocks required
    # to build the shape. best (worst) function ever
    reader = csv.reader(StringIO(xs_and_dots), delimiter = ' ')
    rows = [s for s in (''.join(row) for row in reader) if s.strip()]
    lines, points = [], []
    if not rows:
        return lines, points
    
    width, height = len(rows[0]), len(rows)
    off_x, off_y = -width // 2, -height // 2
    for y, row in enumerate(rows):
        columns = [''.join(l[y:]).split('.', 1)[0] for l in izip(*rows)]
        it = enumerate(columns)
        for x, column in it:
            h = len(row[x:].split('.', 1)[0])
            v = len(column)
            if h == v == 0:
                continue
            if max(h, v) == 1:
                points.append((x + off_x, y + off_y))
            elif h >= v:
                lines.append((x + off_x, y + off_y, x + off_x + h - 1, y + off_y))
                row = '.' * (x + h) + row[(x + h):]
                next(islice(it, h, h), None) # forward the iterator
            else:
                lines.append((x + off_x, y + off_y, x + off_x, y + off_y + v - 1))
                rows[y:y + v] = (r[:x] + '.' + r[x + 1:] for r in rows[y:y + v])
    return lines, points

class EnemyBackground(BaseMarker):
    color = make_color(0, 0, 0)
    s = """
    . . X X X X X . .
    . X X X X X X X .
    X X X X X X X X X
    X X X X X X X X X
    X X X X X X X X X
    X X X X X X X X X
    X X X X X X X X X
    . X X X X X X X .
    . . X X X X X . .
    """

class Enemy(BaseMarker):
    name = 'Point'
    background_class = EnemyBackground
    duration = 40.0
    always_there = True
    color = make_color(255, 0, 0)
    s = """
    . . X X X . .
    . X X X X X .
    X X X X X X X
    X X X X X X X
    X X X X X X X
    . X X X X X .
    . . X X X . .
    """

class Here(BaseMarker):
    name = 'Circle'
    triggers = ['!here']
    duration = 60.0
    random_colors = [
        make_color(192, 255,   0), # lime green
        make_color(255, 255,   0), # yellow
        make_color(255, 192,   0), # orange
        make_color(255, 192, 255), # light pink
        make_color(  0, 192, 255)  # light blue
    ]
    s = """
    . . X X X X X . .
    . X X X X X X X .
    X X X . . . X X X
    X X . . . . . X X
    X X . . . . . X X
    X X . . . . . X X
    X X X . . . X X X
    . X X X X X X X .
    . . X X X X X . .
    """

class BackupBackground(BaseMarker):
    color = make_color(0, 0, 0)
    s = """
    . X X X X .
    X X X X X X
    X X X X X X
    X X X X X X
    X X X X X X
    X X X X X X
    X X X X X X
    . X X X X .
    . X X X X .
    . X X X X .
    . X X X X .
    . X X X X .
    . X X X X .
    """

class Backup(BaseMarker):
    name = 'Exclamation'
    background_class = BackupBackground
    triggers = ['!backup', '!support', '!airstrike', '!danger', '!help']
    duration = 2 * 60.0
    color = make_color(255, 0, 0)
    s = """
    . X X .
    X X X X
    X X X X
    X X X X
    X X X X
    . X X .
    . X X .
    . X X .
    . . . .
    . X X .
    . X X .
    """

class Intel(BaseMarker):
    name = 'Intel'
    color = make_color(255, 255, 255)
    s = """
    . . . X X X X X X . . .
    . . . . . . . . . . . .
    . . . . X X X X . . . .
    X . . . . . . . . . . X
    X . X . . X X . . X . X
    X . X . X X X X . X . X
    X . X . X X X X . X . X
    X . X . . X X . . X . X
    X . . . . . . . . . . X
    . . . . X X X X . . . .
    . . . . . . . . . . . .
    . . . X X X X X X . . .
    """

class BuildBackground(BaseMarker):
    color = make_color(255, 255, 255)
    s = """
    . . . . . X X X . . . . .
    . . . X X X X X X X . . .
    . X X X X X X X X X X X .
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    X X X X X X X X X X X X X
    . . X X X X X X X X X . .
    . . . . X X X X X . . . .
    """

class Build(BaseMarker):
    name = 'Cube'
    triggers = ['!build', '!bunker', '!bridge', '!fort']
    duration = 5 * 60.0
    maximum_instances = 6
    team_color = True
    background_class = BuildBackground
    s = """
    . . . . . X . . . . .
    . . . X X X X X . . .
    . X X X X X X X X X .
    X . . X X X X X . . X
    X X X . . X . . X X X
    X X X X X . X X X X X
    X X X X X . X X X X X
    X X X X X . X X X X X
    X X X X X . X X X X X
    X X X X X . X X X X X
    . . X X X . X X X . .
    . . . . X . X . . . .
    """

class TunnelBackground(BaseMarker):
    color = make_color(255, 255, 255)
    s = """
    . . X X X X X X X . .
    . . X X X X X X X . .
    . . X X X X X X X . .
    . . X X X X X X X . .
    X X X X X X X X X X X
    X X X X X X X X X X X
    X X X X X X X X X X X
    . X X X X X X X X X .
    . . X X X X X X X . .
    . . . X X X X X . . .
    . . . . X X X . . . .
    """

class Tunnel(BaseMarker):
    name = 'Arrow'
    background_class = TunnelBackground
    triggers = ['!tunnel', '!arrow']
    duration = 5 * 60.0
    maximum_instances = 6
    team_color = True
    s = """
    . . X X X X X . .
    . . X X X X X . .
    . . X X X X X . .
    . . X X X X X . .
    X X X X X X X X X
    . X X X X X X X .
    . . X X X X X . .
    . . . X X X . . .
    . . . . X . . . .
    """

class NumberMarker(BaseMarker):
    duration = Enemy.duration
    background_class = Enemy
    color = make_color(255, 255, 255)
    always_there = True

class Zero(NumberMarker):
    name = '0'
    triggers = ['!0']
    s = """
    . X X X .
    X X . X X
    X X . X X
    X X . X X
    X X . X X
    X X . X X
    . X X X .
    """

class One(NumberMarker):
    name = '1'
    triggers = ['!1']
    s = """
    . X X X .
    . . X X .
    . . X X .
    . . X X .
    . . X X .
    . . X X .
    . X X X X
    """

class Two(NumberMarker):
    name = '2'
    triggers = ['!2']
    s = """
    . X X X .
    X X . X X
    . . . X X
    . . X X .
    . X X . .
    X X . . .
    X X X X X
    """

class Three(NumberMarker):
    name = '3'
    triggers = ['!3']
    s = """
    . X X X .
    X X . X X
    . . . X X
    . . X X .
    . . . X X
    X X . X X
    . X X X .
    """

class Four(NumberMarker):
    name = '4'
    triggers = ['!4']
    s = """
    X X . X X
    X X . X X
    X X . X X
    . X X X X
    . . . X X
    . . . X X
    . . . X X
    """

class Five(NumberMarker):
    name = '5'
    triggers = ['!5']
    s = """
    X X X X X
    X X . . .
    X X . . .
    X X X X .
    . . . X X
    . . . X X
    X X X X .
    """

class Six(NumberMarker):
    name = '6'
    triggers = ['!6']
    s = """
    . X X X .
    X X . X X
    X X . . .
    X X X X .
    X X . X X
    X X . X X
    . X X X .
    """

class Seven(NumberMarker):
    name = '7'
    triggers = ['!7']
    s = """
    X X X X X
    . . . X X
    . . . X X
    . . X X .
    . X X . .
    X X . . .
    X X . . .
    """

class Eight(NumberMarker):
    name = '8'
    triggers = ['!8']
    s = """
    . X X X .
    X X . X X
    X X . X X
    . X X X .
    X X . X X
    X X . X X
    . X X X .
    """

class Nine(NumberMarker):
    name = '9'
    triggers = ['!9']
    s = """
    . X X X .
    X X . X X
    X X . X X
    . X X X X
    . . . X X
    X X . X X
    . X X X .
    """

# in triggering order
number_markers = [Zero, One, Two, Three, Four, Five, Six, Seven, Eight, Nine]
trigger_markers = [Tunnel, Backup, Build] + number_markers + [Here]
other_markers = [Enemy, Intel]
background_markers = []

# turn bitmap into line and block instructions
for cls in chain(trigger_markers, other_markers, background_markers):
    if cls.background_class:
        background_markers.append(cls.background_class)
    cls.lines, cls.points = parse_string_map(cls.s)

def apply_script(protocol, connection, config):
    class MarkerConnection(connection):
        allow_markers = True
        last_marker = None
        sneak_presses = None
        
        def send_markers(self):
            is_self = lambda player: player is self
            send_me = partial(self.protocol.send_contained, rule = is_self)
            for marker in self.protocol.markers:
                marker.build(send_me)
        
        def destroy_markers(self):
            is_self = lambda player: player is self
            send_me = partial(self.protocol.send_contained, rule = is_self)
            for marker in self.protocol.markers:
                marker.destroy(send_me)
        
        def make_marker(self, marker_class, location):
            marker_max = marker_class.maximum_instances
            if (marker_max is not None and
                self.team.marker_count[marker_class] >= marker_max):
                self.send_chat(S_REACHED_LIMIT)
                return
            new_marker = marker_class(self.protocol, self.team, *location)
            self.last_marker = seconds()
        
        def on_animation_update(self, jump, crouch, sneak, sprint):
            markers_allowed = (VV_ENABLED and self.allow_markers and
                self.protocol.allow_markers)
            if markers_allowed and sneak and self.world_object.sneak != sneak:
                now = seconds()
                if self.last_marker is None or now - self.last_marker > COOLDOWN:
                    presses = self.sneak_presses
                    presses.append(now)
                    if len(presses) == 2 and presses[0] >= now - VV_TIMEFRAME:
                        location = self.get_there_location()
                        if location:
                            coords = to_coordinates(*location)
                            chat_message.chat_type = CHAT_TEAM
                            chat_message.player_id = self.player_id
                            chat_message.value = S_SPOTTED.format(coords = coords)
                            self.protocol.send_contained(chat_message, team =
                                self.team)
                            self.make_marker(Enemy, location)
                            presses.clear()
            return connection.on_animation_update(self, jump, crouch, sneak,
                sprint)
        
        def on_chat(self, value, global_message):
            markers_allowed = self.allow_markers and self.protocol.allow_markers
            if CHAT_MARKERS and markers_allowed and not self.team.spectator:
                chat = value.lower()
                try:
                    marker_class = next(cls for cls in trigger_markers if
                        cls.is_triggered(chat))
                except StopIteration:
                    pass
                else:
                    if global_message:
                        self.send_chat(S_TEAMCHAT)
                    elif (self.last_marker is not None and
                        seconds() - self.last_marker <= COOLDOWN):
                        self.send_chat(S_WAIT)
                    else:
                        location = None
                        if marker_class.always_there or 'there' in chat:
                            location = self.get_there_location()
                            if location is None:
                                self.send_chat(S_FAIL)
                        else:
                            x, y, z = self.get_location()
                            location = (x + 6 if self.team.id == 0 else x - 6, y)
                        if location:
                            self.make_marker(marker_class, location)
            return connection.on_chat(self, value, global_message)
        
        def on_login(self, name):
            self.send_markers()
            self.sneak_presses = deque(maxlen = 2)
            connection.on_login(self, name)
        
        def on_team_changed(self, old_team):
            if old_team and not old_team.spectator:
                new_team, self.team = self.team, old_team
                self.destroy_markers()
                self.team = new_team
            if self.team and not self.team.spectator:
                self.send_markers()
            connection.on_team_changed(self, old_team)
        
        def on_kill(self, killer, type, grenade):
            x1, y1, z1 = self.get_location()
            closest, best_distance = None, None
            for marker in self.protocol.markers:
                if marker.name == Enemy.name:
                    x, y = x1 - marker.x, y1 - marker.y
                    distance = x * x + y * y
                    if distance > ENEMY_EXPIRE_DISTANCE_SQUARED:
                        continue
                    if not closest or distance < best_distance:
                        closest, best_distance = marker, distance
            if closest:
                closest.expire()
            return connection.on_kill(self, killer, type, grenade)
        
        def on_flag_take(self):
            if SHADOW_INTEL and self.protocol.allow_markers:
                enemy_team = self.team.other
                x, y, z = self.get_location()
                marker = Intel(self.protocol, enemy_team, x, y)
                enemy_team.intel_marker = marker
            return connection.on_flag_take(self)
        
        def on_flag_capture(self):
            enemy_team = self.team.other
            if SHADOW_INTEL and enemy_team.intel_marker:
                enemy_team.intel_marker.expire()
                enemy_team.intel_marker = None
            if REVEAL_ENEMIES and self.protocol.allow_markers:
                delay = 0.25
                for call in self.team.marker_calls:
                    if call.active():
                        call.cancel()
                self.team.marker_calls = []
                for player in enemy_team.get_players():
                    x, y, z = player.get_location()
                    delay += 0.15
                    call = callLater(delay, Enemy, self.protocol, self.team, x, y)
                    self.team.marker_calls.append(call)
            connection.on_flag_capture(self)
        
        def on_flag_drop(self):
            enemy_team = self.team.other
            if SHADOW_INTEL and enemy_team.intel_marker:
                enemy_team.intel_marker.expire()
                enemy_team.intel_marker = None
            connection.on_flag_drop(self)
        
        def get_there_location(self):
            location = self.world_object.cast_ray(THERE_RAY_LENGTH)
            return location[:2] if location else None
    
    class MarkerProtocol(protocol):
        allow_markers = True
        markers = None
        
        def on_map_change(self, map):
            for team in (self.blue_team, self.green_team):
                team.intel_marker = None
                team.marker_calls = []
                team.marker_count = defaultdict(int)
            self.markers = []
            protocol.on_map_change(self, map)
        
        def on_map_leave(self):
            for marker in self.markers[:]:
                marker.release()
            self.markers = None
            for team in (self.blue_team, self.green_team):
                team.intel_marker = None
                for call in team.marker_calls:
                    if call.active():
                        call.cancel()
                team.marker_calls = None
                team.marker_count = None
            protocol.on_map_leave(self)
    
    return MarkerProtocol, MarkerConnection