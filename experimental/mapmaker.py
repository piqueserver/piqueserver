import array
import random
import Image

class Heightmap:
    def __init__(self):
        self.width = 512
        self.height = 512
        self.data = array.array('f',[0. for n in xrange(0, self.width*self.height)])
    def get(self, x, y):
        return self.data[x+y*self.height]
    def get_repeat(self, x, y):
        """This allows the algorithm to tile at the edges."""
        if x>=self.width:
            x-=self.width
        if y>=self.height:
            y-=self.height
        return self.data[x+y*self.width]
    def set_repeat(self, x, y, val):
        """This allows the algorithm to tile at the edges."""
        if x>=self.width:
            x-=self.width
        if y>=self.height:
            y-=self.height
        self.data[x+y*self.width] = val
    def seed(self):
        for idx in xrange(len(self.data)):
            self.data[idx] = 0.5 + (random.random()*0.2 - 0.1) # TUNABLE
    def midpoint_displace(self, jittervalue):
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
            spanscaling = spanscaling * 0.6 # TUNABLE

hmap = Heightmap()
hmap.seed()
hmap.midpoint_displace(3) # TUNABLE

result = Image.new('RGB',(hmap.width,hmap.height))
converted = []
for px in hmap.data:
    val = int(min(max(px,0.0),1.0)*255)
    converted.append((val,val,val))
result.putdata(converted)
result.save("result.bmp")