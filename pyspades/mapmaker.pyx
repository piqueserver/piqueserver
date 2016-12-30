# Copyright (c) James Hofmann 2012.

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

from vxl cimport VXLData, MapData

cdef extern from "classicgen_c.cpp":
    void genland(unsigned long seed, MapData * map)

import array
import random
import math
import sys
from collections import deque
cimport cython

def generate_classic(seed):
    cdef VXLData map = VXLData()
    genland(seed, map.map)
    return map

class Biome(object):
    def __init__(self, gradient, height, variation, noise):
        """
        Create a biome with a Gradient object, typical height(0.0-1.0), and
        height variation(0.0-1.0).
        """
        self.gradient = gradient
        self.height = height
        self.variation = variation
        self.noise = noise
        self.id = -1

@cython.final
cdef class BiomeMap:
    """
    A tilemap containing biome data for a HeightMap.
    """
    cdef public int width
    cdef public int height
    cdef public int twidth
    cdef public int theight
    cdef public list biomes
    cdef public list tmap
    cdef public list gradients
    def __init__(self, biomes, width=32, height=32):
        self.biomes = biomes
        self.width = width
        self.height = height
        self.twidth = 512//self.width
        self.theight = 512//self.height
        self.tmap = [biomes[0] for n in xrange(self.width*self.height)]
        self.gradients = []
        for n in xrange(len(biomes)):
            biomes[n].id = n
            self.gradients.append(biomes[n].gradient)
    cpdef inline object get_repeat(self, int x, int y):
        """This allows the algorithm to tile at the edges."""
        return self.tmap[(x%self.width)+(y%self.height)*self.width]
    cpdef inline set_repeat(self, int x, int y, object val):
        """This allows the algorithm to tile at the edges."""
        self.tmap[(x%self.width)+(y%self.height)*self.width] = val
    cpdef noise(self):
        for idx in xrange(len(self.tmap)):
            self.tmap[idx] = random.choice(self.biomes)
    cpdef random_points(self, qty, biome, x=0, y=0, w=None,
                       h=None):
        """Generate some points for point_flood()"""
        result = []
        if w is None:
            w = self.width
        if h is None:
            h = self.height
        for n in xrange(qty):
            result.append((random.randint(x,x+w),
                         random.randint(y,y+h),
                         biome))
        return result
    cpdef point_flood(self, points):
        """Each tuple of (x,y,biome) in the "points" list
        is round-robined through a flooding
        algorithm. The algorithm uses one queue for each flood,
        so that the flooding is as even as possible."""

        openp = deque([deque([p]) for p in points])
        closedp = set([])
        biomeid = 0

        while len(openp)>0:
            plist = openp.popleft()
            p = plist.popleft()
            closedp.add((p[0],p[1]))
            self.set_repeat(p[0],p[1],p[2])
            if p[0]>0 and (p[0]-1,p[1]) not in closedp:
                plist.append((p[0]-1,p[1],p[2]))
            if p[0]<self.width-1 and (p[0]+1,p[1]) not in closedp:
                plist.append((p[0]+1,p[1],p[2]))
            if p[1]>0 and (p[0],p[1]-1) not in closedp:
                plist.append((p[0],p[1]-1,p[2]))
            if p[1]<self.height-1 and (p[0],p[1]+1) not in closedp:
                plist.append((p[0],p[1]+1,p[2]))
            if len(plist)>0:
                openp.append(plist)

    cpdef jitter(self):
        cdef int x
        cdef int y
        for idx in xrange(len(self.tmap)):
            x = idx % self.width
            y = idx // self.height
            self.tmap[idx] = self.get_repeat(x + random.randint(-1,1),
                                             y + random.randint(-1,1))
    cpdef create_heightmap(self):
        """Return a HeightMap with unfinished color data and a list of
        gradients. When finished with post-processing, use
        hmap.rewrite_gradient_fill(gradients). """
        cdef HeightMap hmap = HeightMap(0.)

        # paste a rectangle into each biome's area

        for idx in xrange(len(self.tmap)):
            x = idx % self.width
            y = idx // self.height
            biome = self.tmap[idx]
            hmap.rect_noise(x*self.twidth,y*self.theight,
                            self.twidth,self.theight,
                            biome.noise,
                            biome.height+random.random()*biome.variation)
            hmap.rect_color(x*self.twidth,y*self.theight,
                            self.twidth,self.theight,
                            biome.id)

        return hmap, self.gradients
    cpdef rect_of_point(self, x, y):
        x_pos = x*self.twidth
        y_pos = y*self.theight
        return [x_pos, y_pos, x_pos+self.twidth, y_pos+self.theight]

@cython.final
cdef class HeightMap:
    cdef public int width
    cdef public int height
    cdef public object hmap
    cdef public object cmap
    def __init__(self, height):
        self.width = 512
        self.height = 512
        self.hmap = array.array('f',[height for n in xrange(0,
                                    self.width*self.height)])
        self.cmap = array.array('i',[<int>0xFF00FFFF for n in xrange(0,
                                    self.width*self.height)])
    cpdef inline double get(self, int x, int y):
        return self.hmap[x+y*self.height]
    cpdef inline double get_repeat(self, int x, int y):
        """This allows the algorithm to tile at the edges."""
        return self.hmap[(x%self.width)+(y%self.height)*self.width]
    cpdef inline set(self, int x, int y, double val):
        self.hmap[x+y*self.height] = val
    cpdef inline set_repeat(self, int x, int y, double val):
        """This allows the algorithm to tile at the edges."""
        self.hmap[(x%self.width)+(y%self.height)*self.width] = val
    cpdef inline add_repeat(self, int x, int y, double val):
        self.hmap[(x%self.width)+(y%self.height)*self.width] += val
    cpdef inline int get_col(self, int x, int y):
        return self.cmap[x+y*self.height]
    cpdef inline int get_col_repeat(self, int x, int y):
        return self.cmap[(x%self.width)+(y%self.height)*self.width]
    cpdef inline set_col_repeat(self, int x, int y, int val):
        self.cmap[(x%self.width)+(y%self.height)*self.width] = val
    cpdef inline fill_col(self, int col):
        for n in xrange(len(self.cmap)):
            self.cmap[n] = col
    cpdef mult_repeat(self, int x, int y, double mult):
        cdef int idx = (x%self.width)+(y%self.height)*self.width
        self.hmap[idx] *= mult
    cpdef seed(self, double jitter, double midpoint):
        cdef double halfjitter = jitter * 0.5
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = midpoint + (random.random()*jitter -
                                         halfjitter)
    cpdef peaking(self):
        """Adds a "peaking" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = self.hmap[idx] * self.hmap[idx]
    cpdef dipping(self):
        """Adds a "dipping" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = math.sin(self.hmap[idx]*(math.pi))
    cpdef rolling(self):
        """Adds a "rolling" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = math.sin(self.hmap[idx]*(math.pi/2))
    cpdef smoothing(self):
        """Does some simple averaging to bring down the noise level."""
        for x in xrange(0,self.width):
            for y in xrange(0,self.height):
                top = self.get_repeat(x,y-1)
                left = self.get_repeat(x-1,y)
                right = self.get_repeat(x+1,y)
                bot = self.get_repeat(x,y+1)
                center = self.hmap[x+y*self.width]
                self.hmap[x+y*self.width] = (top + left + right + bot + center)/5
    cpdef midpoint_displace(self, double jittervalue, \
                          double spanscalingmultiplier, \
                            int skip=0):
        """Midpoint displacement with the diamond-square algorithm."""

        cdef int span = self.width+1
        cdef float spanscaling = 1.
        cdef float jitterrange
        cdef float jitteroffset
        cdef int halfspan
        cdef float topleft
        cdef float topright
        cdef float botleft
        cdef float botright
        cdef float center

        for iterations in xrange(9): # hardcoded for 512x512
            if skip>0:
                skip-=1
                span = span >> 1
                spanscaling = spanscaling * spanscalingmultiplier
                continue
            jitterrange = jittervalue * spanscaling
            jitteroffset = - jitterrange / 2
            for x in xrange(0,self.width,span):
                for y in xrange(0,self.height,span):
                    halfspan = span >> 1
                    topleft = self.get_repeat(x,y)
                    topright = self.get_repeat((x+span),y)
                    botleft = self.get_repeat(x,(y+span))
                    botright = self.get_repeat((x+span),(y+span))
                    center = (topleft+topright+botleft+botright) * 0.25\
                             + (random.random() * jitterrange + jitteroffset)

                    self.set_repeat(x+halfspan,y,(topleft+topright+center)*0.33)
                    self.set_repeat(x,y+halfspan,(topleft+botleft+center)*0.33)
                    self.set_repeat(x+halfspan,y+span,
                                    (botleft+botright+center)*0.33)
                    self.set_repeat(x+span,y+halfspan,
                                    (topright+botright+center)*0.33)
                    self.set_repeat(x + halfspan, y + halfspan, center)
            span = span >> 1
            spanscaling = spanscaling * spanscalingmultiplier
    cpdef jitter_heights(self, double amount):
        """Image jittering filter. Amount is max pixels distance to jitter."""
        cdef int nx = 0
        cdef int ny = 0
        cdef int idx = 0

        while idx<len(self.hmap):
            nx = int((idx % self.width) + (random.random()-0.5)*amount)
            ny = int((idx // self.width) + (random.random()-0.5)*amount)
            self.hmap[idx] = self.get_repeat(nx, ny)
            idx+=1
    cpdef jitter_colors(self, double amount):
        """Image jittering filter. Amount is max pixels distance to jitter."""
        cdef int nx = 0
        cdef int ny = 0
        cdef int idx = 0

        while idx<len(self.hmap):
            nx = int((idx % self.width) + (random.random()-0.5)*amount)
            ny = int((idx // self.width) + (random.random()-0.5)*amount)
            self.cmap[idx] = self.get_col_repeat(nx, ny)
            idx+=1

    cpdef level_against_heightmap(self, HeightMap other, double height):
        """Use another HeightMap as an alpha-mask to force values to a
            specific height"""
        for x in xrange(0, self.width):
            for y in xrange(0, self.height):
                orig = self.get_repeat(x,y)
                dist = orig - height
                self.set_repeat(x,y, orig - dist * other.get_repeat(x,y))
    cpdef blend_heightmaps(self, HeightMap alphamap, HeightMap HeightMap):
        """Blend according to two HeightMaps: one as an alpha-mask,
            the other contains desired heights"""
        for x in xrange(0, self.width):
            for y in xrange(0, self.height):
                orig = self.get_repeat(x,y)
                dist = orig - HeightMap.get_repeat(x,y)
                self.set_repeat(x,y, orig - dist * alphamap.get_repeat(x,y))
    cpdef rect_solid(self, int x, int y, int w, int h, double z):
        for xx in xrange(x, x+w):
            for yy in xrange(y, y+h):
                self.set_repeat(xx,yy,z)
    cpdef rect_noise(self, int x, int y, int w, int h,
                     double jitter, double midpoint):
        cdef double halfjitter = jitter * 0.5
        for xx in xrange(x,x+w):
            for yy in xrange(y,y+h):
                self.set(xx,yy, midpoint + (random.random()*jitter -
                                         halfjitter))
    cpdef rect_color(self, int x, int y, int w, int h, int col):
        for xx in xrange(x, x+w):
            for yy in xrange(y, y+h):
                self.set_col_repeat(xx,yy,col)
    cpdef truncate(self):
        """Truncates the HeightMap to a valid (0-1) range.
        Do this before painting or writing to voxels to avoid crashing."""
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = min(max(self.hmap[idx],0.0),1.0)
    cpdef offset_z(self, double qty):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]+qty
    cpdef rescale_z(self, double multiple):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]*multiple
    cpdef paint_gradient_fill(self, gradient):
        """Surface the map with a single gradient."""
        cdef zcoldef = gradient.array()

        cdef int idx = 0

        while idx<len(self.hmap):
            h = int(self.hmap[idx] * 63)
            self.cmap[idx] = paint_gradient(zcoldef,h)
            idx+=1
    cpdef rewrite_gradient_fill(self, list gradients):
        """Given a cmap of int-indexed gradient definitions,
        rewrite them as surface color definitions."""

        cdef zcoldefs = []
        for n in gradients:
            zcoldefs.append(n.array())

        cdef int idx = 0

        while idx<len(self.hmap):
            h = int(self.hmap[idx] * 63)
            self.cmap[idx] = paint_gradient(zcoldefs[self.cmap[idx]],h)
            idx+=1
    cpdef rgb_noise_colors(self, low, high):
        """Add noise to the heightmap colors."""
        cdef int idx = 0

        patterns = array.array('i', [random.randint(low,high) for n in xrange(101)])

        while idx<len(self.hmap):
            mid = self.cmap[idx]

            r = max(0, min(0xFF,get_r(mid)+patterns[idx%len(patterns)]))
            g = max(0, min(0xFF,get_g(mid)+patterns[(idx+1)%len(patterns)]))
            b = max(0, min(0xFF,get_b(mid)+patterns[(idx+2)%len(patterns)]))

            self.cmap[idx] = make_color(r,g,b)

            idx+=1

    cpdef smooth_colors(self):
        """Average the color of each pixel to add smoothness."""
        cdef int x = 0
        cdef int y = 0

        import copy

        swap = copy.deepcopy(self.cmap)

        while y<self.height:
            left = swap[((x-1)%self.width)+(y%self.height)*self.width]
            right = swap[((x+1)%self.width)+(y%self.height)*self.width]
            up = swap[((x)%self.width)+((y-1)%self.height)*self.width]
            down = swap[((x)%self.width)+((y+1)%self.height)*self.width]
            mid = swap[((x)%self.width)+((y)%self.height)*self.width]

            r = (get_r(left) + get_r(right) + get_r(up) + get_r(down) + get_r(mid))/5
            g = (get_g(left) + get_g(right) + get_g(up) + get_g(down) + get_g(mid))/5
            b = (get_b(left) + get_b(right) + get_b(up) + get_b(down) + get_b(mid))/5

            self.set_col_repeat(x,y,make_color(r,g,b))

            x += 1
            if x>=self.width:
                x = 0
                y += 1

    cpdef write_vxl(self):
        cdef VXLData vxl = VXLData()

        cdef int x = 0
        cdef int y = 0
        cdef int h = 0
        cdef int z = 0
        cdef int idx = 0

        while idx<len(self.hmap):
            x = idx % self.width
            y = idx // self.height
            h = int(self.hmap[idx] * 63)
            vxl.set_column_fast(x, y, h, 63, int(min(63,h+3)),
                                self.cmap[idx])
            idx+=1
        return vxl
    cpdef line_add(self,int x,int y,
                int x2,int y2,int radius, double depth):
        cdef int posx, posy
        for c in bresenham_line(x,y,x2,y2):
            posx = c[0]
            posy = c[1]
            for x in xrange(-radius,radius+1):
                for y in xrange(-radius,radius+1):
                    self.add_repeat(posx+x,posy+y,depth)
    cpdef line_set(self,int x,int y,
                int x2,int y2,int radius, double height):
        cdef int posx, posy
        for c in bresenham_line(x,y,x2,y2):
            posx = c[0]
            posy = c[1]
            for x in xrange(-radius,radius+1):
                for y in xrange(-radius,radius+1):
                    self.set_repeat(posx+x,posy+y,height)

cdef lim_byte(int val):
    return max(0,min(255,val))

cpdef inline int make_color(int r, int g, int b):
    return b | (g << 8) | (r << 16) | (<int>128 << 24)

cpdef inline int get_r(int color):
    return (color>>16) & 0xFF

cpdef inline int get_g(int color):
    return (color>>8) & 0xFF

cpdef inline int get_b(int color):
    return (color) & 0xFF

cdef inline int paint_gradient(object zcoltable, int z):
    cdef int zz = z*3
    cdef int rnd = random.randint(-4,4)
    return make_color(lim_byte(zcoltable[zz]+rnd),
                      lim_byte(zcoltable[zz+1]+rnd),
                      lim_byte(zcoltable[zz+2]+rnd)
                      )

cdef inline list bresenham_line(int x, int y, int x2, int y2):
    cdef int steep = 0
    cdef list coords = []
    cdef int dx, dy, sx, sy, d
    dx = abs(x2 - x)
    if (x2 - x) > 0: sx = 1
    else: sx = -1
    dy = abs(y2 - y)
    if (y2 - y) > 0: sy = 1
    else: sy = -1
    if dy > dx:
        steep = 1
        x,y = y,x
        dx,dy = dy,dx
        sx,sy = sy,sx
    d = (2 * dy) - dx
    for i in xrange(0,dx):
        if steep: coords.append((y,x))
        else: coords.append((x,y))
        while d >= 0:
            y = y + sy
            d = d - (2 * dx)
        x = x + sx
        d = d + (2 * dy)
    coords.append((x2,y2))
    return coords

from color import *

class Gradient(object):
    def __init__(self):
        self.steps = []
        for n in xrange(0,64):
            self.steps.append((0,0,0,0))
    def set_step_rgb(self, step, rgb):
        self.steps[step] = (rgb[0],rgb[1],rgb[2],255)
    def set_step_hsb(self, step, hsb):
        rgb = hsb_to_rgb(*hsb)
        self.steps[step] = (rgb[0],rgb[1],rgb[2],255)
    def rgb(self, start_pos, start_color, end_pos, end_color):
        """Linear interpolation of (0-255) RGB values."""
        dist = end_pos - start_pos
        for n in xrange(start_pos, end_pos):
            pct = float(n - start_pos) / dist
            self.set_step_rgb(n, interpolate_rgb(start_color,
                                             end_color,
                                             pct))
    def hsb(self, start_pos, start_color, end_pos, end_color):
        """Linear interpolation of (0-360,0-100,0-100) HSB values
            as used in GIMP."""
        dist = end_pos - start_pos
        start_color = (start_color[0]/360.,
                       start_color[1]/100.,
                       start_color[2]/100.)
        end_color = (end_color[0]/360.,
                       end_color[1]/100.,
                       end_color[2]/100.)
        for n in xrange(start_pos, end_pos):
            pct = float(n - start_pos) / dist
            interp = interpolate_hsb(start_color, end_color, pct)
            self.set_step_hsb(n, interp)
    def array(self):
        base = list(self.steps)
        base.reverse()
        result = []
        for rgb in base:
            result.append(int(rgb[0]))
            result.append(int(rgb[1]))
            result.append(int(rgb[2]))
        return array.array('i',result)
