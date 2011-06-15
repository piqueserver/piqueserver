import array
import random
import math
import sys

sys.path.append('..')
from pyspades.load import VXLData

"""NOTES:

filling an entire z column(index 0-63) with set_point() caused corruption,
but only after I filled a 2x2 x/y area. Is this expected behavior?

For now my policy is to set 1-63 for sets, 1-61 for typical removes,
and remove 62-63 only when I plan to repaint the ground/water.

It turns out that I require unsafe_set and unsafe_remove; besides being faster,
the regular versions of those functions won't let me change the ground or water.

"""

class Heightmap:
    def __init__(self):
        self.width = 512//4
        self.height = 512//4
        self.hmap = array.array('f',[0. for n in xrange(0, self.width*self.height)])
        self.style = array.array('i',[0 for n in xrange(0, self.width*self.height)])
    def get(self, x, y):
        return self.hmap[x+y*self.height]
    def get_repeat(self, x, y):
        """This allows the algorithm to tile at the edges."""
        return self.hmap[(x%self.width)+(y%self.height)*self.width]
    def set_repeat(self, x, y, val):
        """This allows the algorithm to tile at the edges."""
        self.hmap[(x%self.width)+(y%self.height)*self.width] = val
    def seed(self, jitter, midpoint):
        halfjitter = jitter * 0.5
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = midpoint + (random.random()*jitter - halfjitter) # TUNABLE
    def peaking(self):
        """Adds a "peaking" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = self.hmap[idx] * self.hmap[idx]
    def dipping(self):
        """Adds a "dipping" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = math.sin(self.hmap[idx]*(math.pi))
    def rolling(self):
        """Adds a "rolling" feel to the map."""
        for idx in xrange(len(self.hmap)):
            self.hmap[idx] = math.sin(self.hmap[idx]*(math.pi/2))
    def smoothing(self):
        """Does some simple averaging to bring down the noise level."""
        for x in xrange(0,self.width):
            for y in xrange(0,self.height):
                top = self.get_repeat(x,y-1)
                left = self.get_repeat(x-1,y)
                right = self.get_repeat(x+1,y)
                bot = self.get_repeat(x,y+1)
                center = self.hmap[x+y*self.width]
                self.hmap[x+y*self.width] = (top + left + right + bot + center)/5
    def midpoint_displace(self, jittervalue, spanscalingmultiplier):
        """Midpoint displacement with the diamond-square algorithm."""
        
        span = self.width+1
        spanscaling = 1.

        for iterations in xrange(8):
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
        """Use another heightmap as an alpha-mask to force values to a specific height"""
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
    def rect_gradient(self, x, y, w, h, algorithm):
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
    def offset_z(self,qty):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]+qty
    def rescale_z(self,multiple):
        for idx in xrange(0,len(self.hmap)):
            self.hmap[idx] = self.hmap[idx]*multiple
    def writeVXL(self):
        self.truncate()
        vxl = VXLData()
        
        zcoltable = [(12,15,117,255),(54,74,13,255)] # water and "beach" z-levels
        for n in xrange(0,62):
            gradient_pct = (n+20.)/(62+20.)
            color = (int(118*gradient_pct),int(222*gradient_pct),int(106*gradient_pct),255)
            zcoltable.append(color)
        zcoltable.reverse()
        
        helpers = []
        """Helpers for filling and detailing the 4x4 tiles."""
        for x in xrange(0,4):
            for y in xrange(0,4):
                adder = (x,y)
                offsetx = 0
                offsety = 0
                if x==0:
                    offsetx-=1
                elif x==3:
                    offsetx+=1
                if y==0:
                    offsety-=1
                elif y==3:
                    offsety+=1
                gradient = (offsetx,offsety)
                helpers.append((adder,gradient))

        for x in xrange(0, self.width):
            mx = x * 4
            for y in xrange(0, self.height):
                my = y * 4
                curheight = self.get(x,y)
                for point in helpers:
                    adder = point[0]
                    gradient = point[1]
                    nearbyheight1 = self.get_repeat(x,y+gradient[1])
                    nearbyheight2 = self.get_repeat(x+gradient[0],y)
                    nearbyheight3 = self.get_repeat(x+gradient[0],y+gradient[1])
                    avg = ((nearbyheight1 + nearbyheight2 + nearbyheight3) / 3. + curheight) / 2.
                    modavg = 63 - int(avg*63)
                    col = zcoltable[modavg]
                    for z in xrange(2, 63):
                        if modavg<=z:
                            vxl.set_point_unsafe(mx+adder[0], my+adder[1], z, col)
                    vxl.set_point_unsafe(mx+adder[0], my+adder[1], 63, col)
        return vxl
    def writeBMP(self):
        import Image
        result = Image.new('RGB',(hmap.width,hmap.height))
        converted = []
        for px in hmap.data:
            val = int(px*255)
            converted.append((val,val,val))
        result.putdata(converted)
        result.save("result.bmp")

def algorithm_1(hmap):
    """Large mountain peaks, rough foothills, lakes"""
    hmap.seed(0.2,0.68)
    hmap.peaking()
    hmap.midpoint_displace(1.44,0.75)
    hmap.smoothing()
    hmap.peaking()
    hmap.smoothing()

def algorithm_2(hmap):
    """Gently rolling hills"""
    hmap.seed(0.2,0.2)
    hmap.midpoint_displace(0.7,0.6)
    hmap.rolling()
    hmap.smoothing()

def algorithm_3(hmap):
    """Cliffs and canyons"""
    hmap.seed(0.2,0.9)
    hmap.dipping()
    hmap.midpoint_displace(1.44,0.85)
    hmap.smoothing()
    hmap.smoothing()
    hmap.dipping()
    hmap.smoothing()
    hmap.smoothing()

def generator_random():

    print("""Please wait, running "random" map generator.""")
    hmap = Heightmap()

    algorithm_2(hmap)
    hmap2 = Heightmap()
    algorithm_3(hmap2)
    hmap3 = Heightmap()
    algorithm_1(hmap3)
    hmap.blend_heightmaps(hmap2,hmap3)
    hmap.offset_z(-0.05)

    return hmap.writeVXL()
