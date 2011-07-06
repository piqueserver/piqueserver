from commands import add, admin
from pyspades.server import block_action, set_color
from pyspades.common import make_color
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.constants import *

@admin
def platform(connection):
    if connection.building_button:
        return "You're in button mode! Type /button to exit it."
    if not connection.building_platform:
        return connection.start_platform()
    else:
        return connection.end_platform()

@admin
def button(connection, value = None, type = None, speed = None):
    if connection.building_platform:
        return "You're in platform mode! Type /platform to exit it."
    if not connection.building_button:
        return connection.start_button(value, type, speed)
    else:
        return connection.cancel_button()

add(platform)
add(button)

def apply_script(protocol, connection, config):
    class Button:
        platform = None
        callback = None
        args = None
        
        def __init__(self, platform, callback, *args):
            self.platform = platform
            self.callback = callback
            self.args = args
        
        def action(self, user):
            self.callback(user, *self.args)
    
    class Platform:
        protocol = None
        cycle_call = None
        busy = False
        mode = None
        
        def __init__(self, protocol, min_x, min_y, max_x, max_y, start_z):
            self.protocol = protocol
            self.x = min_x
            self.y = min_y
            self.x2 = max_x
            self.y2 = max_y
            self.z = start_z
            self.start_z = start_z
            self.cycle_call = LoopingCall(self.cycle)
        
        def collides(self, x, y, z):
            return (x >= self.x and x < self.x2 and y >= self.y and y < self.y2
                and z <= self.start_z and z >= self.z)
        
        def start(self, user, target_z, speed):
            if self.busy:
                return False
            self.busy = True
            self.user = user
            self.last_z = self.z
            self.target_z = target_z
            self.speed = speed
            self.cycle_call.start(self.speed, now = False)
        
        def once(self, user, target_z, speed):
            speed = speed or 0.25
            if self.start(user, target_z, speed) == False:
                return
            self.mode = 'once'
        
        def elevator(self, user, target_z, speed):
            speed = speed or 0.75
            if self.start(user, target_z, speed) == False:
                return
            self.mode = 'elevator'
        
        def cycle(self):
            if self.z == self.target_z:
                self.busy = False
                self.cycle_call.stop()
                if self.mode == 'elevator':
                    self.busy = True
                    self.mode = 'once'
                    self.target_z = self.last_z
                    reactor.callLater(3.0, self.cycle_call.start, self.speed)
                return
            elif self.z > self.target_z:
                self.z -= 1
                set_color.value = make_color(255, 0, 0)
                set_color.player_id = self.user.player_id
                self.protocol.send_contained(set_color, save = True)
                block_action.value = BUILD_BLOCK
            elif self.z < self.target_z:
                block_action.value = DESTROY_BLOCK
            block_action.z = self.z
            block_action.player_id = self.user.player_id
            for x in xrange(self.x, self.x2):
                block_action.x = x
                for y in xrange(self.y, self.y2):
                    block_action.y = y
                    self.protocol.send_contained(block_action, save = True)
                    if block_action.value == BUILD_BLOCK:
                        self.protocol.map.set_point(x, y, self.z, (255, 0, 0, 255),
                            user = False)
                    else:
                        self.protocol.map.remove_point(x, y, self.z)
            if self.z < self.target_z:
                self.z += 1
    
    class PlatformConnection(connection):
        building_platform = False
        building_button = False
        button_platform = None
        platform_blocks = None
        
        def find_aux_connection(self):
            """Attempts to find a dead player"""
            for player in self.protocol.players.values():
                if player.hp <= 0:
                    return player
            return self
        
        def on_block_build(self, x, y, z):
            if self.building_platform:
                self.platform_blocks.add((x, y, z))
            if self.building_button:
                self.place_button(x, y, z)
            connection.on_block_build(self, x, y, z)
        
        def on_block_destroy(self, x, y, z, mode):
            if mode == DESTROY_BLOCK:
                if self.building_button and self.button_platform is None:
                    self.button_platform = self.protocol.check_platform(
                        x, y, z)
                    if self.button_platform is None:
                        self.send_chat('That is not a platform! Aborting '
                            'button placement.')
                        self.building_button = False
                    elif self.button_platform.start_z - self.button_height < 1:
                        self.send_chat("Sorry, but you'll have to pick a lower"
                            "height value.")
                        self.building_button = False
                    else:
                        self.send_chat('Platform selected! Now place a block '
                            'for the button.')
                    return False
                if self.protocol.buttons:
                    if (x, y, z) in self.protocol.buttons:
                        self.protocol.buttons[(x, y, z)].action(
                            self.find_aux_connection())
                        return False
            if self.protocol.check_platform(x, y, z):
                return False
            return connection.on_block_destroy(self, x, y, z, mode)
        
        def on_block_removed(self, x, y, z):
            pos = (x, y, z)
            if self.building_platform:
                self.platform_blocks.discard(pos)
            if self.protocol.buttons and pos in self.protocol.buttons:
                del self.protocol.buttons[pos]
            connection.on_block_removed(self, x, y, z)
        
        def start_platform(self):
            self.building_platform = True
            self.platform_blocks = set()
            return ('Platform construction started. Build a rectangle of the '
                'desired size.')
        
        def end_platform(self):
            self.building_platform = False
            if len(self.platform_blocks):
                min_x, min_y, max_x, max_y = None, None, None, None
                start_z = None
                bad = None
                for x, y, z in self.platform_blocks:
                    if start_z is None:
                        start_z = z
                    elif start_z != z:
                        bad = ('Bad platform. All blocks must be on a '
                            'single height.')
                        break
                    min_x = x if min_x is None else min(min_x, x)
                    min_y = y if min_y is None else min(min_y, y)
                    max_x = x if max_x is None else max(max_x, x)
                    max_y = y if max_y is None else max(max_y, y)
                max_x += 1
                max_y += 1
                for x in xrange(min_x, max_x):
                    if bad:
                        break
                    for y in xrange(min_y, max_y):
                        if (x, y, start_z) not in self.platform_blocks:
                            bad = 'Bad platform. Incomplete or uneven floor.'
                            break
                if bad:
                    block_action.value = DESTROY_BLOCK
                    block_action.player_id = self.player_id
                    for x, y, z in self.platform_blocks:
                        block_action.x = x
                        block_action.y = y
                        block_action.z = z
                        self.protocol.send_contained(block_action)
                    return bad
                p = Platform(self.protocol, min_x, min_y, max_x, max_y, start_z)
                if self.protocol.platforms is None:
                    self.protocol.platforms = []
                self.protocol.platforms.append(p)
                return 'Platform construction completed.'
            else:
                return 'Platform construction cancelled.'
        
        def start_button(self, height, type, speed):
            if height is None:
                return 'Usage: /button <height> [elevator|once] [speed]'
            self.button_height = int(height)
            if self.button_height < 0:
                return 'Height is relative to the initial platform and must be positive!'
            if type is None:
                type = 'elevator'
            type = type.lower()
            types = ['once', 'elevator']
            if type not in types:
                return ('Allowed platform types: %s' % ', '.join(types))
            self.button_type = type
            self.button_speed = float(speed) if speed is not None else None
            if self.protocol.platforms is None:
                return ('There are no platforms created yet! Use /platform to '
                    'build one')
            self.building_button = True
            self.button_platform = None
            return 'Select the platform by digging it with the pickaxe.'
        
        def cancel_button(self):
            self.building_button = False
            return 'Button placement cancelled.'
        
        def place_button(self, x, y, z):
            self.building_button = False
            p = self.button_platform
            if p is None:
                self.send_chat('Bad button. No platform selected.')
                return
            callbacks = {'once' : p.once, 'elevator' : p.elevator}
            b = Button(p, callbacks[self.button_type],
                p.start_z - self.button_height, self.button_speed)
            if self.protocol.buttons is None:
                self.protocol.buttons = {}
            self.protocol.buttons[(x, y, z)] = b
            self.send_chat('Button succesfully created!')
    
    class PlatformProtocol(protocol):
        platforms = None
        buttons = None
        
        def check_platform(self, x, y, z):
            if self.platforms is None:
                return None
            for plat in self.platforms:
                if plat.collides(x, y, z):
                    return plat
            return None
        
        def is_indestructable(self, x, y, z):
            if self.platforms:
                if self.check_platform(x, y, z):
                    return True
            if self.buttons:
                if (x, y, z) in self.buttons:
                    return True
            return protocol.is_indestructable(self, x, y, z)
    
    return PlatformProtocol, PlatformConnection