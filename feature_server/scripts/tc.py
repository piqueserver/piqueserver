from commands import add
from array import array

from pyspades.server import block_action, set_color
from pyspades.common import make_color
from pyspades.constants import *

from twisted.internet.task import LoopingCall
from twisted.internet import reactor

def score(connection):
    connection.send_chat(connection.protocol.get_tc_score())
    g_add, b_add = connection.protocol.compute_tc_score()
    if connection.team is connection.protocol.green_team:
        return ('You control %s sector(s), Blue controls %s sector(s).' %
          (g_add, b_add))
    else:
        return ('You control %s sector(s), Green controls %s sector(s).' %
          (b_add, g_add))
    

add(score)

def apply_script(protocol, connection, config):
    
    class TCConnection(connection):

        control_squelch = None       
    
        def on_spawn(self, pos):
            for n in self.explain_game_mode():
                self.send_chat(n)
            return connection.on_spawn(self, pos)

        def explain_game_mode(self):
            return ["Sector owners are shown on the map as squares of your team's color.",
                    "Build or break to capture sectors. Each sector is worth 1pt."]

        def on_block_build(self, x, y, z):
            self.do_control(x, y)
            return connection.on_block_build(self, x, y, z)

        def on_block_removed(self, x, y, z):
            # FIXME: we don't have an easy way to get the collapsed blocks, so collapsing doesn't take control :(
            self.do_control(x, y)
            return connection.on_block_removed(self, x, y, z)

        def draw_cap_box(self, grid_x, grid_y, color):
            block_action.value = BUILD_BLOCK

            # assign different fake players to different teams:
            
            if color[1] == 255:
                player_id = 32
                xstart = grid_x * 64 + 57
            else:
                player_id = 33
                xstart = grid_x * 64 + 2
                
            xend = xstart + 6
            ystart = grid_y * 64 + 2
            yend = ystart + 6
            
            set_color.value = make_color(*color)
            set_color.player_id = player_id
            set_color.fog = False
            self.protocol.send_contained(set_color,
                                         save = True)
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            for x in xrange(xstart, xend):
                for y in xrange(ystart, yend):
                    if (x == xstart or x == xend - 1 or
                        y == ystart or y == yend - 1):
                        block_action.x = x
                        block_action.y = y
                        block_action.z = 0
                        block_action.player_id = player_id
                        self.protocol.send_contained(block_action,
                                                     save = True)
                        self.protocol.map.set_point(x, y, 0, color + (255,),
                            user = False)
                        self.protocol.god_blocks.add((x, y, 0))
            self.protocol.send_contained(set_color,
                                         save = True)

        def clear_cap_box(self, grid_x, grid_y):
            block_action.value = DESTROY_BLOCK
            cell = grid_x + grid_y * 8
            xstart = grid_x * 64 + 2
            xend = xstart + 6
            ystart = grid_y * 64 + 2
            yend = ystart + 6
            for x in xrange(xstart, xend):
                for y in xrange(ystart, yend):
                    if (x == xstart or x == xend - 1 or
                        y == ystart or y == yend - 1):
                        # left
                        block_action.x = x
                        block_action.y = y
                        block_action.z = 0
                        block_action.player_id = 32
                        self.protocol.send_contained(block_action,
                                                     save = True)
                        self.protocol.map.remove_point(x, y, 0,
                            user = False)
                        # right
                        block_action.x = x + 55
                        block_action.y = y
                        block_action.z = 0
                        block_action.player_id = 32
                        self.protocol.send_contained(block_action,
                                                     save = True)
                        self.protocol.map.remove_point(x + 55, y, 0,
                            user = False)
            
        def clear_cap_boxes(self):
            for x in xrange(0, 8):
                for y in xrange(0, 8):
                    self.clear_cap_box(x, y)
            
        def do_control(self, x, y):
            if self.protocol.get_owner(x, y) is self.team:
                pass
            else:
                
                grididx, old_green_held, old_blue_held = (
                    self.protocol.set_owner(x, y, self.team)) 
                gridlocale = 'ABCDEFGH'[x//64] + str((y//64)+1)

                nomans = (old_blue_held <
                          self.protocol.min_blocks_to_capture and
                          old_green_held <
                          self.protocol.min_blocks_to_capture)

                if self.team is self.protocol.green_team:
                    my_owned = self.protocol.green_tc_held[grididx]
                    other_owned = self.protocol.blue_tc_held[grididx]
                    can_lose = (old_blue_held>=
                        self.protocol.min_blocks_to_capture)
                    can_cap = old_green_held<=old_blue_held or nomans
                else:
                    my_owned = self.protocol.blue_tc_held[grididx]
                    other_owned = self.protocol.green_tc_held[grididx]
                    can_lose = (old_green_held>=
                        self.protocol.min_blocks_to_capture)
                    can_cap = old_green_held>=old_blue_held or nomans

                if (my_owned>other_owned and
                    my_owned>=self.protocol.min_blocks_to_capture):
                    if can_cap:                    
                        if self.team is self.protocol.green_team:
                            self.protocol.send_chat('GREEN has captured %s' %
                                                    gridlocale)
                            self.clear_cap_box(x//64,y//64)
                            self.draw_cap_box(x//64,y//64,(0,255,0))
                        else:
                            self.protocol.send_chat('BLUE has captured %s' %
                                                    gridlocale)
                            self.clear_cap_box(x//64,y//64)
                            self.draw_cap_box(x//64,y//64,(0,0,255))
                    else:
                        self.squelch_chat('owner', gridlocale, my_owned,
                                          other_owned)
                else:
                    if (can_lose and
                        other_owned<self.protocol.min_blocks_to_capture):
                        self.clear_cap_box(x//64,y//64)
                        self.protocol.send_chat('%s is NO-MANS-LAND!' %
                                                gridlocale)
                    self.squelch_chat('attacker', gridlocale, my_owned,
                                      other_owned)
                   
        def squelch_chat(self, style, gridlocale, my_owned, other_owned):
            """Only send a chat message if some time has passed or the player
                changed to a new grid location since the last block action."""
            if self.control_squelch is None or (
                self.control_squelch['gridlocale'] != gridlocale or
                self.control_squelch['time'] <= reactor.seconds()):
                if style == 'owner':                
                    self.send_chat(
                    'You own %s with %s blocks (Enemy: %s)' %
                   (gridlocale, my_owned, other_owned))
                elif style == 'attacker':
                    if my_owned > self.protocol.min_blocks_to_capture:
                        self.send_chat(
                        'You now control %s blocks of %s (Enemy: %s)' %
                        (my_owned, gridlocale, other_owned))
                    else:
                        self.send_chat(
                        'You now control %s blocks of %s (%s blocks to cap)' %
                    (my_owned, gridlocale, self.protocol.min_blocks_to_capture))
                self.control_squelch = { 'gridlocale' : gridlocale,
                                     'time' : reactor.seconds() + 2}
            
    class TCProtocol(protocol):

        game_mode = 'tc'
        green_tc_score = 0
        blue_tc_score = 0
        green_tc_held = [0 for n in xrange(8*8)]
        blue_tc_held = [0 for n in xrange(8*8)]
        territory_update_time = config.get('territory_update_time', 30)
        score_limit = config.get('score_limit', 100)
        min_blocks_to_capture = config.get('min_blocks_to_capture', 10)
        tc_owner = array('i')
        for y in xrange(512):
            for x in xrange(512):
                tc_owner.append(-1)

        def __init__(self, config, map):
            result = protocol.__init__(self, config, map)
            self.gameplay_loop = LoopingCall(self.update_tc_score)
            self.gameplay_loop.start(self.territory_update_time)
            self.reset_ownership()
            return result

        def compute_tc_score(self):
            g_add = 0
            b_add = 0
            for cell in xrange(len(self.blue_tc_held)):
                if (self.blue_tc_held[cell]>self.green_tc_held[cell] and
                    self.blue_tc_held[cell]>=self.min_blocks_to_capture):
                    b_add += 1
                elif (self.blue_tc_held[cell]<self.green_tc_held[cell] and
                    self.green_tc_held[cell]>=self.min_blocks_to_capture):
                    g_add += 1
            return g_add, b_add
        
        def update_tc_score(self):
            g_add, b_add = self.compute_tc_score()
            if g_add>b_add:
                self.green_tc_score+=g_add-b_add
                self.send_chat('Green gains %s point(s) (%s sector(s) to %s)' %
                               (g_add-b_add, g_add, b_add))
            elif b_add>g_add:
                self.blue_tc_score+=b_add-g_add
                self.send_chat('Blue gains %s point(s) (%s sector(s) to %s)' %
                               (b_add-g_add, b_add, g_add))
            else:
                self.send_chat('Both teams even at %s sectors' %
                               g_add)
            if not self.check_end_game():
                self.send_chat(self.get_tc_score())
    
        def get_tc_score(self):
            g_score = self.green_tc_score
            b_score = self.blue_tc_score
            diff = g_score - b_score
            if g_score>b_score:
                return ("Green leads %s-%s. Playing to %s points." %
                        (g_score, b_score,
                        self.score_limit))
            elif g_score<b_score:
                return ("Blue leads %s-%s. Playing to %s points." %
                        (b_score, g_score,
                        self.score_limit))
            else:
                return ("%s-%s. Playing to %s points." %
                        (g_score,
                         b_score,
                        self.score_limit))
        
        def check_end_game(self):
            if (self.green_tc_score>=self.score_limit and
                self.green_tc_score>self.blue_tc_score):
                self.send_chat("Green Team Wins, %s - %s" %
                               (self.green_tc_score, self.blue_tc_score))
                player = self.get_a_player(self.green_team)
                if player:
                    self.reset_game(player)
                    self.on_game_end(player)
                return True
            elif (self.blue_tc_score>=self.score_limit and
                  self.blue_tc_score>self.green_tc_score):
                self.send_chat("Blue Team Wins, %s - %s" %
                               (self.blue_tc_score, self.green_tc_score))
                player = self.get_a_player(self.blue_team)
                if player:
                    self.reset_game(player)
                    self.on_game_end(player)
                return True
            return False

        def reset_ownership(self):
            self.tc_owner = array('i')
            for y in xrange(512):
                for x in xrange(512):
                    self.tc_owner.append(-1)

        def get_owner(self, x, y):
            owner = self.tc_owner[x + y * 512]
            if owner == -1:
                return None
            elif owner == 0:
                return self.blue_team
            elif owner == 1:
                return self.green_team
   
        def set_owner(self, x, y, team):
            lastowner = self.tc_owner[x + y * 512]

            gridx = x//64
            gridy = y//64
            grididx = gridx + gridy * 8

            old_green_held = self.green_tc_held[grididx]
            old_blue_held = self.blue_tc_held[grididx]
            
            if lastowner == 1:
                self.green_tc_held[grididx]-=1
            elif lastowner == 0:
                self.blue_tc_held[grididx]-=1
            
            if team is self.green_team:
                self.tc_owner[x + y * 512] = 1
                self.green_tc_held[grididx]+=1                
            elif team is self.blue_team:
                self.tc_owner[x + y * 512] = 0
                self.blue_tc_held[grididx]+=1
            else:
                self.tc_owner[x + y * 512] = -1
            return grididx, old_green_held, old_blue_held

        def on_game_end(self, player):
            self.green_tc_score = 0
            self.blue_tc_score = 0
            self.green_tc_held = [0 for n in xrange(8*8)]
            self.blue_tc_held = [0 for n in xrange(8*8)]
            self.reset_ownership()
            player.clear_cap_boxes()
            return protocol.on_game_end(self, player)

        def get_a_player(self, team):
            for n in self.players.values():
                if n.team is team:
                    return n
            return None
    
    return TCProtocol, TCConnection