/*
Genland - procedural landscape generator
by Tom Dobrowolski (http://ged.ax.pl/~tomkh) (heightmap generator)
and Ken Silverman (http://advsys.net/ken) (DTA/PNG/VXL writers)

If you do something cool, feel free to write us
(contact info can be found at our websites)

License for this code:
   * No commercial exploitation please
   * Do not remove our names from the code or credits
   * You may distribute modified code/executables,
     but please make it clear that it is modified.

History:
   2005-12-24: Released GENLAND.EXE with Ken's GROUDRAW demos.
   2006-03-10: Released GENLAND.CPP source code
*/

/*
adapted from the AoS codebase for pyspades, originally by Tom Dobrowolski and
Ken Silverman

http://moonedit.com/tom/vox1_en.htm#genland
*/

#include "vxl_c.h"
#include "constants_c.h"

#define OCTMAX 10 //how many sub functions(10)
#define EPS 0.1f //color smoothing (0.1)

#define max(a,b)  (((a) > (b)) ? (a) : (b))
#define min(a,b)  (((a) < (b)) ? (a) : (b))

// Noise algo based on "Improved Perlin Noise" by Ken Perlin
static inline float fgrad (long h, float x, float y, float z)
{
   switch (h) //h masked before call (h&15)
   {
      case  0: return( x+y  );
      case  1: return(-x+y  );
      case  2: return( x-y  );
      case  3: return(-x-y  );
      case  4: return( x  +z);
      case  5: return(-x  +z);
      case  6: return( x  -z);
      case  7: return(-x  -z);
      case  8: return(   y+z);
      case  9: return(  -y+z);
      case 10: return(   y-z);
      case 11: return(  -y-z);
      case 12: return( x+y  );
      case 13: return(-x+y  );
      case 14: return(   y-z);
      case 15: return(  -y-z);
   }
   return(0);
}

static char noisep[512], noisep15[512];
static void noiseinit ()
{
   long i, j, k;

   for(i=256-1;i>=0;i--) noisep[i] = i;
   for(i=256-1;i> 0;i--) { j = ((rand()*(i+1))>>15); k = noisep[i]; noisep[i] = noisep[j]; noisep[j] = k; }
   for(i=256-1;i>=0;i--) noisep[i+256] = noisep[i];
   for(i=512-1;i>=0;i--) noisep15[i] = noisep[i]&15;
}

float noise3d (float fx, float fy, float fz, long mask)
{
   long i, l[6], a[4];
   float p[3], f[8];

   //if (mask > 255) mask = 255; //Checked before call
   l[0] = (long)floorf(fx); p[0] = fx-((float)l[0]); l[0] &= mask; l[3] = (l[0]+1)&mask;
   l[1] = (long)floorf(fy); p[1] = fy-((float)l[1]); l[1] &= mask; l[4] = (l[1]+1)&mask;
   l[2] = (long)floorf(fz); p[2] = fz-((float)l[2]); l[2] &= mask; l[5] = (l[2]+1)&mask;
   i = noisep[l[0]]; a[0] = noisep[i+l[1]]; a[2] = noisep[i+l[4]];
   i = noisep[l[3]]; a[1] = noisep[i+l[1]]; a[3] = noisep[i+l[4]];
   f[0] = fgrad(noisep15[a[0]+l[2]],p[0]  ,p[1]  ,p[2]);
   f[1] = fgrad(noisep15[a[1]+l[2]],p[0]-1,p[1]  ,p[2]);
   f[2] = fgrad(noisep15[a[2]+l[2]],p[0]  ,p[1]-1,p[2]);
   f[3] = fgrad(noisep15[a[3]+l[2]],p[0]-1,p[1]-1,p[2]); p[2]--;
   f[4] = fgrad(noisep15[a[0]+l[5]],p[0]  ,p[1]  ,p[2]);
   f[5] = fgrad(noisep15[a[1]+l[5]],p[0]-1,p[1]  ,p[2]);
   f[6] = fgrad(noisep15[a[2]+l[5]],p[0]  ,p[1]-1,p[2]);
   f[7] = fgrad(noisep15[a[3]+l[5]],p[0]-1,p[1]-1,p[2]); p[2]++;
   p[2] = (3.f - 2.f*p[2])*p[2]*p[2];
   p[1] = (3.f - 2.f*p[1])*p[1]*p[1];
   p[0] = (3.f - 2.f*p[0])*p[0]*p[0];
   f[0] = (f[4]-f[0])*p[2] + f[0];
   f[1] = (f[5]-f[1])*p[2] + f[1];
   f[2] = (f[6]-f[2])*p[2] + f[2];
   f[3] = (f[7]-f[3])*p[2] + f[3];
   f[0] = (f[2]-f[0])*p[1] + f[0];
   f[1] = (f[3]-f[1])*p[1] + f[1];
   return((f[1]-f[0])*p[0] + f[0]);
}

long buf[VSID*VSID];
long amb[VSID*VSID];

inline int get_height_pos(int x, int y)
{
    return y * VSID + x;
}

inline int get_height(int x, int y, int def)
{
    if (!is_valid_position(x, y, 0))
        return def;
    return ((char *)&buf[get_height_pos(x, y)])[3];
}

inline int get_lowest_height(int x, int y)
{
    int z = get_height(x, y, 63);
    z = max(get_height(x - 1, y, z),
        max(get_height(x + 1, y, z),
        max(get_height(x, y - 1, z),
        max(get_height(x, y + 1, z),
            z))));
    return z;
}

void genland(unsigned long seed, MapData * map)
{
    float dx, dy, d, g, g2, river, amplut[OCTMAX], samp[3], csamp[3];
    float nx, ny, nz, gr, gg, gb;
    long i, x, y, k, o, maxa, msklut[OCTMAX];

    srand(seed);

    noiseinit();

    d = 1;
    //each subdivion adds detail
    for(i=0;i<OCTMAX;i++)
    {
        amplut[i] = d; d *= .4f; //Noise (.4)
        msklut[i] = min((1<<(i+2))-1,255); //fractal stuff
    }
    k = 0;
    for(y=0;y<VSID;y++)
    {
        for(x=0;x<VSID;x++,k++)
        {
            //Get 3 samples (0,0), (EPS,0), (0,EPS):
            for(i=0;i<3;i++)
            {
                dx = (x*0.5f + (float)(i&1)*EPS)*(0.015625f); //1/64
                dy = (y*0.5f + (float)(i>>1)*EPS)*(0.015625f); //1/64
                d = 0; river = 0;
                for(o=0;o<OCTMAX;o++)
                {
                    d += noise3d(dx,dy,9.5f,msklut[o])*amplut[o]*(d*1.6f+1.f); //multi-fractal
                    river += noise3d(dx,dy,13.2f,msklut[o])*amplut[o];
                    dx *= 2; dy *= 2;
                }
                samp[i] = d*-20.f + 28.f; 
                d = sinf(x*(PI/256.f) + river*4.f)*(.52f)+(.48f); // .02 = river width
                if (d > 1) d = 1;
                csamp[i] = samp[i]*d; if (d < 0) d = 0;
                samp[i] *= d;
                if (csamp[i] < samp[i]) csamp[i] = -logf(1.f-csamp[i]); // simulate water normal ;)
            }

            //Get normal using cross-product
            nx = csamp[1]-csamp[0];
            ny = csamp[2]-csamp[0];
            nz = -EPS;
            d = 1.f/sqrtf(nx*nx + ny*ny + nz*nz); nx *= d; ny *= d; nz *= d;

            gr = 140; gg = 125; gb = 115; //Ground

            g = min(max(max(-nz,0)*1.4f - csamp[0]/32.f + noise3d(x*(0.015625f),y*(0.015625f),.3f,15)*.3f,0),1);

            gr += (72-gr)*g; gg += (80-gg)*g; gb += (32-gb)*g; //Grass
            g2 = (1-fabsf(g-.5f)*2)*.7f;
            gr += (68-gr)*g2; gg += (78-gg)*g2; gb += (40-gb)*g2; //Grass2
            g2 = max(min((samp[0]-csamp[0])*1.5f,1),0);
            g = 1-g2*.2f;
            gr += (60*g-gr)*g2; gg += (100*g-gg)*g2; gb += (120*g-gb)*g2; //Water

            ((char *)&amb[k])[2] = (char)min(max(gr*.3f,0),255);
            ((char *)&amb[k])[1] = (char)min(max(gg*.3f,0),255);
            ((char *)&amb[k])[0] = (char)min(max(gb*.3f,0),255);
            maxa = max(max(((char *)&amb[k])[2],((char *)&amb[k])[1]),((char *)&amb[k])[0]);

            //lighting
            d = 1.2f*(nx*.5f + ny*.25f - nz)/sqrtf(1.3125f); //.5*.5 + .25*.25 + 1.0*1.0 = 1.3125
            ((char *)&buf[k])[3] = (char)(63-(samp[0]));
            ((char *)&buf[k])[2] = (char)min(max(gr*d,0),255-maxa);
            ((char *)&buf[k])[1] = (char)min(max(gg*d,0),255-maxa);
            ((char *)&buf[k])[0] = (char)min(max(gb*d,0),255-maxa);
        }
    }

    for(y=0,k=0;y<VSID;y++)
    {
        for(x=0;x<VSID;x++,k++)
        {
            ((char *)&buf[k])[2] += ((char *)&amb[k])[2];
            ((char *)&buf[k])[1] += ((char *)&amb[k])[1];
            ((char *)&buf[k])[0] += ((char *)&amb[k])[0];
        }
    }
    
    int height, z, lowest_z;

    for (y = 0, k = 0; y < VSID; y++) {
    for (x = 0; x < VSID; x++, k++) {
        height = ((char *)&buf[k])[3];
        for (z = 63; z > height; z--) {
            map->geometry[get_pos(x, y, z)] = true;
        }
        map->geometry[get_pos(x, y, z)] = true;
        lowest_z = get_lowest_height(x, y) + 1;
        // printf("%d %d\n", z, lowest_z);
        for (; z < lowest_z; z++) {
            map->colors[get_pos(x, y, z)] = buf[k];
        }
    }}

    return;
}