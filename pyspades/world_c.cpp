/*
    Copyright (c) Mathias Kaerlev 2011-2012.

    This file is part of pyspades.

    pyspades is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pyspades is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

*/

/*
world_c.cpp - this shit is hazardous
*/

// Cython->C++

#define isvoxelsolidwrap __pyx_f_8pyspades_5world_isvoxelsolidwrap
static int isvoxelsolidwrap(void *, float, float, float);

// from vxl.h
#define CHUNK 1023 //zlib buffer size
#define VSID 512    //Maximum .VXL dimensions in both x & y direction
#define VSIDM (VSID-1)
#define VSIDSQ (VSID*VSID)
#define VSIDSQM (VSIDSQ-1)
#define MAXSCANDIST 128
#define MAXSCANSQ (MAXSCANDIST*MAXSCANDIST)
#define VOXSIZ (VSIDSQ*MAXZDIM)
#define SCPITCH 128
#define SQRT 0.70710678f
#define MINERANGE 3
#define MAXZDIM 64 //Maximum .VXL dimensions in z direction (height)
#define MAXZDIMM (MAXZDIM-1)
#define MAXZDIMMM (MAXZDIM-2)
#define PI 3.141592653589793f
#define PORT 32887
#define GRID_SIZE 64

// common.h
#define CUBE_ARRAY_LENGTH 64

#include <math.h>

struct Vector3
{
    float x, y, z;
};

struct LongVector3
{
    long x, y, z;
};

struct Orientation
{
    Vector3 f, s, h;
};

inline void get_orientation(Orientation * o,
                            float orientation_x, 
                            float orientation_y,
                            float orientation_z)
{
    float f;
    o->f.x = orientation_x;
    o->f.y = orientation_y;
    o->f.z = orientation_z;
    f = sqrtf(orientation_x*orientation_x + orientation_y*orientation_y);
    o->s.x = -orientation_y/f;
    o->s.y = orientation_x/f;
    o->s.z = 0.0f;
    o->h.x = -orientation_z*o->s.y;
    o->h.y = orientation_z*o->s.x;
    o->h.z = orientation_x*o->s.y - orientation_y*o->s.x;
}

float distance3d(float x1, float y1, float z1, float x2, float y2, float z2)
{
    return sqrtf(pow(x2-x1, 2) + pow(y2-y1,2) + pow(z2-z1,2));
}

int validate_hit(float shooter_x, float shooter_y, float shooter_z,
                 float orientation_x, float orientation_y, float orientation_z, 
                 float ox, float oy, float oz, 
                 float tolerance)
{
    float cx, cy, cz, r, x, y;
    Orientation o;
    get_orientation(&o, orientation_x, orientation_y, orientation_z);
    ox -= shooter_x;
    oy -= shooter_y;
    oz -= shooter_z;
    cz = ox * o.f.x + oy * o.f.y + oz * o.f.z;
    r = 1.f/cz;
    cx = ox * o.s.x + oy * o.s.y + oz * o.s.z;
    x = cx * r;
    cy = ox * o.h.x + oy * o.h.y + oz * o.h.z;
    y = cy * r;
    r *= tolerance;
    return (x-r < 0 && x+r > 0 && y-r < 0 && y+r > 0);
}

// silly VOXLAP function
inline void ftol(float f, long *a)
{
    *a = (long)f;
}

long can_see(void * map, float x0, float y0, float z0, float x1, float y1,
             float z1)
{
    Vector3 f, g;
    LongVector3 a, c, d, p, i;
    long cnt = 0;

    ftol(x0-.5f,&a.x); ftol(y0-.5f,&a.y); ftol(z0-.5f,&a.z);
    ftol(x1-.5f,&c.x); ftol(y1-.5f,&c.y); ftol(z1-.5f,&c.z);

    if (c.x <  a.x) {
        d.x = -1; f.x = x0-a.x; g.x = (x0-x1)*1024; cnt += a.x-c.x;
    }
    else if (c.x != a.x) {
        d.x =  1; f.x = a.x+1-x0; g.x = (x1-x0)*1024; cnt += c.x-a.x;
    }
    else 
        f.x = g.x = 0;
    if (c.y <  a.y) {
        d.y = -1; f.y = y0-a.y;   g.y = (y0-y1)*1024; cnt += a.y-c.y;
    }
    else if (c.y != a.y) {
        d.y =  1; f.y = a.y+1-y0; g.y = (y1-y0)*1024; cnt += c.y-a.y;
    }
    else
        f.y = g.y = 0;
    if (c.z <  a.z) {
        d.z = -1; f.z = z0-a.z;   g.z = (z0-z1)*1024; cnt += a.z-c.z;
    }
    else if (c.z != a.z) {
        d.z =  1; f.z = a.z+1-z0; g.z = (z1-z0)*1024; cnt += c.z-a.z;
    }
    else
        f.z = g.z = 0;

    ftol(f.x*g.z - f.z*g.x,&p.x); ftol(g.x,&i.x);
    ftol(f.y*g.z - f.z*g.y,&p.y); ftol(g.y,&i.y);
    ftol(f.y*g.x - f.x*g.y,&p.z); ftol(g.z,&i.z);

    if (cnt > 32)
        cnt = 32;
    while (cnt)
    {
        if (((p.x|p.y) >= 0) && (a.z != c.z)) {
            a.z += d.z; p.x -= i.x; p.y -= i.y;
        }
        else if ((p.z >= 0) && (a.x != c.x)) {
            a.x += d.x; p.x += i.z; p.z -= i.y;
        }
        else {
            a.y += d.y; p.y += i.z; p.z += i.x;
        }

        if (isvoxelsolidwrap(map, a.x, a.y,a.z))
            return 0;
        cnt--;
    }
    return 1;
}

long cast_ray(void * map, float x0, float y0, float z0, float x1, float y1,
    float z1, float length, long* x, long* y, long* z)
{
    x1 = x0 + x1 * length;
    y1 = y0 + y1 * length;
    z1 = z0 + z1 * length;
    Vector3 f, g;
    LongVector3 a, c, d, p, i;
    long cnt = 0;

    ftol(x0-.5f,&a.x); ftol(y0-.5f,&a.y); ftol(z0-.5f,&a.z);
    ftol(x1-.5f,&c.x); ftol(y1-.5f,&c.y); ftol(z1-.5f,&c.z);

    if (c.x <  a.x) {
        d.x = -1; f.x = x0-a.x; g.x = (x0-x1)*1024; cnt += a.x-c.x;
    }
    else if (c.x != a.x) {
        d.x =  1; f.x = a.x+1-x0; g.x = (x1-x0)*1024; cnt += c.x-a.x;
    }
    else 
        f.x = g.x = 0;
    if (c.y <  a.y) {
        d.y = -1; f.y = y0-a.y;   g.y = (y0-y1)*1024; cnt += a.y-c.y;
    }
    else if (c.y != a.y) {
        d.y =  1; f.y = a.y+1-y0; g.y = (y1-y0)*1024; cnt += c.y-a.y;
    }
    else
        f.y = g.y = 0;
    if (c.z <  a.z) {
        d.z = -1; f.z = z0-a.z;   g.z = (z0-z1)*1024; cnt += a.z-c.z;
    }
    else if (c.z != a.z) {
        d.z =  1; f.z = a.z+1-z0; g.z = (z1-z0)*1024; cnt += c.z-a.z;
    }
    else
        f.z = g.z = 0;

    ftol(f.x*g.z - f.z*g.x,&p.x); ftol(g.x,&i.x);
    ftol(f.y*g.z - f.z*g.y,&p.y); ftol(g.y,&i.y);
    ftol(f.y*g.x - f.x*g.y,&p.z); ftol(g.z,&i.z);

    if (cnt > length)
        cnt = (long)length;
    while (cnt)
    {
        if (((p.x|p.y) >= 0) && (a.z != c.z)) {
            a.z += d.z; p.x -= i.x; p.y -= i.y;
        }
        else if ((p.z >= 0) && (a.x != c.x)) {
            a.x += d.x; p.x += i.z; p.z -= i.y;
        }
        else {
            a.y += d.y; p.y += i.z; p.z += i.x;
        }

        if (isvoxelsolidwrap(map, a.x, a.y,a.z)) {
            *x = a.x;
            *y = a.y;
            *z = a.z;
            return 1;
        }
        cnt--;
    }
    return 0;
}

size_t cube_line(int x1, int y1, int z1, int x2, int y2, int z2,
                 LongVector3 * cube_array)
{
	LongVector3 c, d;
	long ixi, iyi, izi, dx, dy, dz, dxi, dyi, dzi;
	size_t count = 0;

	//Note: positions MUST be rounded towards -inf
	c.x = x1;
	c.y = y1;
	c.z = z1;

	d.x = x2 - x1;
	d.y = y2 - y1;
	d.z = z2 - z1;

	if (d.x < 0) ixi = -1;
	else ixi = 1;
	if (d.y < 0) iyi = -1;
	else iyi = 1;
	if (d.z < 0) izi = -1;
	else izi = 1;

	if ((fabsf(d.x) >= fabsf(d.y)) && (fabsf(d.x) >= fabsf(d.z)))
	{
		dxi = 1024; dx = 512;
		dyi = (long)(!d.y ? 0x3fffffff/VSID : fabsf(d.x*1024/d.y));
		dy = dyi/2;
		dzi = (long)(!d.z ? 0x3fffffff/VSID : fabsf(d.x*1024/d.z));
		dz = dzi/2;
	}
	else if (fabsf(d.y) >= fabsf(d.z))
	{
		dyi = 1024; dy = 512;
		dxi = (long)(!d.x ? 0x3fffffff/VSID : fabsf(d.y*1024/d.x));
		dx = dxi/2;
		dzi = (long)(!d.z ? 0x3fffffff/VSID : fabsf(d.y*1024/d.z));
		dz = dzi/2;
	}
	else
	{
		dzi = 1024; dz = 512;
		dxi = (long)(!d.x ? 0x3fffffff/VSID : fabsf(d.z*1024/d.x));
		dx = dxi/2;
		dyi = (long)(!d.y ? 0x3fffffff/VSID : fabsf(d.z*1024/d.y));
		dy = dyi/2;
	}
	if (ixi >= 0) dx = dxi-dx;
	if (iyi >= 0) dy = dyi-dy;
	if (izi >= 0) dz = dzi-dz;

	while (1)
	{
		cube_array[count] = c;

		if(count++ == CUBE_ARRAY_LENGTH)
			return count;

		if(c.x == x2 &&
			c.y == y2 &&
			c.z == z2)
			return count;

		if ((dz <= dx) && (dz <= dy))
		{
			c.z += izi;
			if (c.z < 0 || c.z >= MAXZDIM)
				return count;
			dz += dzi;
		}
		else
		{
			if (dx < dy)
			{
				c.x += ixi;
				if ((unsigned long)c.x >= VSID)
					return count;
				dx += dxi;
			}
			else
			{
				c.y += iyi;
				if ((unsigned long)c.y >= VSID)
					return count;
				dy += dyi;
			}
		}
	}
}