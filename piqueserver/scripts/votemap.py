"""
Allows players to vote for maps.

Commands
^^^^^^^^

* ``/votemap`` initiates map voting
* ``/vote <map name>`` vote for a map

.. code-block:: guess

    [votemap]
    public_votes = true
    extension_time = "15min"
    player_driven = false
    autoschedule = false
    percentage = 80

.. codeauthor:: James Hofmann a.k.a triplefox (GPL LICENSE)
"""


import random
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.common import prettify_timespan
from piqueserver.map import check_rotation
from piqueserver.scheduler import Scheduler
from piqueserver.commands import command, player_only
from piqueserver.config import config, cast_duration

votemap_config = config.section('votemap')

VOTEMAP_AUTOSCHEDULE_OPTION = votemap_config.option('autoschedule', 180)
VOTEMAP_PUBLIC_VOTES_OPTION = votemap_config.option('public_votes', True)
# godwhoa: This option gets loaded into votemap_time but that doesn't get used anywhere.
VOTEMAP_TIME_OPTION = votemap_config.option('time', default="2min", cast=cast_duration)
VOTEMAP_EXTENSION_TIME_OPTION = votemap_config.option('extension_time', default="15min",
    cast=lambda x: cast_duration(x)/60)
VOTEMAP_PLAYER_DRIVEN_OPTION = votemap_config.option('player_driven', False)
VOTEMAP_PERCENTAGE_OPTION = votemap_config.option('percentage', 80)

def cancel_verify(connection, instigator):
    return (connection.admin or
            connection is instigator or
            connection.rights.cancel)


class VoteMap:
    extension_time = 0.0
    public_votes = True
    instigator = None
    protocol = None

    def __init__(self, connection, protocol, rotation):
        self.instigator = connection
        self.rotation = rotation
        self.protocol = protocol
        self.vote_percentage = self.protocol.votemap_percentage
        self.vote_time = self.protocol.votemap_time
        self.vote_interval = self.protocol.votemap_interval
        self.public_votes = self.protocol.votemap_public_votes
        self.extension_time = self.protocol.votemap_extension_time
        rotation = [n.name.lower() for n in rotation]
        final_rotation = random.sample(rotation, min(len(rotation), 5))
        if self.extension_time > 0:
            final_rotation.append("extend")
        self.picks = final_rotation
        self.votes = {}
        if connection is None:
            name = 'server'
        else:
            name = connection.name

    def votes_left(self):
        thresh = int((len(self.protocol.players)) *
                     self.vote_percentage / 100.0)
        counts = {}
        for v in list(self.votes.values()):
            if v in counts:
                counts[v]['count'] += 1
            else:
                counts[v] = {'name': v, 'count': 1}
        cvlist = list(counts.values())
        if len(cvlist) <= 0:
            return {'name': self.picks[0], 'count': 0}
        mv = cvlist[0]
        for n in list(counts.keys()):
            if counts[n]['count'] > mv['count']:
                mv = n
        mv['count'] = thresh - mv['count']
        return mv

    def verify(self):
        instigator = self.instigator
        if instigator is None:
            return True
        last = instigator.last_votemap
        if (last is not None and
                reactor.seconds() - last < self.vote_interval):
            return "You can't start a vote now."
        return True

    def start(self):
        instigator = self.instigator
        protocol = self.protocol
        if instigator is None:
            protocol.send_chat('Time to vote!', irc=True)
        else:
            protocol.send_chat(
                '* %s initiated a map vote.' % instigator.name, irc=True)
        self.schedule = schedule = Scheduler(protocol)
        schedule.call_later(self.vote_time, self.timeout)
        schedule.loop_call(30.0, self.update)
        self.protocol.votemap = self
        self.update()

    def vote(self, connection, mapname):
        mapname = mapname.lower()
        if mapname not in self.picks:
            connection.send_chat("Map %s is not available." % mapname)
            return
        self.votes[connection] = mapname
        if self.public_votes:
            self.protocol.send_chat('%s voted for %s.' % (connection.name,
                                                          mapname))
        if self.votes_left()['count'] <= 0:
            self.on_majority()

    def cancel(self, connection=None):
        if connection is None:
            message = 'Cancelled'
        elif not cancel_verify(connection, self.instigator):
            return 'You did not start the vote.'
        else:
            message = 'Cancelled by %s' % connection.name
        self.protocol.send_chat(message)
        self.set_cooldown()
        self.finish()

    def update(self):
        self.protocol.send_chat(
            'Choose next map. Say /vote <name> to cast vote.')
        names = ' '.join(self.picks)
        self.protocol.send_chat('Maps: %s' % names)
        self.protocol.send_chat('To extend current map: /vote extend')

    def timeout(self):
        self.show_result()
        self.finish()

    def on_majority(self):
        self.show_result()
        self.finish()

    def show_result(self):
        result = self.votes_left()['name']
        if result == "extend":
            tl = self.protocol.set_time_limit(self.extension_time, True)
            span = prettify_timespan(tl * 60.0)
            self.protocol.send_chat('Mapvote ended. Current map will '
                                    'continue for %s.' % span, irc=True)
            self.protocol.autoschedule_votemap()
        else:
            self.protocol.send_chat('Mapvote ended. Next map will be: %s.' %
                                    result, irc=True)
            self.protocol.planned_map = check_rotation([result])[0]
        self.set_cooldown()

    def set_cooldown(self):
        if self.instigator is not None and not self.instigator.admin:
            self.instigator.last_votemap = reactor.seconds()

    def finish(self):
        self.schedule.reset()
        self.protocol.votemap = None


@command()
@player_only
def votemap(connection, *arg):
    if not connection.protocol.votemap_player_driven and not connection.admin:
        return "Player-initiated mapvotes are disabled on this server."
    return connection.protocol.start_votemap(
        VoteMap(connection, connection.protocol, connection.protocol.maps))


@command('vote')
@player_only
def votemap_vote(connection, value):
    if connection.protocol.votemap is not None:
        return connection.protocol.votemap.vote(connection, value)
    else:
        return 'No map vote in progress.'


def apply_script(protocol, connection, config):
    class VoteProtocol(protocol):
        # voting
        votemap_time = 120
        votemap_interval = 3 * 60
        votemap_percentage = 80.0
        votemap = None
        planned_map = None
        autoschedule_call = None

        # voting

        def __init__(self, interface, config):
            protocol.__init__(self, interface, config)
            self.votemap_autoschedule = VOTEMAP_AUTOSCHEDULE_OPTION.get()
            self.votemap_public_votes = VOTEMAP_PUBLIC_VOTES_OPTION.get()
            self.votemap_time = VOTEMAP_TIME_OPTION.get()
            self.votemap_extension_time = VOTEMAP_EXTENSION_TIME_OPTION.get()
            self.votemap_player_driven = VOTEMAP_PLAYER_DRIVEN_OPTION.get()
            self.votemap_percentage = VOTEMAP_PERCENTAGE_OPTION.get()
            self.autoschedule_votemap()

        def autoschedule_votemap(self):
            if self.votemap_autoschedule > 0 and self.autoschedule_call is None:
                self.autoschedule_call = self.call_end(
                    self.votemap_autoschedule, self.start_votemap)

        def cancel_vote(self, connection=None):
            if self.votemap is not None:
                return self.votemap.cancel(connection)
            else:
                return protocol.cancel_vote(self, connection)

        def start_votemap(self, votemap=None):
            if self.votemap is not None:
                return self.votemap.update()
            if votemap is None:
                votemap = VoteMap(None, self, self.maps)
            verify = votemap.verify()
            if verify is True:
                votemap.start()
            else:
                return verify

        def on_advance(self, *arg, **kw):
            protocol.on_advance(self, *arg, **kw)
            self.end_votes()

        def end_votes(self):
            if self.votemap is not None:
                self.votemap.finish()

    class VoteConnection(connection):
        last_votemap = None

    return VoteProtocol, VoteConnection
