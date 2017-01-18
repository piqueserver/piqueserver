###Badmin is an bot admin.  He'll do a variety of common admin tasks so you don't have to.
###He might not always get it right, but he'll get it done, and isn't that what really matters?
###-Requirements: blockinfo.py (for grief detection), ratio.py (for k/d ratio), aimbot2.py (hit accuracy)

from twisted.internet import reactor
from pyspades.common import prettify_timespan
from pyspades.constants import *
from pyspades.collision import distance_3d_vector
from commands import add, admin, get_player
import re

BADMIN_VERSION = 9
#Settings for auto-aimbot
SCORE_AIMBOT_ENABLED = True
#any votekicks under uncertain will be cancelled
SCORE_AIMBOT_UNCERTAIN = 2
SCORE_AIMBOT_WARN = 5
SCORE_AIMBOT_KICK = 15
SCORE_AIMBOT_BAN = 25

#Settings for auto-griefcheck
SCORE_GRIEF_ENABLED = True
#any votekicks under uncertain will be cancelled
SCORE_GRIEF_UNCERTAIN = 2
SCORE_GRIEF_WARN = 4
SCORE_GRIEF_KICK = 8
SCORE_GRIEF_BAN = 12

#Settings for blank reason votekicks
#turns on setting preventing blank votekicks
BLANK_VOTEKICK_ENABLED = True

#Settings for language filter
LANGUAGE_FILTER_ENABLED = True


slur_pattern = re.compile(".*nigger.*", re.IGNORECASE)
grief_pattern = re.compile(".*(gr.*f.*(ing|er)|grief|destroy).*", re.IGNORECASE)
aimbot_pattern = re.compile(".*(aim|bot|ha(ck|x)|cheat).*", re.IGNORECASE)

def slur_match(player, msg):
	return (not slur_pattern.match(msg) is None)

def grief_match(player, msg):
	return (not grief_pattern.match(msg) is None)

def aimbot_match(player, msg):
	return (not aimbot_pattern.match(msg) is None)

@admin
def badmin(connection, var=None):
    if var == None:
        return ("@Badmin (r%s): Language Filter(LF) [%s], Blank Votekick Blocker(BV) "
        "[%s], Grief Votekick Protection(GV) [%s], Aimbot Votekick Protection(AV) [%s]"
        % (BADMIN_VERSION, LANGUAGE_FILTER_ENABLED, BLANK_VOTEKICK_ENABLED,
        SCORE_GRIEF_ENABLED, SCORE_AIMBOT_ENABLED))
add(badmin)

@admin
def investigate(connection, player):
    player = get_player(connection.protocol, player)
    score = score_grief(connection, player)
    kdr = round(player.ratio_kills/float(max(1,player.ratio_deaths)))
    percent = round(check_percent(player))
    message = "Results for %s: Grief Score - %s / KDR - %s / Hit Acc. - %s" % (player.name, score, kdr, percent)
add(investigate)

def score_grief(connection, player, time=None): #302 = blue (0), #303 = green (1)
    print "start score grief"
    color = connection not in connection.protocol.players and connection.colors
    minutes = float(time or 2)
    if minutes < 0.0:
        raise ValueError()
    time = reactor.seconds() - minutes * 60.0
    blocks_removed = player.blocks_removed or []
    blocks = [b[1] for b in blocks_removed if b[0] >= time]
    player_name = player.name
    team_id = player.team.id #0=blue, 1=green
    print "name/team set"
    gscore = 0 #griefscore
    map_blocks = 0
    team_blocks = 0
    enemy_blocks = 0
    team_harmed = 0
    enemy_harmed = 0
    print "init values set"
    if len(blocks):
        print "len blocks = true, blocks found"
        total_blocks = len(blocks)
        info = blocks
        for info in blocks:
            if info:
                name, team = info
                if name != player_name and team == team_id:
                    team_blocks+= 1
                elif team != team_id:
                    enemy_blocks+=1
            else:
                map_blocks+= 1
        print "second for done"
        infos = set(blocks)
        infos.discard(None)
        for name, team in infos:
            if name != player_name and team == team_id:
                team_harmed += 1
            elif team != team_id:
                enemy_harmed += 1
        print "third for done"
    else:
        print "len blocks = false, no blocks found"
        total_blocks = 0

    #heuristic checks start here
    #if they didn't break any blocks at all, they probably aren't griefing.
    if total_blocks == 0:
        print "no blocks, ending"
        return 0
    #checks on team blocks destroyed
    if team_blocks > 0 and team_blocks <= 5:
        gscore += 1
    elif team_blocks > 5 and team_blocks <= 10:
        gscore += 2
    elif team_blocks > 10 and team_blocks <= 25:
        gscore += 4
    elif team_blocks > 25 and team_blocks <= 50:
        gscore += 6
    elif team_blocks > 50:
        gscore += 10
    print "team blocks set"
    #team / total ratio checks
    if total_blocks != 0:
        ttr = (float(team_blocks) / float(total_blocks)) * 100
    if ttr > 5 and ttr <= 20:
        gscore += 1
    elif ttr > 20 and ttr <= 50:
        gscore += 2
    elif ttr > 50 and ttr <= 80:
        gscore += 3
    elif ttr > 80:
        gscore += 4
    print "ttr set"
    #teammates harmed check
    if team_harmed == 1:
        gscore += 1
    elif team_harmed > 2 and team_harmed <= 4:
        gscore += 3
    elif team_harmed > 4:
        gscore += 6
    print "team harmed set"
    print "mb: %s, tb: %s, eb: %s, Tb: %s, th: %s, ttr: %s, eh: %s, gs: %s" % (map_blocks, team_blocks, enemy_blocks, total_blocks, team_harmed, ttr, enemy_harmed, gscore)
    return gscore

def check_percent(self):
    if self.weapon == RIFLE_WEAPON:
        if self.semi_hits == 0 or self.semi_count == 0:
            return 0;
        else:
            return (float(self.semi_hits)/float(self.semi_count)) * 100
    elif self.weapon == SMG_WEAPON:
        if self.smg_hits == 0 or self.smg_count == 0:
            return 0;
        else:
            return (float(self.smg_hits)/float(self.smg_count)) * 100
    elif self.weapon == SHOTGUN_WEAPON:
        if self.shotgun_hits == 0 or self.shotgun_count == 0:
            return 0;
        else:
            return float(self.shotgun_hits)/float(self.shotgun_count)

def apply_script(protocol, connection, config):
    def send_slur_nick(connection):
        badmin_punish(connection, 'kick', 'Being a racist')

    def badmin_punish(connection, punishment='warn', reason = "Being a meany face"):
        connection.protocol.irc_say("* @Badmin: %s is being punished. Type: %s (Reason: %s)" % (connection.name, punishment, reason))
        if punishment == "ban":
            connection.ban('@Badmin: ' + reason, connection.protocol.votekick_ban_duration)
        elif punishment == "kick":
            connection.kick('@Badmin: ' + reason)
        elif punishment == "warn":
            connection.protocol.send_chat(" @Badmin: Hey %s, %s" % (connection.name, reason))

    class BadminConnection(connection):
        def on_chat(self, value, global_message):
			if slur_match(self, value) and LANGUAGE_FILTER_ENABLED == True:
				reactor.callLater(1.0, send_slur_nick, self)
			return connection.on_chat(self, value, global_message)
    class BadminProtocol(protocol):
        def start_votekick(self, connection, player, reason = None):
            if reason == None and BLANK_VOTEKICK_ENABLED == True:
                connection.protocol.irc_say("* @Badmin: %s is attempting a blank votekick (against %s)" % (connection.name, player.name))
                return "@Badmin: You must input a reason for the votekick (/votekick name reason)"
            #print "before aimbot check"
            #print player.ratio_kills/float(max(1,player.ratio_deaths))
            if aimbot_match(self, reason) and SCORE_AIMBOT_ENABLED == True:
                #print "made aimbot check"
                score = round(player.ratio_kills/float(max(1,player.ratio_deaths)))
                percent = round(check_percent(player))
                #print "score: %s, acc: %s" % (score, percent)
                if score >= SCORE_AIMBOT_BAN:
                    badmin_punish(player, "ban", "Suspected Aimbotting (Kicker: %s, KDR: %s, Hit Acc: %s)" % (connection.name, score, percent))
                    return
                if score >= SCORE_AIMBOT_KICK:
                    badmin_punish(player, "kick", "Suspected Aimbotting (Kicker: %s, KDR: %s, Hit Acc: %s)" % (connection.name, score, percent))
                    return
                if score >= SCORE_AIMBOT_WARN:
                    badmin_punish(player, "warn", "People think you're aimbotting! (KDR: %s, Hit Acc: %s)" % (score, percent))
                    return protocol.start_votekick(self, connection, player, reason)
                if score >= SCORE_AIMBOT_UNCERTAIN:
                    connection.protocol.irc_say("* @Badmin: Aimbot vote: (KDR: %s, Hit Acc: %s)" % (score, percent))
                    return protocol.start_votekick(self, connection, player, reason)
                if score < SCORE_AIMBOT_UNCERTAIN:
                    connection.protocol.irc_say("* @Badmin: I've cancelled an aimbot votekick! Kicker: %s, Kickee: %s, KDR: %s, Hit Acc: %s" % (connection.name, player.name, score, percent))
                    return "@Badmin: This player is not aimbotting."
                    #print "went too far (aimbot)"
            if grief_match(self, reason) and SCORE_GRIEF_ENABLED == True:
                #print "made grief check"
                score = score_grief(connection, player)
                if score >= SCORE_GRIEF_BAN:
                    badmin_punish(player, "ban", "Griefing (Kicker: %s, GS: %s)" % (connection.name, score))
                    return
                if score >= SCORE_GRIEF_KICK:
                    badmin_punish(player, "kick", "Griefing (Kicker: %s, GS: %s)" % (connection.name, score))
                    return
                if score >= SCORE_GRIEF_WARN:
                    badmin_punish(player, "warn", "Stop Griefing! (GS: %s)" % score)
                    return protocol.start_votekick(self, connection, player, reason)
                if score >= SCORE_GRIEF_UNCERTAIN:
                    connection.protocol.irc_say("* @Badmin: Grief Score: %s" % score)
                    return protocol.start_votekick(self, connection, player, reason)
                if score < SCORE_GRIEF_UNCERTAIN:
                    connection.protocol.irc_say("* @Badmin: I've cancelled a griefing votekick! Kicker: %s, Kickee: %s, Score: %s" % (connection.name, player.name, score))
                    return "@Badmin: This player has not been griefing."
            return protocol.start_votekick(self, connection, player, reason)

    return BadminProtocol, BadminConnection
