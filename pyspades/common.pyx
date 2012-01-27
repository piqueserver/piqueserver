# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from math import pi

cdef extern from "math.h":
    double sqrt(double x)
    double sin(double x)
    double cos(double x)
    double acos(double x)

def get_color(color):
    b = color & 0xFF
    g = (color & 0xFF00) >> 8
    r = (color & 0xFF0000) >> 16
    return r, g, b

def make_color(r, g, b):
    return b | (g << 8) | (r << 16)

def binify(data, size = 2):
    binText = bin(str(data))[2:]
    binText = (2 * 8 - len(binText)) * '0' + binText
    return binText

MAX_HEX_SIZE = 110
EPSILON = 0.0000001

def hexify(data, max = MAX_HEX_SIZE):
    hexed = str(data).encode('hex')
    if max is not None and len(hexed) > max:
        hexed = '%s (...)' % hexed[:max]
    return hexed

def stringify(data, max = MAX_HEX_SIZE):
    data = str(data)
    if max is not None and len(data) > max:
        data = '%s (...)' % data[:max]
    return '%r' % data

def coordinates(data):
    if data is None:
        raise ValueError()
    if len(data) != 2:
        raise ValueError()
    x = (ord(data[0].lower()) - ord('a')) * 64
    y = (int(data[1]) - 1) * 64
    if x < 0 or x >= 512 or y < 0 or y >= 512:
        raise ValueError()
    return x, y

def to_coordinates(x, y):
    return '%s%s' % (chr(ord('a') + int(x) / 64).upper(), (int(y) / 64) + 1)

def prettify_timespan(total, get_seconds = False):
    total = int(total)
    days = total / (1440 * 60)
    total -= days * 1440 * 60
    hours = total / (60 * 60)
    total -= hours * 60 * 60
    minutes = total / 60
    seconds = total - minutes * 60 if get_seconds else 0
    if days == hours == minutes == seconds == 0:
        return 'less than a %s' % 'second' if get_seconds else 'minute'
    days_s = '%s day' % days if days > 0 else None
    hours_s = '%s hour' % hours if hours > 0 else None
    minutes_s = '%s minute' % minutes if minutes > 0 else None
    seconds_s = '%s second' % seconds if seconds > 0 else None
    if days > 1: days_s += 's'
    if hours > 1: hours_s += 's'
    if minutes > 1: minutes_s += 's'
    if seconds > 1: seconds_s += 's'
    text = ', '.join([s for s in (days_s, hours_s, minutes_s, seconds_s) if s])
    return text

def compare_reader(reader, value, name):
    if reader.read(len(value)) != value:
        print '%s is wrong' % name

def open_debugger(name, locals):
    print '%s, opening debugger' % name
    import code
    code.interact(local = locals)

def check_default(value, default):
    if value != default:
        raw_input('check_default() failed')
        raise NotImplementedError('was %s, should be %s' % (value, default))

import zlib
def crc32(data):
    return zlib.crc32(data) & 0xffffffff

# Ace of Spades uses the CP437 character set for chat and Windows-1252 for
# player list

def encode(value):
    if value is not None:
        return value.encode('cp437', 'replace')

def decode(value):
    if value is not None:
        return value.decode('cp437', 'replace')

cdef class Vertex3:
    # NOTE: for the most part this behaves as a 2d vector, with z being tacked on
    # so it's useful for orientation math
    
    def __init__(self, *arg):
        if arg:
            self.set(*arg)
    
    def copy(self):
        return Vertex3(self.x, self.y, self.z)
    
    def get(self):
        return self.x, self.y, self.z
    
    def set(self, double x, double y, double z):
        self.x = x
        self.y = y
        self.z = z
    
    def set_vector(self, Vertex3 vector):
        self.set(vector.x, vector.y, vector.z)
    
    def zero(self):
        self.x = self.y = self.z = 0.0
    
    def __add__(self, Vertex3 A):
        return Vertex3(self.x + A.x, self.y + A.y, self.z + A.z)
    
    def __sub__(self, Vertex3 A):
        return Vertex3(self.x - A.x, self.y - A.y, self.z - A.z)
    
    def __mul__(self, double k):
        return Vertex3(self.x * k, self.y * k, self.z * k)
    
    def __div__(self, double k):
        return Vertex3(self.x / k, self.y / k, self.z / k)
    
    def __iadd__(self, Vertex3 A):
        self.x += A.x
        self.y += A.y
        self.z += A.z
        return self
    
    def __isub__(self, Vertex3 A):
        self.x -= A.x
        self.y -= A.y
        self.z -= A.z
        return self
    
    def __imul__(self, double k):
        self.x *= k
        self.y *= k
        self.z *= k
        return self
    
    def __idiv__(self, double k):
        self.x /= k
        self.y /= k
        self.z /= k
        return self
    
    def translate(self, double x, double y, double z):
        self.x += x
        self.y += y
        self.z += z
        return self
    
    def cross(self, Vertex3 A):
        return Vertex3(
            self.y * A.z - self.z * A.y,
            self.z * A.x - self.x * A.z,
            self.x * A.y - self.y * A.x)
    
    def dot(self, Vertex3 A):
        return self.x * A.x + self.y * A.y
    
    def perp_dot(self, Vertex3 A):
        return self.x * A.y - self.y * A.x
    
    def rotate(self, Vertex3 A):
        self.x, self.y = self.x * A.x - self.y * A.y, self.x * A.y + self.y * A.x
        return self
    
    def unrotate(self, Vertex3 A):
        self.x, self.y = self.x * A.x + self.y * A.y, self.y * A.x - self.x * A.y
        return self
    
    def length(self):
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def length_sqr(self):
        return self.x * self.x + self.y * self.y + self.z * self.z
    
    def is_zero(self):
        return self.length_sqr() < EPSILON
    
    def normal(self):
        k = self.length()
        return k and Vertex3(self.x / k, self.y / k, self.z / k) or Vertex3()
    
    def normalize(self):
        k = self.length()
        self.x, self.y, self.z = (k and (self.x / k, self.y / k, self.z / k) or
            (0.0, 0.0, 0.0))
        return k
    
    cpdef Quaternion get_rotation_to(self, Vertex3 A):
        q = Quaternion()
        v0 = self.normal()
        v1 = A.normal()
        d = v0.dot(v1)
        if d >= 1.0:
            return Quaternion()
        if d < EPSILON - 1.0:
            axis = Vertex3(1.0, 0.0, 0.0).cross(self)
            if axis.is_zero():
                axis = Vertex3(0.0, 1.0, 0.0).cross(self)
            axis.normalise()
            q.set_angle_axis(pi, axis)
        else:
            k = sqrt((1.0 + d) * 2.0)
            inv_k = 1.0 / k
            c = v0.cross(v1)
            q.x = c.x * inv_k
            q.y = c.y * inv_k
            q.z = c.z * inv_k
            q.w = k * 0.5
            q.normalize()
        return q
    
    def __neg__(self):
        return Vertex3(-self.x, -self.y, -self.z)
    
    def __pos__(self):
        return Vertex3(+self.x, +self.y, +self.z)
    
    def __str__(self):
        return "(%s %s %s)" % (self.x, self.y, self.z)

cdef class Quaternion:
    def __init__(self, *arg):
        self.w = 1.0
        if arg:
            self.set(*arg)
    
    def copy(self):
        return Quaternion(self.w, self.x, self.y, self.z)
    
    def get(self):
        return self.w, self.x, self.y, self.z
    
    def set(self, double w, double x, double y, double z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z
    
    cpdef Quaternion set_angle_axis(self, double radians, Vertex3 axis):
        # axis must be normalized
        half_angle = radians * 0.5
        sha = sin(half_angle)
        self.w = cos(half_angle)
        self.x = axis.x * sha
        self.y = axis.y * sha
        self.z = axis.z * sha
        return self
    
    cpdef Quaternion slerp(self, Quaternion q, double t):
        if t <= 0.0: return self.copy()
        if t >= 1.0: return q.copy()
        
        cos_omega = self.x * q.x + self.y * q.y + self.z * q.z + self.w * q.w
        k0, k1 = 1.0 - t, t
        if cos_omega < 0.0:
            q.w, q.x, q.y, q.z = -q.w, -q.x, -q.y, -q.z
            cos_omega = -cos_omega
        if cos_omega <= 0.9999:
            omega = acos(cos_omega)
            sin_omega = sin(omega)
            k0 = sin(k0 * omega) / sin_omega
            k1 = sin(k1 * omega) / sin_omega
        
        return Quaternion(
            k0 * self.w + k1 * q.w,
            k0 * self.x + k1 * q.x,
            k0 * self.y + k1 * q.y,
            k0 * self.z + k1 * q.z)
    
    cpdef Quaternion nlerp(self, Quaternion q, double t):
        return (self.multiply_scalar(1.0 - t) + q.multiply_scalar(t)).normalize()
    
    cpdef Vertex3 transform_vector(self, Vertex3 v):
        tx = self.w * v.x + self.y * v.z - self.z * v.y
        ty = self.w * v.y - self.x * v.z + self.z * v.x
        tz = self.w * v.z + self.x * v.y - self.y * v.x
        tw = -(self.x * v.x + self.y * v.y + self.z * v.z)
        
        return Vertex3(
            -tw * self.x + tx * self.w - ty * self.z + tz * self.y,
            -tw * self.y + ty * self.w - tz * self.x + tx * self.z,
            -tw * self.z + tz * self.w - tx * self.y + ty * self.x)
    
    cpdef Vertex3 inverse_transform_vector(self, Vertex3 v):
        tx = self.w * v.x - self.y * v.z + self.z * v.y;
        ty = self.w * v.y + self.x * v.z - self.z * v.x;
        tz = self.w * v.z - self.x * v.y + self.y * v.x;
        tw = self.x * v.x + self.y * v.y + self.z * v.z;
        
        return Vertex3(
            tw * self.x + tx * self.w + ty * self.z - tz * self.y,
            tw * self.y + ty * self.w + tz * self.x - tx * self.z,
            tw * self.z + tz * self.w + tx * self.y - ty * self.x)
    
    def normalize(self):
        k = self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z
        if abs(k - 1.0) > EPSILON:
            k = 1.0 / sqrt(k)
            self.w *= k
            self.x *= k
            self.y *= k
            self.z *= k
        return self
    
    def multiply_scalar(self, double k):
        return Quaternion(self.w * k, self.x * k, self.y * k, self.z * k)
    
    def get_matrix(self):
        x2, y2, z2 = self.x * self.x, self.y * self.y, self.z * self.z
        xy = self.x * self.y
        xz = self.x * self.z
        yz = self.y * self.z
        wx = self.w * self.x
        wy = self.w * self.y
        wz = self.w * self.z
        
        # column-major
        return (1.0 - 2.0 * (y2 + z2), 2.0 * (xy - wz), 2.0 * (xz + wy), 0.0,
            2.0 * (xy + wz),1.0 - 2.0 * (x2 + z2), 2.0 * (yz - wx), 0.0,
            2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (x2 + y2), 0.0,
            0.0, 0.0, 0.0, 1.0)
    
    def __add__(self, Quaternion A):
        return Quaternion(self.w + A.w, self.x + A.x, self.y + A.y, self.z + A.z)
    
    def __mul__(self, Quaternion A):
        return Quaternion(
            self.w * A.w - self.x * A.x - self.y * A.y - self.z * A.z,
            self.w * A.x + self.x * A.w + self.y * A.z - self.z * A.y,
            self.w * A.y + self.y * A.w + self.z * A.x - self.x * A.z,
            self.w * A.z + self.z * A.w + self.x * A.y - self.y * A.x)
    
    def __neg__(self):
        return Quaternion(self.w, -self.x, -self.y, -self.z)
    
    def __pos__(self):
        return Quaternion(self.w, +self.x, +self.y, +self.z)
    
    def __str__(self):
        return "(%s %s %s %s)" % (self.w, self.x, self.y, self.z)