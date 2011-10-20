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
    
def cap_box_shape(grid_x, grid_y, is_green):
    if is_green:
        xstart = grid_x * 64 + 57
    else:
        xstart = grid_x * 64 + 2
    xend = xstart + 6
    ystart = grid_y * 64 + 2
    yend = ystart + 6

    result = []
    
    for x in xrange(xstart, xend):
        for y in xrange(ystart, yend):
            if (x == xstart or x == xend - 1 or
                y == ystart or y == yend - 1):
                result.append((x,y))
    return result

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

        def clear_cap_box(self, x, y, is_green):
            if is_green:
                id = 33
            else:
                id = 32
            self.protocol.remove_shape(cap_box_shape(x, y, is_green), id)
        
        def draw_cap_box(self, x, y, is_green):
            if is_green:
                id = 33
                color = (0, 255, 0)
            else:
                id = 32
                color = (0, 0, 255)
            self.protocol.draw_shape(cap_box_shape(x, y, is_green), id, color)
            
        def do_control(self, x, y):
            if self.protocol.get_owner(x, y) is self.team:
                pass
            else:
                
                grididx, old_green_held, old_blue_held = (
                    self.protocol.set_owner(x, y, self.team)) 
                gridlocale = 'ABCDEFGH'[x//64] + str((y//64)+1)

                if self.team is self.protocol.green_team:
                    my_owned = self.protocol.green_tc_held[grididx]
                    other_owned = self.protocol.blue_tc_held[grididx]
                    own_turf = x//64 >= 4
                    other_advantage = old_green_held<=old_blue_held
                    was_under_min = (old_green_held <
                                     self.protocol.min_blocks_to_capture)
                    other_was_min = (old_blue_held >=
                                 self.protocol.min_blocks_to_capture)
                else:
                    my_owned = self.protocol.blue_tc_held[grididx]
                    other_owned = self.protocol.green_tc_held[grididx]
                    own_turf = x//64 < 4
                    other_advantage = old_green_held>=old_blue_held
                    was_under_min = (old_blue_held <
                                     self.protocol.min_blocks_to_capture)
                    other_was_min = (old_green_held >=
                                 self.protocol.min_blocks_to_capture)
                    
                have_min = (my_owned >=
                             self.protocol.min_blocks_to_capture)
                other_min = (other_owned >=
                             self.protocol.min_blocks_to_capture)
                have_advantage = my_owned > other_owned
                can_cap = ((own_turf and other_advantage and other_was_min) or
                           (not own_turf and
                            (other_advantage or was_under_min)))

                if ((have_advantage and have_min) or (own_turf and
                                                      not other_min)):
                    if can_cap:
                        if self.team is self.protocol.green_team:
                            self.protocol.send_chat('GREEN has captured %s' %
                                                    gridlocale)
                            self.clear_cap_box(x//64,y//64, False)
                            self.draw_cap_box(x//64,y//64, True)
                        else:
                            self.protocol.send_chat('BLUE has captured %s' %
                                                    gridlocale)
                            self.clear_cap_box(x//64,y//64, True)
                            self.draw_cap_box(x//64,y//64, False)
                    else:
                        self.squelch_chat('owner', gridlocale, my_owned,
                                          other_owned)
                else:
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
                    if (my_owned > self.protocol.min_blocks_to_capture or
                        other_owned > self.protocol.min_blocks_to_capture):
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
        green_tc_score = 0
        blue_tc_score = 0
        green_tc_held = [0 for n in xrange(8*8)]
        blue_tc_held = [0 for n in xrange(8*8)]
        territory_update_time = config.get('territory_update_time', 30)
        score_limit = config.get('score_limit', 100)
        min_blocks_to_capture = config.get('min_blocks_to_capture', 30)
        tc_owner = array('i')
        game_mode = CTF_MODE
        for y in xrange(512):
            for x in xrange(512):
                tc_owner.append(-1)

        def __init__(self, *arg, **kw):
            result = protocol.__init__(self, *arg, **kw)
            self.gameplay_loop = LoopingCall(self.update_tc_score)
            self.gameplay_loop.start(self.territory_update_time)
            self.reset_ownership()
            self.init_cap_boxes()
            return result

        def draw_shape(self, shape, id, color):           
            block_action.value = BUILD_BLOCK
            
            set_color.value = make_color(*color)
            set_color.player_id = id
            self.send_contained(set_color, save = True)
            
            if self.god_blocks is None:
                self.god_blocks = set()          
            
            for pt in shape:
                x, y = pt
                self.god_blocks.add((x, y, 0))
                self.map.set_point(x, y, 0, color + (255,), user = False)
                block_action.x = x
                block_action.y = y
                block_action.z = 0
                block_action.player_id = id
                self.send_contained(block_action,
                                     save = True)

        def remove_shape(self, shape, id):
            block_action.value = DESTROY_BLOCK
            for pt in shape:
                x, y = pt
                if (x, y, 0) in self.god_blocks:
                    self.god_blocks.remove((x, y, 0))
                self.map.remove_point(x, y, 0, user = False)
                block_action.x = x
                block_action.y = y
                block_action.z = 0
                block_action.player_id = id
                self.send_contained(block_action,
                                     save = True)
                
        def init_cap_boxes(self):
            if self.god_blocks is None:
                self.god_blocks = set()          
            
            for x in xrange(4):
                for y in xrange(8):
                    addshape = cap_box_shape(x, y, False)
                    if not self.map.get_solid(*(addshape[0]+(0,))):
                        self.draw_shape(addshape, 32, (0, 0, 255))
                    delshape = cap_box_shape(x, y, True)
                    if self.map.get_solid(*(delshape[0]+(0,))):
                        self.remove_shape(delshape, 33)
                    addshape = cap_box_shape(x + 4, y, True)
                    if not self.map.get_solid(*(addshape[0]+(0,))):
                        self.draw_shape(addshape, 34, (0, 255, 0))
                    delshape = cap_box_shape(x + 4, y, False)
                    if self.map.get_solid(*(delshape[0]+(0,))):
                        self.remove_shape(delshape, 35)
 
        def compute_tc_score(self):
            g_add = 0
            b_add = 0
            x = 0
            for cell in xrange(len(self.blue_tc_held)):
                blue_turf = x < 4
                green_turf = x >= 4
                blue_majority = (self.blue_tc_held[cell] >=
                                 self.green_tc_held[cell])
                green_majority = not blue_majority
                blue_min_threshold = (self.blue_tc_held[cell] >=
                                      self.min_blocks_to_capture)
                green_min_threshold = (self.green_tc_held[cell] >=
                                      self.min_blocks_to_capture)
                if ((blue_turf and blue_majority) or
                    (blue_turf and not green_min_threshold) or
                    (blue_min_threshold and blue_majority)):
                    b_add += 1
                elif ((green_turf and green_majority) or
                    (green_turf and not blue_min_threshold) or
                    (green_min_threshold and green_majority)):
                    g_add += 1
                x = (x + 1) % 8
            return g_add, b_add
        
        def update_tc_score(self):
            g_add, b_add = self.compute_tc_score()
            gpos = 4 + (g_add - b_add)//2
            if gpos < 0:
                gpos = 0
            if gpos > 8:
                gpos = 8
            graphic = ["<","-","-","-","-","-","-","-",">"]
            graphic[gpos] = unichr(06)
            graphic = "".join(graphic)
            if g_add>b_add:
                self.green_tc_score+=g_add-b_add
                self.send_chat('Green advantage (+%s)   B %s %s %s G ' %
                               (g_add-b_add, b_add, graphic, g_add))
            elif b_add>g_add:
                self.blue_tc_score+=b_add-g_add
                self.send_chat('Blue advantage (+%s)   B %s %s %s G' %
                               (b_add-g_add, b_add, graphic, g_add))
            else:
                self.send_chat('No advantage   B %s %s %s G' %
                               (b_add, graphic, g_add))
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
                    self.on_game_end()
                return True
            elif (self.blue_tc_score>=self.score_limit and
                  self.blue_tc_score>self.green_tc_score):
                self.send_chat("Blue Team Wins, %s - %s" %
                               (self.blue_tc_score, self.green_tc_score))
                player = self.get_a_player(self.blue_team)
                if player:
                    self.reset_game(player)
                    self.on_game_end()
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

        def reset_tc(self):
            self.green_tc_score = 0
            self.blue_tc_score = 0
            self.green_tc_held = [0 for n in xrange(8*8)]
            self.blue_tc_held = [0 for n in xrange(8*8)]
            self.reset_ownership()
            self.init_cap_boxes()
        
        def on_game_end(self):
            self.reset_tc()
            return protocol.on_game_end(self)

        def get_a_player(self, team):
            for n in self.players.values():
                if n.team is team:
                    return n
            return None
    
    return TCProtocol, TCConnection