from twisted.internet.task import LoopingCallimport commands@commands.name('dayspeed')@commands.admindef day_speed(connection, value = None):
    if value is None:
        return 'Day cycle speed is %s.' % connection.protocol.time_multiplier
    value = float(value)    protocol = connection.protocol
    protocol.time_multiplier = value    if value == 0.0:
        if protocol.daycycle_loop.running:            protocol.daycycle_loop.stop()
        protocol.send_chat('Day cycle stopped.', irc = True)
    else:
        if not protocol.daycycle_loop.running:
            protocol.daycycle_loop.start(protocol.day_update_frequency)        protocol.send_chat('Day cycle speed changed to %s.' % value, irc = True)
from math import floor, modf

@commands.name('daytime')
def day_time(connection, value = None):
    if value is not None:
        if not connection.admin:
            return 'No administrator rights!'
        value = float(value)
        if value < 0.0:
            raise ValueError()
        connection.protocol.current_time = value
        connection.protocol.update_day_color()
    f, i = modf(connection.protocol.current_time)
    return 'Time of day: %02d:%02d' % (i, f * 60)

commands.add(day_speed)
commands.add(day_time)def wrap(min, max, value):
    return value - floor((value - min) / (max - min)) * (max - min)

def hsb_to_rgb(hue, sat, bri):
    bri_n = bri * 255.0
    if sat == 0.0:
	# greyscale
	r, g, b = bri_n, bri_n, bri_n
    else:
        hue_n = wrap(0.0, 1.0, hue) * 6 # wrap hue
        hue_i = floor(hue_n) # get integer part
        hue_f = hue_n - hue_i # fractional part
        if hue_i % 2 == 0:
            hue_f = 1.0 - hue_f
        m = bri_n * (1.0 - sat)
        n = bri_n * (1.0 - (sat * hue_f))
        if hue_i == 0 or hue_i == 6:
            r, g, b = bri_n, n, m
        elif hue_i == 1:
            r, g, b = n, bri_n, m
        elif hue_i == 2:
            r, g, b = m, bri_n, n
        elif hue_i == 3:
            r, g, b = m, n, bri_n
        elif hue_i == 4:
            r, g, b = n, m, bri_n
        elif hue_i == 5:
            r, g, b = bri_n, m, n
    return int(r), int(g), int(b)

def interpolate_rgb((r1, g1, b1), (r2, g2, b2), t):
    return (int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t))

def interpolate_hsb((h1, s1, b1), (h2, s2, b2), t):
    return (h1 + (h2 - h1) * t, s1 + (s2 - s1) * t, b1 + (b2 - b1) * t)

def rgb_distance((r1, g1, b1), (r2, g2, b2)):
    return int(abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2))
def apply_script(protocol, connection, config):    class DayCycleProtocol(protocol):        current_color = None
        current_time = None
        daycycle_loop = None
        day_duration = None        day_update_frequency = None
        time_multiplier = None
                def __init__(self, *arg, **kw):            protocol.__init__(self, *arg, **kw)
            self.daycycle_loop = LoopingCall(self.update_day_color)            self.reset_daycycle()
        
        def reset_daycycle(self):
            if not self.daycycle_loop:
                return
            self.current_color = None
            self.current_time = 7.00
            self.day_duration = 24 * 60 * 60.00
            self.day_update_frequency = 0.1
            self.time_multiplier = 48.0
            self.day_colors = [
                ( 0.00, (0.05,   0.05, 0.05), False),
                ( 4.00, (0.05,   0.77, 0.05), False),
                ( 5.00, (0.0694, 0.77, 0.78), True),
                ( 5.30, (0.0361, 0.25, 0.95), False),
                ( 6.00, (0.56,   0.18, 0.94), False),
                ( 9.00, (0.5527, 0.24, 0.94), False),
                (12.00, (0.5527, 0.41, 0.95), False),
                (19.50, (0.56,   0.28, 0.96), False),
                (20.00, (0.15,   0.33, 0.87), False),
                (20.25, (0.11,   0.49, 0.94), False),
                (20.50, (0.1056, 0.69, 1.00), False),
                (22.50, (0.1,    0.69, 0.1 ), True),
                (23.00, (0.05,   0.05, 0.05), False)]
            self.time_step = 24.00 / (self.day_duration /
                self.day_update_frequency)
            self.target_color_index = 0
            self.next_color()
            if not self.daycycle_loop.running:
                self.daycycle_loop.start(self.day_update_frequency)
                def update_day_color(self):
            if self.current_time >= 24.00:
                self.current_time = wrap(0.00, 24.00, self.current_time)
            while (self.current_time < self.start_time or
                self.current_time >= self.target_time):
                self.next_color()
                self.target_time = self.target_time or 24.00
            t = ((self.current_time - self.start_time) /
                (self.target_time - self.start_time))
            if self.hsv_transition:
                new_color = interpolate_hsb(self.start_color, 
                    self.target_color, t)
                new_color = hsb_to_rgb(*new_color)
            else:
                new_color = interpolate_rgb(self.start_color, 
                    self.target_color, t)
            if (self.current_color is None or
                rgb_distance(self.current_color, new_color) > 3):
                self.current_color = new_color                self.set_fog_color(self.current_color)
            self.current_time += self.time_step * self.time_multiplier
        
        def next_color(self):
            self.start_time, self.start_color, _ = (
                self.day_colors[self.target_color_index])
            self.target_color_index = ((self.target_color_index + 1) %
                len(self.day_colors))
            self.target_time, self.target_color, self.hsv_transition = (
                self.day_colors[self.target_color_index])
            if not self.hsv_transition:
                self.start_color = hsb_to_rgb(*self.start_color)
                self.target_color = hsb_to_rgb(*self.target_color)
        
        def on_map_change(self, map):
            self.reset_daycycle()
            protocol.on_map_change(self, map)
        return DayCycleProtocol, connection