"""
Killing KILL_REQUIREMENT other players in under TIME_REQUIREMENT seconds
sends you into a rampage lasting RAMPAGE_DURATION seconds.
The rampage refills and drastically increases your weapons' rate of fire.

By default this means 3 kills in under 8 seconds to activate. For reference,
lines disappear from the killfeed 10 seconds after they appear.

Intended for use in frantic last team standing or free for all matches.

Maintainer: hompy
"""

from collections import deque
from twisted.internet.reactor import callLater, seconds
from twisted.internet.task import LoopingCall
from pyspades.server import set_tool, fog_color, weapon_reload
from pyspades.common import make_color
from pyspades.constants import *

KILL_REQUIREMENT = 3
TIME_REQUIREMENT = 8.0
GRENADE_KILLS_COUNT = True
RAMPAGE_REFILLS = True
RAMPAGE_RELOADS = True
RAMPAGE_DURATION = 20.0
RAPID_INTERVALS = {
    RIFLE_WEAPON : 0.16,
    SMG_WEAPON : 0.08,
    SHOTGUN_WEAPON : 0.18
}
RAMPAGE_FOG_COLOR = (255, 0, 0)
RAMPAGE_FOG_FUNC = lambda: RAMPAGE_FOG_COLOR

ANNOUNCE_RAMPAGE = True
S_RAMPAGE_START = '{player} IS ON A RAMPAGE!!'
S_RAMPAGE_KILLED = "{victim}'s rampage was ended by {killer}"

def resend_tool(player):
    set_tool.player_id = player.player_id
    set_tool.value = player.tool
    if player.weapon_object.shoot:
        player.protocol.send_contained(set_tool)
    else:
        player.send_contained(set_tool)

def rapid_cycle(player):
    resend_tool(player)
    if not player.weapon_object.shoot:
        player.rampage_rapid_loop.stop()

def send_fog(player, color):
    fog_color.color = make_color(*color)
    player.send_contained(fog_color)

def fog_switch(player, colorgetter_a, colorgetter_b):
    if player.rampage:
        send_fog(player, colorgetter_a())
        player.rampage_warning_call = callLater(0.5, fog_switch, player,
            colorgetter_b, colorgetter_a)

def apply_script(protocol, connection, config):
    class RampageConnection(connection):
        rampage = False
        rampage_rapid_loop = None
        rampage_call = None
        rampage_warning_call = None
        rampage_kills = None
        rampage_reenable_rapid_hack_detect = None
        
        def start_rampage(self):
            self.rampage = True
            self.rampage_kills.clear()
            self.rampage_reenable_rapid_hack_detect = self.rapid_hack_detect
            self.rapid_hack_detect = False
            self.rampage_call = callLater(RAMPAGE_DURATION, self.end_rampage)
            if RAMPAGE_DURATION > 4.0:
                self.rampage_warning_call = callLater(RAMPAGE_DURATION - 3.0,
                    fog_switch, self, self.protocol.get_fog_color,
                    RAMPAGE_FOG_FUNC)
            if RAMPAGE_REFILLS:
                self.refill()
            if RAMPAGE_RELOADS:
                weapon = self.weapon_object
                was_shooting = weapon.shoot
                weapon.reset()
                weapon_reload.player_id = self.player_id
                weapon_reload.clip_ammo = weapon.current_ammo
                weapon_reload.reserve_ammo = weapon.current_stock
                weapon.set_shoot(was_shooting)
                self.send_contained(weapon_reload)
            send_fog(self, RAMPAGE_FOG_COLOR)
            if ANNOUNCE_RAMPAGE:
                message = S_RAMPAGE_START.format(player = self.name)
                self.protocol.send_chat(message, global_message = None)
        
        def end_rampage(self):
            self.rampage = False
            self.rapid_hack_detect = self.rampage_reenable_rapid_hack_detect
            if self.rampage_call and self.rampage_call.active():
                self.rampage_call.cancel()
            self.rampage_call = None
            if self.rampage_warning_call and self.rampage_warning_call.active():
                self.rampage_warning_call.cancel()
            self.rampage_warning_call = None
            if self.rampage_rapid_loop and self.rampage_rapid_loop.running:
                self.rampage_rapid_loop.stop()
            send_fog(self, self.protocol.fog_color)
        
        def on_connect(self):
            self.rampage_rapid_loop = LoopingCall(rapid_cycle, self)
            self.rampage_kills = deque(maxlen = KILL_REQUIREMENT)
            connection.on_connect(self)
        
        def on_disconnect(self):
            if self.rampage:
                self.end_rampage()
            self.rampage_rapid_loop = None
            connection.on_disconnect(self)
        
        def on_reset(self):
            if self.rampage:
                self.end_rampage()
            connection.on_reset(self)
        
        def on_kill(self, killer, type, grenade):
            was_rampaging = self.rampage
            if self.rampage:
                self.end_rampage()
            if killer is not None and killer is not self:
                if was_rampaging and ANNOUNCE_RAMPAGE:
                    message = S_RAMPAGE_KILLED.format(victim = self.name,
                        killer = killer.name)
                    self.protocol.send_chat(message, global_message = None)
                if (not killer.rampage and killer.hp and
                    killer.team is not self.team and
                    (GRENADE_KILLS_COUNT or type != GRENADE_KILL)):
                    now = seconds()
                    killer.rampage_kills.append(now)
                    if (len(killer.rampage_kills) == KILL_REQUIREMENT and
                        killer.rampage_kills[0] >= now - TIME_REQUIREMENT):
                        killer.start_rampage()
            return connection.on_kill(self, killer, type, grenade)
        
        def on_grenade_thrown(self, grenade):
            if self.rampage:
                resend_tool(self)
            connection.on_grenade_thrown(self, grenade)
        
        def on_shoot_set(self, fire):
            if (self.rampage and fire and
                self.rampage_rapid_loop and not self.rampage_rapid_loop.running):
                interval = RAPID_INTERVALS[self.weapon]
                self.rampage_rapid_loop.start(interval, now = False)
            connection.on_shoot_set(self, fire)
    
    send_fog_rule = lambda player: not player.rampage
    
    class RampageProtocol(protocol):
        def set_fog_color(self, color):
            self.fog_color = color
            fog_color.color = make_color(*color)
            
            self.send_contained(fog_color, save = True, rule = send_fog_rule)
    
    return RampageProtocol, RampageConnection