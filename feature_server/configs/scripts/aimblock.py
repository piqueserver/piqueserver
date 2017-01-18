# AImBlock - aimbot detection script
#
# The point of this script is to detect aimbots
# WITHOUT resorting to a hit-to-miss ratio.
#
# Current detection methods:
# - if one changes target, determine how accurate the gun is with respect to the head
#   (currently disabled by default, enable below if you want it - the heuristic SUCKS)
# - if one gets a lot of kills quickly it will warn the admins over IRC
#
# There are more possible methods that can be used, but for now, this should work.
# I'm a bit worried about false positives though.
#
# - Ben "GreaseMonkey" Russell

from twisted.internet import reactor
import commands

# disable if you don't want to see all the jerk information
AIMBLOCK_SPAM = False

# disable if you don't want to kick people who jerk conviniently onto their targets
# note, needs more tweaking, also might not catch hooch's aimbot
# ultimately needs lag compensation to be effective, which it doesn't have
AIMBLOCK_KICK_JERK = False

# disable if you don't want to kick people who jerk conviniently backwards onto their targets
# -- NOT IMPLEMENTED!
AIMBLOCK_KICK_SNAP = False

def aimbotcheck(connection, user, minutes):
    connection = commands.get_player(connection.protocol, user)
    if connection not in connection.protocol.players:
        raise KeyError()
    kills = connection.tally_kill_log(reactor.seconds() - int(minutes)*60)
    return ('Player %s did %s kills in the last %s minutes.' %
        (connection.name, kills, minutes))
commands.add(aimbotcheck)

def apply_script(protocol, connection, config):
    def aimblock(f):
        def _f1(self, *args, **kwargs):
            if self.aimbot_detect:
                return f(self, *args, **kwargs)
        return _f1

    class AImBlockConnection(connection):
        aimbot_detect = True
        aimbot_heur_max = 0.92
        aimbot_heur_jerk = 0.33
        aimbot_heur_leeway = 0.9
        aimbot_heur_snap_thres = -0.1
        aimbot_heur_snap_score = 1.2

        aimbot_heuristic = 0.0
        aimbot_target = None
        aimbot_orient_uv = (1.0, 0.0, 0.0)

        aimbot_kill_time = 30.0
        aimbot_kill_count = 10.0
        aimbot_kill_log = None
        aimbot_kill_warn_last = -3000.0
        aimbot_kill_warn_pause = 30.0

        def aimbot_record_kill(self):
            curkill = reactor.seconds()

            if self.aimbot_kill_log == None:
                self.aimbot_kill_log = []

            self.aimbot_kill_log.append(curkill)

            if self.tally_kill_log(self.aimbot_kill_time) >= self.aimbot_kill_count:
                self.aimbot_trywarn()

        def tally_kill_log(self, seconds):
            if self.aimbot_kill_log == None:
                return 0

            i = -1
            while i >= -len(self.aimbot_kill_log):
                t = self.aimbot_kill_log[i]
                if t < seconds:
                    break
                i -= 1

            return -1-i

        def aimbot_trywarn(self):
            curtime = reactor.seconds()
            if curtime < self.aimbot_kill_warn_last+self.aimbot_kill_warn_pause:
                return
            self.aimbot_kill_warn_last = curtime
            aimwarn = "AIMBOT WARNING: Player \"%s\" got %d kills in the last %d seconds!" % (
                self.name, self.tally_kill_log(self.aimbot_kill_time), self.aimbot_kill_time
                    )
            self.protocol.irc_say(aimwarn)

        def on_kill(self, killer, type, grenade):
            if killer != None and killer != self:
                killer.aimbot_record_kill()
            return connection.on_kill(self, killer, type, grenade)

        def loader_received(self, loader):
            ret = connection.loader_received(self, loader)

            if not self.aimbot_detect:
                return ret

            chtarg = False

            if self.hp:
                if self.player_id is not None:
                    chtarg = True
                    self.recalc_orient_uv()

            if chtarg:
                self.get_aimbot_target()

            return ret

        def sub_vec(self, (x1, y1, z1), (x2, y2, z2)):
            return ((x1-x2),(y1-y2),(z1-z2))

        def calc_uv(self, (x, y, z)):
            d = (x*x + y*y + z*z)**0.5
            if d <= 0.001:
                d = 0.001

            x /= d
            y /= d
            z /= d

            return (x,y,z)

        def recalc_orient_uv(self):
            ox, oy, oz = self.world_object.orientation.get()

            self.aimbot_orient_uv = self.calc_uv((ox, oy, oz))

        def dot_product(self, v1, v2):
            x1, y1, z1 = v1
            x2, y2, z2 = v2

            return x1*x2 + y1*y2 + z1*z2

        @aimblock
        def get_aimbot_target(self):
            oldtarget = self.aimbot_target

            # find best target
            ftarg = None
            fdist = 0.0
            locpos = self.world_object.position.get()

            for pid in xrange(32):
                if pid not in self.protocol.players:
                    continue
                p = self.protocol.players[pid]

                if pid == self.player_id:
                    continue
                if p.team == self.team:
                    continue

                xpos = p.world_object.position.get()
                xdist = self.dot_product(
                    self.calc_uv(self.sub_vec(xpos,locpos)),
                    self.aimbot_orient_uv
                        )
                if xdist > fdist:
                    ftarg = p
                    fdist = xdist

            # if we haven't found one, return
            if ftarg == None:
                return

            # do a quick unit vector check
            # TODO: proper triangulation check

            odist = 0.0
            if oldtarget != None:
                opos = oldtarget.world_object.position.get()
                odist = self.dot_product(
                    self.calc_uv(self.sub_vec(opos,locpos)),
                    self.aimbot_orient_uv
                        )

            if (oldtarget != None and oldtarget != ftarg
                        and odist < self.aimbot_heur_leeway):
                self.aimbot_heuristic += (
                    (fdist-self.aimbot_heuristic)
                    * self.aimbot_heur_jerk
                        )
                if AIMBLOCK_SPAM:
                    print "Jerk test: %.5f -> %.5f" % (
                        fdist, self.aimbot_heuristic)

            self.aimbot_target = ftarg

            self.aimblock_try_complain()

        @aimblock
        def aimblock_try_complain(self):
            if self.aimbot_heuristic >= self.aimbot_heur_max:
                if AIMBLOCK_KICK_JERK:
                    self.on_hack_attempt('Aimbot detected')
                else:
                    self.aimbot_trywarn()

    return protocol, AImBlockConnection
