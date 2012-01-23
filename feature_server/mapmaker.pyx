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

import array
import random
import math
import sys

sys.path.append('..')
from pyspades.load import VXLData

cdef class Heightmap:
    cdef public int width
    cdef public int height
    cdef public object hmap
    def __init__(self, height):
        self.width = 512
        self.height = 512
        self.hmap = array.array('f',[height for n in xrange(0, self.width*self.height)])
    cpdef double get(self, int x, int y):
        return self.hmap[x+y*self.height]
    cpdef double get_repeat(self, int x, int y):
        """This allows the algorithm to tile at the edges."""
        return self.hmap[(x%self.width)+(y%self.height)*self.width]
    cpdef set_repeat(self, int x, int y, double val):
        """This allows the algorithm to tile at the edges."""
        self.hmap[(x%self.width)+(y%self.height)*self.width] = val
    cpdef mult_repeat(self, int x, int y, double mult):
        idx = (x%self.width)+(y%self.height)*self.width
        self.hmap[idx] *= mult
    cpdef seed(self, double jitter, double midpoint):
        cdef double halfjitter = jitter * 0.5
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = midpoint + (random.random()*jitter - halfjitter) # TUNABLE
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
    def midpoint_displace(self, double jittervalue, \
                          double spanscalingmultiplier):
        """Midpoint displacement with the diamond-square algorithm."""
        
        span = self.width+1
        spanscaling = 1.

        for iterations in xrange(9): # hardcoded for 512x512
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
                    self.set_repeat(x+halfspan,y+span,(botleft+botright+center)*0.33)
                    self.set_repeat(x+span,y+halfspan,(topright+botright+center)*0.33)
                    self.set_repeat(x + halfspan, y + halfspan, center)
            span = span >> 1
            spanscaling = spanscaling * spanscalingmultiplier
    def level_against_heightmap(self, other, height):
        """Use another heightmap as an alpha-mask to force values to a
            specific height"""
        for x in xrange(0, self.width):
            for y in xrange(0, self.height):
                orig = self.get_repeat(x,y)
                dist = orig - height
                self.set_repeat(x,y, orig - dist * other.get_repeat(x,y))
    def blend_heightmaps(self, alphamap, heightmap):
        """Blend according to two heightmaps: one as an alpha-mask,
            the other contains desired heights"""
        for x in xrange(0, self.width):
            for y in xrange(0, self.height):
                orig = self.get_repeat(x,y)
                dist = orig - heightmap.get_repeat(x,y)
                self.set_repeat(x,y, orig - dist * alphamap.get_repeat(x,y))
    def rect_gradient(self, int x, int y, int w, int h, algorithm):
        maxx = x+w
        maxy = y+h
        midx = maxx/2.
        midy = maxy/2.
        if algorithm == 'xy':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = ((midx-abs(xx - midx))/midx + (midy-abs(yy - midy))/midy)/2
                    self.set_repeat(xx,yy,qty)
        elif algorithm == 'invxy':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = ((abs(xx - midx))/midx + (abs(yy - midy))/midy)/2
                    self.set_repeat(xx,yy,qty)
        elif algorithm == 'x':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = (midx-abs(xx - midx))/midx
                    self.set_repeat(xx,yy,qty)
        elif algorithm == 'invx':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = (abs(xx - midx))/midx
                    self.set_repeat(xx,yy,qty)
        elif algorithm == 'y':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = (midy-abs(yy - midy))/midx
                    self.set_repeat(xx,yy,qty)
        elif algorithm == 'invy':
            for xx in xrange(x, maxx):
                for yy in xrange(y, maxy):
                    qty = (abs(yy - midy))/midx
                    self.set_repeat(xx,yy,qty)
    def truncate(self):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = min(max(self.hmap[idx],0.0),1.0)
    def offset_z(self, double qty):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]+qty
    def rescale_z(self, double multiple):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]*multiple
    cpdef writeVXL(self, painting_algorithm):
        self.truncate()
        vxl = VXLData()
        
        for x in xrange(0, self.width):
            for y in xrange(0, self.height):
                h = int(self.get(x,y) * 63)
                col = painting_algorithm(x,y,h)
                for z in xrange(2, 63):
                    if h<=z:
                        vxl.set_point_unsafe(x, y, z, col)
                vxl.set_point_unsafe(x, y, 63, col)
        return vxl
    def river(self,startx,starty,length):
        posx = startx
        posy = starty
        recorded = {}
        for n in xrange(length):
            recorded[(posx,posy)] = True
            curheight = self.get_repeat(posx,posy)
            candidates = []
            for mx in xrange(-20,21):
                for my in xrange(-20,21):
                    if not recorded.has_key((posx+mx, posy+my)):
                        candidates.append((mx,my,
                                           self.get_repeat(posx+mx,posy+my)))                    

            # sort by manhattan distance then (slightly) by lowest height
            candidates.sort(key=lambda cd: -cd[2]*0.1 + (
                abs(cd[0]-posx)+abs(cd[1]-posy)))
            
            chosen = list(random.choice(candidates))
            
            # limit step size to 1
            if abs(chosen[0])>1:
                chosen[0] = int(math.copysign(1,chosen[0]))
            if abs(chosen[1])>1:
                chosen[1] = int(math.copysign(1,chosen[1]))
            posx += chosen[0]
            posy += chosen[1]
        for r in recorded:
            posx = r[0]
            posy = r[1]
            self.set_repeat(posx,posy,0)
            self.mult_repeat(posx-1,posy,0.2)
            self.mult_repeat(posx+1,posy,0.2)
            self.mult_repeat(posx,posy+1,0.2)
            self.mult_repeat(posx,posy-1,0.2)
            self.mult_repeat(posx-1,posy-1,0.5)
            self.mult_repeat(posx+1,posy+1,0.5)
            self.mult_repeat(posx-1,posy+1,0.5)
            self.mult_repeat(posx+1,posy-1,0.5)    

class Gradient:
    def __init__(self):
        self.steps = []
        for n in xrange(0,64):
            self.steps.append((0,0,0,0))
    def set_step(self, step, rgb):
        self.steps[step] = (rgb[0],rgb[1],rgb[2],255)
    def rgb(self, start_pos, start_color, end_pos, end_color):
        dist = end_pos - start_pos
        r_dist = end_color[0] - start_color[0]
        g_dist = end_color[1] - start_color[1]
        b_dist = end_color[2] - start_color[2]
        for n in xrange(start_pos, end_pos):
            pct = float(n - start_pos) / dist
            self.set_step(n, (start_color[0] + r_dist*pct,
                              start_color[1] + g_dist*pct,
                              start_color[2] + b_dist*pct))
    def list(self):
        result = list(self.steps)
        result.reverse()
        return result

class Mapmaker:
    """Scripting API."""
    def __init__(self):
        self.Heightmap = Heightmap
        self.Gradient = Gradient
