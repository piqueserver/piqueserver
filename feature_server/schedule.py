from twisted.internet import reactor

class ScheduleTimer(object):
    """
    A "safe" scheduler which allows multiple groups of timed events to
    queue and destroy themselves gracefully.
    """

    def __init__(self, protocol):
        self.call_later = None
        self.schedules = []
        self.protocol = protocol
        self.reschedule()

    def __str__(self):
        return "\n".join([str(n) for n in self.schedules])
        
    def queue(self, schedule):
        self.schedules.append(schedule)
        self.reschedule()
        
    def reschedule(self):
        if (self.protocol.advance_call is not None and
        self.protocol.advance_call.active()):
            self.game_time = (self.protocol.advance_call.getTime() -
                              reactor.seconds())
        else:
            self.game_time = None
        if self.call_later is not None and self.call_later.active():
            self.call_later.cancel()
        min_time = None
        min_call = None
        min_schedule = None
        for n in self.schedules:
            first_time, first_call = n.first()
            if min_time == None or first_time < min_time:
                min_call = first_call
                min_time = first_time
                min_schedule = n
        self.call_later = None
        if min_call is not None:
            self.held_call = min_call
            self.held_schedule = min_schedule
            if min_time<=0:
                self.do_call()
            else:
                self.call_later = reactor.callLater(min_time, self.do_call)
            
    def do_call(self):
        self.held_call.call()
        self.held_schedule.shift(self.held_call)
        self.reschedule()
        
    def _remove(self, schedule):
        if schedule in self.schedules:
            self.schedules.remove(schedule)

class AlarmLater(object):
    """Equivalent to reactor.callLater and LoopingCall."""
    
    def __init__(self, call, minutes=0, seconds=0, loop=False,
                 traversal_required = True):
        self.relative_time = minutes * 60.0 + seconds
        self.time = reactor.seconds() + self.relative_time
        self.loop = loop
        self.call = call
        self.traversed = not traversal_required
        
    def __str__(self):
        return "AlarmLater -> %s; %s %s %s" % (self.call.__name__,
                                         "L" if self.loop else "",
                                         "T" if self.traversed else "",
                                         self.relative_time
                                         )
    
    def advance(self):
        self.traversed = True
        if self.loop:
            self.time = reactor.seconds() + self.relative_time
        else:
            self.time = None
            
    def get_emit_time(self, timer):
        if self.time is None:
            return None
        return self.time - reactor.seconds()

class AlarmBeforeEnd(object):
    """
    Calls at the specified number of minutes and seconds before
    the map cycle ends.
    """
    def __init__(self, call, minutes=0, seconds=0, traversal_required=True):
        self.relative_time = minutes * 60.0 + seconds
        self.call = call
        self.traversed = not traversal_required
        self.loop = False
        
    def __str__(self):
        return "AlarmBeforeEnd -> %s; %s %s %s" % (self.call.__name__,
                                         "L" if self.loop else "",
                                         "T" if self.traversed else "",
                                         self.relative_time
                                         )
    
    def advance(self):
        self.traversed = True
        
    def get_emit_time(self, timer):
        if timer.game_time is None:
            return None
        return timer.game_time - self.relative_time

class Schedule(object):
    """
    Specifies some number of Alarm events, which will be called according
    to these rules:
        Non-looping alarms are called once at the specified time.
        Looping alarms are called endlessly.
        When all alarms have been traversed at least once, the schedule ends.
        (If you want an alarm that is non-required, e.g. recurring status
        updates, create it with traversal_required = False)
    """

    def __init__(self, protocol, calls, on_destroy=None, name="Untitled"):
        self.protocol = protocol
        self.calls = calls
        self.on_destroy = on_destroy
        self.name = name

    def __str__(self):
        return "Schedule %s\n" % (self.name) +\
               "\n".join([str(c) for c in self.calls])

    def first(self):
        min_time = None
        min_call = None
        for n in self.calls:
            if not n.traversed or n.loop:
                cur_time = n.get_emit_time(self.protocol.schedule)
                if cur_time is None:
                    continue
                if min_time == None or (min_time>=cur_time):
                    min_time = cur_time
                    min_call = n
        return min_time, min_call

    def shift(self, call):
        call.advance()
        for n in self.calls:
            if not n.traversed:
                return
        self.protocol.schedule._remove(self)
        
    def destroy(self):            
        self.protocol.schedule._remove(self)
        if self.on_destroy:
            self.on_destroy()
        self.protocol.schedule.reschedule()

class OptimisticSchedule(Schedule):
    """
    A Schedule that ignores events that are in the past.
    """
    
    def __str__(self):
        return "OptimisticSchedule %s\n" % (self.name) +\
               "\n".join([str(c) for c in self.calls])
    
    def first(self):
        min_time = None
        min_call = None
        for n in self.calls:
            if not n.traversed or n.loop:
                cur_time = n.get_emit_time(self.protocol.schedule)
                if cur_time is None:
                    continue
                if cur_time<0:
                    n.traversed = True
                elif min_time == None or (min_time>=cur_time):
                    min_time = cur_time
                    min_call = n
        return min_time, min_call
