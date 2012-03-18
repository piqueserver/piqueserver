from twisted.internet import reactor

def on_loop(protocol):
    print("i'm looping!")
def on_point(protocol):
    print("i'm triggered!")
def on_point2(protocol):
    print("i'm triggered too!")

def schedule_test(protocol):
    myschedule = Schedule(protocol, [
                AlarmLater(on_loop, 0, 5, True),
                AlarmGameTime(on_point2, protocol.default_time_limit, -10),
                AlarmLater(on_point, 0, 1, False)])
    protocol.schedule.queue(myschedule)

class ScheduleTimer(object):
    def __init__(self, protocol):
        self.call_later = None
        self.schedules = []
        self.protocol = protocol
        self.reschedule()
    def queue(self, schedule):
        self.schedules.append(schedule)
        self.reschedule()
    def reschedule(self):
        if self.protocol.advance_call is not None and\
           self.protocol.advance_call.active():
            self.game_time = (self.protocol.advance_call.getTime() -
                          reactor.seconds())
        else:
            self.game_time = 99999999999
        if self.call_later is not None and self.call_later.active():
            self.call_later.cancel()
        min_time = None
        min_call = None
        min_schedule = None
        for n in self.schedules:
            cur_data = n.first()
            if min_time == None or cur_data['time'] < min_time:
                min_call = cur_data['call']
                min_time = cur_data['time']
                min_schedule = n
        self.call_later = None
        if min_call is not None:
            self.held_call = min_call
            self.held_schedule = min_schedule
            self.call_later = reactor.callLater(max(min_time,0), self.do_call)
    def do_call(self):
        self.held_call.call(self.protocol)
        self.held_schedule.shift(self.held_call)
        self.reschedule()

class AlarmLater(object):
    def __init__(self, call, minutes, seconds, loop):
        self.relative_time = minutes * 60.0 + seconds
        self.time = reactor.seconds() + self.relative_time
        self.loop = loop
        self.call = call
        self.traversed = False
    def advance(self):
        self.traversed = True
        if self.loop:
            self.time = reactor.seconds() + self.relative_time
        else:
            self.time = reactor.seconds() + 999999999
    def emit_time(self, timer):
        return self.time - reactor.seconds()

class AlarmGameTime(object):
    def __init__(self, call, minutes, seconds):
        self.relative_time = minutes * 60.0 + seconds
        self.call = call
        self.traversed = False
        self.loop = False
    def advance(self):
        self.traversed = True
    def emit_time(self, timer):
        return timer.game_time - self.relative_time

class Schedule(object):
    def __init__(self, protocol, calls):
        self.protocol = protocol
        self.calls = calls
    def first(self):
        min_time = None
        min_call = None
        for n in self.calls:
            if not n.traversed or n.loop:
                cur_time = n.emit_time(self.protocol.schedule)
                if min_time == None or (min_time>=cur_time):
                    min_time = cur_time
                    min_call = n
        return {'time':min_time,'call':min_call}
    def shift(self, call):
        call.advance()
        for n in self.calls:
            if not n.traversed:
                return
        self.protocol.schedule.schedules.remove(self)
            
