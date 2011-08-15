from commands import add
from twisted.internet.task import LoopingCall
from array import array

def score(connection):
    return connection.protocol.get_tc_score()

add(score)

def apply_script(protocol, connection, config):
    
    class TCConnection(connection):
    
        def on_spawn(self, pos):
            self.send_chat(self.explain_game_mode())
            return connection.on_spawn(self, pos)

        def explain_game_mode(self):
            return ("Territory Control: Creating or destroying blocks CONTROLS the position and earns points.")

        def on_block_build(self, x, y, z):
            self.do_control(x, y)
            return connection.on_block_build(self, x, y, z)

        def on_block_removed(self, x, y, z):
            self.do_control(x, y)
            return connection.on_block_removed(self, x, y, z)
            
        def do_control(self, x, y):
            if self.protocol.get_owner(x, y) is self.team:
                pass
            else:
                self.protocol.set_owner(x, y, self.team)
                gridlocale = 'ABCDEFGH'[x//64] + str((y//64)+1)
                self.send_chat('You now control %s, %s in %s (+1)' %
                               (x, y, gridlocale))    
            
    class TCProtocol(protocol):

        game_mode = 'tc'
        green_tc_score = 0
        blue_tc_score = 0
        current_line = 0
        territory_update_time = config.get('territory_update_time', 10) / 512.
        score_limit = config.get('score_limit', 1000000)
        tc_owner = array('i')
        for n in xrange(512*512):
            tc_owner.append(-1)

        def __init__(self, config, map):
            result = protocol.__init__(self, config, map)
            self.gameplay_loop = LoopingCall(self.update_tc_score)
            self.gameplay_loop.start(self.territory_update_time)
            self.reset_ownership()
            return result

        def update_tc_score(self):
            idx = self.current_line * 512
            for x in xrange(idx, idx+512):
                if self.tc_owner[x] == 0:
                    self.blue_tc_score += 1
                elif self.tc_owner[x] == 1:
                    self.green_tc_score += 1
            self.current_line = (self.current_line + 1) % 512
            if self.current_line == 0:
                if not self.check_end_game():
                    self.send_chat(self.get_tc_score())
    
        def get_tc_score(self):
            g_score = self.green_tc_score
            b_score = self.blue_tc_score
            diff = g_score - b_score
            if g_score>b_score:
                return ("Green leads %s-%s (+%s, %s left). Playing to %s points." %
                        (g_score, b_score,
                        diff,
                        self.score_limit - g_score,
                        self.score_limit))
            elif g_score<b_score:
                return ("Blue leads %s-%s (+%s, %s left). Playing to %s points." %
                        (b_score, g_score,
                        -diff,
                        self.score_limit - b_score,
                        self.score_limit))
            else:
                return ("%s-%s, %s left. Playing to %s points." %
                        (g_score,
                         b_score,
                        self.score_limit - g_score,
                        self.score_limit))
        
        def check_end_game(self):
            if self.green_tc_score>=self.score_limit:
                self.send_chat("Green Team Wins, %s - %s" %
                               (self.green_tc_score, self.blue_tc_score))
                player = self.get_a_player(self.green_team)
                if player:
                    self.reset_game(player)
                    self.on_game_end(player)
                return True
            elif self.blue_tc_score>=self.score_limit:
                self.send_chat("Blue Team Wins, %s - %s" %
                               (self.blue_tc_score, self.green_tc_score))
                player = self.get_a_player(self.blue_team)
                if player:
                    self.reset_game(player)
                    self.on_game_end(player)
                return True
            return False

        def reset_ownership(self):
            self.current_line = 0
            self.tc_owner = array('i')
            for n in xrange(512*512):
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
            if team is self.green_team:
                self.tc_owner[x + y * 512] = 1
            elif team is self.blue_team:
                self.tc_owner[x + y * 512] = 0
            else:
                self.tc_owner[x + y * 512] = -1

        def on_game_end(self, player):
            self.green_tc_score = 0
            self.blue_tc_score = 0
            self.reset_ownership()
            return protocol.on_game_end(self, player)

        def get_a_player(self, team):
            if len(team.players)>0:
                return list(team.players.values())[0]
            else:
                return None
    
    return TCProtocol, TCConnection