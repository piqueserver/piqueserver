import array
import random
import Image
import math

class Heightmap:
    def __init__(self):
        self.width = 512
        self.height = 512
        self.data = array.array('f',[0. for n in xrange(0, self.width*self.height)])
    def get(self, x, y):
        return self.data[x+y*self.height]
    def get_repeat(self, x, y):
        """This allows the algorithm to tile at the edges."""
        return self.data[(x%self.width)+(y%self.height)*self.width]
    def set_repeat(self, x, y, val):
        """This allows the algorithm to tile at the edges."""
        self.data[(x%self.width)+(y%self.height)*self.width] = val
    def seed(self, jitter, midpoint):
        halfjitter = jitter * 0.5
        for idx in xrange(len(self.data)):
            self.data[idx] = midpoint + (random.random()*jitter - halfjitter) # TUNABLE
    def peaking(self):
        """Adds a "peaking" feel to the map."""
        for idx in xrange(len(self.data)):
            self.data[idx] = self.data[idx] * self.data[idx]
    def dipping(self):
        """Adds a "dipping" feel to the map."""
        for idx in xrange(len(self.data)):
            self.data[idx] = math.sin(self.data[idx]*(math.pi))
    def rolling(self):
        """Adds a "rolling" feel to the map."""
        for idx in xrange(len(self.data)):
            self.data[idx] = math.sin(self.data[idx]*(math.pi/2))
    def smoothing(self):
        """Does some simple averaging to bring down the noise level."""
        for x in xrange(0,self.width):
            for y in xrange(0,self.height):
                top = self.get_repeat(x,y-1)
                left = self.get_repeat(x-1,y)
                right = self.get_repeat(x+1,y)
                bot = self.get_repeat(x,y+1)
                center = self.data[x+y*self.width]
                self.data[x+y*self.width] = (top + left + right + bot + center)/5
    def midpoint_displace(self, jittervalue, spanscalingmultiplier):
        """Midpoint displacement with the diamond-square algorithm."""
        
        span = self.width+1
        spanscaling = 1.

        for iterations in xrange(10):
            jitterrange = jittervalue * spanscaling
            jitteroffset = - jitterrange / 2
            print(jitterrange)
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

hmap = Heightmap()

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

algorithm_2(hmap)
hmap2 = Heightmap()
algorithm_2(hmap2)
hmap3 = Heightmap()
algorithm_1(hmap3)
hmap.blend_heightmaps(hmap2,hmap3)

#TODO use the heightmap class, not these horrible anonymous heightmaps, and eliminate the functions I bootstrapped on

result = Image.new('RGB',(hmap.width,hmap.height))
converted = []
for px in hmap.data:
    val = int(min(max(px,0.0),1.0)*255)
    converted.append((val,val,val))
result.putdata(converted)
result.save("result.bmp")