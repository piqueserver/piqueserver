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

#include "constants_c.h"
#include "vxl_c.h"

// from vxl.h
#define MAXZDIM 64 //Maximum .VXL dimensions in z direction (height)
#define FALL_SLOW_DOWN 0.24f
#define FALL_DAMAGE_VELOCITY 0.58f
#define FALL_DAMAGE_SCALAR 4096
#define WEAPON_PRIMARY 1

// common.h
#define CUBE_ARRAY_LENGTH 64
#include "common_c.h"
#include <cmath>

#define FOG_DISTANCE 128

enum damage_index
{
    BODY_TORSO,
    BODY_HEAD,
    BODY_ARMS,
    BODY_LEGS,
    BODY_MELEE
};

// globals to make porting easier
float ftotclk;
float fsynctics;
MapData *global_map;

struct Orientation
{
    Vector f, s, h;
};

struct PlayerType
{
    Vector p, e, v, s, h, f;
    int mf, mb, ml, mr, jump, crouch, sneak, sprint, primary_fire,
        secondary_fire;
    float lastclimb;
    int airborne, wade, alive, weapon;
};

struct GrenadeType
{
    Vector p, v;
};

inline void get_orientation(Orientation *o,
                            float orientation_x,
                            float orientation_y,
                            float orientation_z)
{
    float f;
    o->f.x = orientation_x;
    o->f.y = orientation_y;
    o->f.z = orientation_z;
    f = sqrtf(orientation_x * orientation_x + orientation_y * orientation_y);
    o->s.x = -orientation_y / f;
    o->s.y = orientation_x / f;
    o->s.z = 0.0f;
    o->h.x = -orientation_z * o->s.y;
    o->h.y = orientation_z * o->s.x;
    o->h.z = orientation_x * o->s.y - orientation_y * o->s.x;
}

float distance3d(float x1, float y1, float z1, float x2, float y2, float z2)
{
    return sqrtf(pow(x2 - x1, 2) + pow(y2 - y1, 2) + pow(z2 - z1, 2));
}

int validate_hit(float shooter_x, float shooter_y, float shooter_z,
                 float orientation_x, float orientation_y, float orientation_z,
                 float ox, float oy, float oz,
                 float aim_tolerance, float dist_tolerance)
{
    ox -= shooter_x;
    oy -= shooter_y;
    if (sqrtf(ox * ox + oy * oy) > FOG_DISTANCE + dist_tolerance)
        return 0;
    oz -= shooter_z;
    
    Orientation o;
    get_orientation(&o, orientation_x, orientation_y, orientation_z);
    float cz = ox * o.f.x + oy * o.f.y + oz * o.f.z;
    float r = 1.f / cz;
    float cx = ox * o.s.x + oy * o.s.y + oz * o.s.z;
    float x = cx * r;
    float cy = ox * o.h.x + oy * o.h.y + oz * o.h.z;
    float y = cy * r;
    r *= aim_tolerance;
    int ret = (x - r < 0 && x + r > 0 && y - r < 0 && y + r > 0);
#if 0
    if (!ret) {
        printf("hit test failed: %f %f %f\n", x, y, r);
    }
#endif
    return ret;
}

// silly VOXLAP function
inline void ftol(float f, long *a)
{
    *a = (long)floor(f + 0.5f);
}

//same as isvoxelsolid but water is empty && out of bounds returns true
int clipbox(float x, float y, float z)
{
    int sz;

    if (x < 0 || x >= 512 || y < 0 || y >= 512)
        return 1;
    else if (z < 0)
        return 0;
    sz = (int)z;
    if (sz == 63)
        sz = 62;
    else if (sz >= 64)
        return 1;
    return get_solid((int)x, (int)y, sz, global_map);
}

//same as isvoxelsolid() but with wrapping
long isvoxelsolidwrap(long x, long y, long z)
{
    if (z < 0)
        return 0;
    else if (z >= 64)
        return 1;
    return get_solid((int)x & VXL_MAX_SIZEM, (int)y & VSIDM, z, global_map);
}

//same as isvoxelsolid but water is empty
long clipworld(long x, long y, long z)
{
    if (x < 0 || x >= 512 || y < 0 || y >= 512)
        return 0;
    if (z < 0)
        return 0;
    int sz = (int)z;
    if (sz == 63)
        sz = 62;
    else if (sz >= 63)
        return 1;
    else if (sz < 0)
        return 0;
    return get_solid((int)x, (int)y, sz, global_map);
}

long can_see(MapData *map, float x0, float y0, float z0, float x1, float y1,
             float z1)
{
    Vector f, g;
    LongVector a, c, d;
    long cnt = 0;

    ftol(x0 - .5f, &a.x);
    ftol(y0 - .5f, &a.y);
    ftol(z0 - .5f, &a.z);
    ftol(x1 - .5f, &c.x);
    ftol(y1 - .5f, &c.y);
    ftol(z1 - .5f, &c.z);

    if (c.x < a.x)
    {
        d.x = -1;
        f.x = x0 - a.x;
        g.x = (x0 - x1) * 1024;
        cnt += a.x - c.x;
    }
    else if (c.x != a.x)
    {
        d.x = 1;
        f.x = a.x + 1 - x0;
        g.x = (x1 - x0) * 1024;
        cnt += c.x - a.x;
    }
    else
        f.x = g.x = 0;
    if (c.y < a.y)
    {
        d.y = -1;
        f.y = y0 - a.y;
        g.y = (y0 - y1) * 1024;
        cnt += a.y - c.y;
    }
    else if (c.y != a.y)
    {
        d.y = 1;
        f.y = a.y + 1 - y0;
        g.y = (y1 - y0) * 1024;
        cnt += c.y - a.y;
    }
    else
        f.y = g.y = 0;
    if (c.z < a.z)
    {
        d.z = -1;
        f.z = z0 - a.z;
        g.z = (z0 - z1) * 1024;
        cnt += a.z - c.z;
    }
    else if (c.z != a.z)
    {
        d.z = 1;
        f.z = a.z + 1 - z0;
        g.z = (z1 - z0) * 1024;
        cnt += c.z - a.z;
    }
    else
        f.z = g.z = 0;

    LongVector p, i;

    ftol(f.x * g.z - f.z * g.x, &p.x);
    ftol(g.x, &i.x);
    ftol(f.y * g.z - f.z * g.y, &p.y);
    ftol(g.y, &i.y);
    ftol(f.y * g.x - f.x * g.y, &p.z);
    ftol(g.z, &i.z);

    if (cnt > FOG_DISTANCE)
        cnt = FOG_DISTANCE;
    while (cnt)
    {
        if (((p.x | p.y) >= 0) && (a.z != c.z))
        {
            a.z += d.z;
            p.x -= i.x;
            p.y -= i.y;
        }
        else if ((p.z >= 0) && (a.x != c.x))
        {
            a.x += d.x;
            p.x += i.z;
            p.z -= i.y;
        }
        else
        {
            a.y += d.y;
            p.y += i.z;
            p.z += i.x;
        }

        if (isvoxelsolidwrap(a.x, a.y, a.z))
            return 0;
        cnt--;
    }
    return 1;
}

long cast_ray(MapData *map, float x0, float y0, float z0, float x1, float y1,
              float z1, float length, long *x, long *y, long *z)
{
    x1 = x0 + x1 * length;
    y1 = y0 + y1 * length;
    z1 = z0 + z1 * length;
    LongVector a, c, d;
    long cnt = 0;

    ftol(x0 - .5f, &a.x);
    ftol(y0 - .5f, &a.y);
    ftol(z0 - .5f, &a.z);
    ftol(x1 - .5f, &c.x);
    ftol(y1 - .5f, &c.y);
    ftol(z1 - .5f, &c.z);

    Vector f, g;

    if (c.x < a.x)
    {
        d.x = -1;
        f.x = x0 - a.x;
        g.x = (x0 - x1) * 1024;
        cnt += a.x - c.x;
    }
    else if (c.x != a.x)
    {
        d.x = 1;
        f.x = a.x + 1 - x0;
        g.x = (x1 - x0) * 1024;
        cnt += c.x - a.x;
    }
    else
        f.x = g.x = 0;
    if (c.y < a.y)
    {
        d.y = -1;
        f.y = y0 - a.y;
        g.y = (y0 - y1) * 1024;
        cnt += a.y - c.y;
    }
    else if (c.y != a.y)
    {
        d.y = 1;
        f.y = a.y + 1 - y0;
        g.y = (y1 - y0) * 1024;
        cnt += c.y - a.y;
    }
    else
        f.y = g.y = 0;
    if (c.z < a.z)
    {
        d.z = -1;
        f.z = z0 - a.z;
        g.z = (z0 - z1) * 1024;
        cnt += a.z - c.z;
    }
    else if (c.z != a.z)
    {
        d.z = 1;
        f.z = a.z + 1 - z0;
        g.z = (z1 - z0) * 1024;
        cnt += c.z - a.z;
    }
    else
        f.z = g.z = 0;

    LongVector p, i;

    ftol(f.x * g.z - f.z * g.x, &p.x);
    ftol(g.x, &i.x);
    ftol(f.y * g.z - f.z * g.y, &p.y);
    ftol(g.y, &i.y);
    ftol(f.y * g.x - f.x * g.y, &p.z);
    ftol(g.z, &i.z);

    if (cnt > length)
        cnt = (long)length;
    while (cnt)
    {
        if (((p.x | p.y) >= 0) && (a.z != c.z))
        {
            a.z += d.z;
            p.x -= i.x;
            p.y -= i.y;
        }
        else if ((p.z >= 0) && (a.x != c.x))
        {
            a.x += d.x;
            p.x += i.z;
            p.z -= i.y;
        }
        else
        {
            a.y += d.y;
            p.y += i.z;
            p.z += i.x;
        }

        if (isvoxelsolidwrap(a.x, a.y, a.z))
        {
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
                 LongVector *cube_array)
{
    // Note: positions MUST be rounded towards -inf
    // Cursor starts at the starting location
    LongVector cursor;
    cursor.x = x1;
    cursor.y = y1;
    cursor.z = z1;

    // distance to move in each axis
    LongVector dist;
    dist.x = x2 - x1;
    dist.y = y2 - y1;
    dist.z = z2 - z1;

    // direction to move in each axis
    LongVector dir;
    dir.x = dist.x < 0 ? -1 : 1;
    dir.y = dist.y < 0 ? -1 : 1;
    dir.z = dist.z < 0 ? -1 : 1;

    long dx, dy, dz, dxi, dyi, dzi;

    using std::abs;

    if ((abs(dist.x) >= abs(dist.y)) && (abs(dist.x) >= abs(dist.z)))
    {
        dxi = 1024;
        dx = 512;
        dyi = (long)(!dist.y ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.x * 1024 / dist.y));
        dy = dyi / 2;
        dzi = (long)(!dist.z ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.x * 1024 / dist.z));
        dz = dzi / 2;
    }
    else if (abs(dist.y) >= abs(dist.z))
    {
        dyi = 1024;
        dy = 512;
        dxi = (long)(!dist.x ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.y * 1024 / dist.x));
        dx = dxi / 2;
        dzi = (long)(!dist.z ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.y * 1024 / dist.z));
        dz = dzi / 2;
    }
    else
    {
        dzi = 1024;
        dz = 512;
        dxi = (long)(!dist.x ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.z * 1024 / dist.x));
        dx = dxi / 2;
        dyi = (long)(!dist.y ? 0x3fffffff / VXL_MAX_SIZE : abs(dist.z * 1024 / dist.y));
        dy = dyi / 2;
    }
    if (dir.x >= 0)
        dx = dxi - dx;
    if (dir.y >= 0)
        dy = dyi - dy;
    if (dir.z >= 0)
        dz = dzi - dz;

    size_t count = 0;

    while (1)
    {
        cube_array[count] = cursor;

        count++;

        if (count >= CUBE_ARRAY_LENGTH)
            return count;

        if (cursor.x == x2 &&
            cursor.y == y2 &&
            cursor.z == z2) {
            // we have reached the end block
            return count;
        }

        if ((dz <= dx) && (dz <= dy))
        {
            cursor.z += dir.z;
            if (cursor.z < 0 || cursor.z >= MAXZDIM)
                // we have reached the z bounds of the map
                return count;
            dz += dzi;
        }
        else
        {
            if (dx < dy)
            {
                cursor.x += dir.x;
                if ((unsigned long)cursor.x >= VXL_MAX_SIZE)
                    return count;
                dx += dxi;
            }
            else
            {
                cursor.y += dir.y;
                if ((unsigned long)cursor.y >= VXL_MAX_SIZE)
                    return count;
                dy += dyi;
            }
        }
    }
}

// original C code

void reposition_player(PlayerType *p, Vector *position)
{
    p->e = p->p = *position;
    float f = p->lastclimb - ftotclk; /* FIXME meaningful name */
    if (f > -0.25f)
        p->e.z += (f + 0.25f) / 0.25f;
}

inline void set_orientation_vectors(Vector *o, Vector *s, Vector *h)
{
    float f = sqrtf(o->x * o->x + o->y * o->y);
    if (f == 0)
        return;
    s->x = -o->y / f;
    s->y = o->x / f;
    h->x = -o->z * s->y;
    h->y = o->z * s->x;
    h->z = o->x * s->y - o->y * s->x;
}

void reorient_player(PlayerType *p, Vector *orientation)
{
    p->f = *orientation;
    set_orientation_vectors(orientation, &p->s, &p->h);
}

int try_uncrouch(PlayerType *p)
{
    float x1 = p->p.x + 0.45f;
    float x2 = p->p.x - 0.45f;
    float y1 = p->p.y + 0.45f;
    float y2 = p->p.y - 0.45f;
    float z1 = p->p.z + 2.25f;
    float z2 = p->p.z - 1.35f;

    //first check if player can lower feet (in midair)
    if (p->airborne && !(clipbox(x1, y1, z1) || clipbox(x1, y2, z1) || clipbox(x2, y1, z1) || clipbox(x2, y2, z1)))
        return (1);
    //then check if they can raise their head
    else if (!(clipbox(x1, y1, z2) ||
               clipbox(x1, y2, z2) ||
               clipbox(x2, y1, z2) ||
               clipbox(x2, y2, z2)))
    {
        p->p.z -= 0.9f;
        p->e.z -= 0.9f;
        return (1);
    }
    return (0);
}

//player movement with autoclimb
void boxclipmove(PlayerType *p)
{
    float f = fsynctics * 32.f;
    float nx = f * p->v.x + p->p.x;
    float ny = f * p->v.y + p->p.y;

    float offset, m;
    if (p->crouch)
    {
        offset = 0.45f;
        m = 0.9f;
    }
    else
    {
        offset = 0.9f;
        m = 1.35f;
    }

    float nz = p->p.z + offset;

    long climb = 0;

    if (p->v.x < 0)
    {
        f = -0.45f;
    }
    else
    {
        f = 0.45f;
    }
    float z = m;

    while (z >= -1.36f && !clipbox(nx + f, p->p.y - 0.45f, nz + z) && !clipbox(nx + f, p->p.y + 0.45f, nz + z))
    {
        z -= 0.9f;
    }
    if (z < -1.36f)
    {
        p->p.x = nx;
    }
    else if (!p->crouch && p->f.z < 0.5f && !p->sprint)
    {
        z = 0.35f;

        while (z >= -2.36f && !clipbox(nx + f, p->p.y - 0.45f, nz + z) && !clipbox(nx + f, p->p.y + 0.45f, nz + z))
            z -= 0.9f;

        if (z < -2.36f)
        {
            p->p.x = nx;
            climb = 1;
        }
        else
            p->v.x = 0;
    }
    else
        p->v.x = 0;

    if (p->v.y < 0)
    {
        f = -0.45f;
    }
    else
    {
        f = 0.45f;
    }
    z = m;
    while (z >= -1.36f && !clipbox(p->p.x - 0.45f, ny + f, nz + z) && !clipbox(p->p.x + 0.45f, ny + f, nz + z))
        z -= 0.9f;
    if (z < -1.36f)
        p->p.y = ny;
    else if (!p->crouch && p->f.z < 0.5f && !p->sprint && !climb)
    {
        z = 0.35f;
        while (z >= -2.36f && !clipbox(p->p.x - 0.45f, ny + f, nz + z) && !clipbox(p->p.x + 0.45f, ny + f, nz + z))
            z -= 0.9f;
        if (z < -2.36f)
        {
            p->p.y = ny;
            climb = 1;
        }
        else
            p->v.y = 0;
    }
    else if (!climb)
        p->v.y = 0;

    if (climb)
    {
        p->v.x *= 0.5f;
        p->v.y *= 0.5f;
        p->lastclimb = ftotclk;
        nz--;
        m = -1.35f;
    }
    else
    {
        if (p->v.z < 0)
            m = -m;
        nz += p->v.z * fsynctics * 32.f;
    }

    p->airborne = 1;

    if (clipbox(p->p.x - 0.45f, p->p.y - 0.45f, nz + m) ||
        clipbox(p->p.x - 0.45f, p->p.y + 0.45f, nz + m) ||
        clipbox(p->p.x + 0.45f, p->p.y - 0.45f, nz + m) ||
        clipbox(p->p.x + 0.45f, p->p.y + 0.45f, nz + m))
    {
        if (p->v.z >= 0)
        {
            p->wade = p->p.z > 61;
            p->airborne = 0;
        }
        p->v.z = 0;
    }
    else
        p->p.z = nz - offset;

    reposition_player(p, &p->p);
}

long move_player(PlayerType *p)
{
    //move player and perform simple physics (gravity, momentum, friction)
    if (p->jump)
    {
        p->jump = 0;
        p->v.z = -0.36f;
    }

    float f = fsynctics; //player acceleration scalar
    if (p->airborne)
        f *= 0.1f;
    else if (p->crouch)
        f *= 0.3f;
    else if ((p->secondary_fire && p->weapon == WEAPON_PRIMARY) || p->sneak)
        f *= 0.5f;
    else if (p->sprint)
        f *= 1.3f;

    if ((p->mf || p->mb) && (p->ml || p->mr))
        f *= sqrt(2) / 2; //if strafe + forward/backwards then limit diagonal velocity

    if (p->mf)
    {
        p->v.x += p->f.x * f;
        p->v.y += p->f.y * f;
    }
    else if (p->mb)
    {
        p->v.x -= p->f.x * f;
        p->v.y -= p->f.y * f;
    }
    if (p->ml)
    {
        p->v.x -= p->s.x * f;
        p->v.y -= p->s.y * f;
    }
    else if (p->mr)
    {
        p->v.x += p->s.x * f;
        p->v.y += p->s.y * f;
    }

    f = fsynctics + 1;
    p->v.z += fsynctics;
    p->v.z /= f; //air friction
    if (p->wade)
        f = fsynctics * 6.f + 1; //water friction
    else if (!p->airborne)
        f = fsynctics * 4.f + 1; //ground friction
    p->v.x /= f;
    p->v.y /= f;
    float f2 = p->v.z;
    boxclipmove(p);
    //hit ground... check if hurt
    if (!p->v.z && (f2 > FALL_SLOW_DOWN))
    {
        //slow down on landing
        p->v.x *= 0.5f;
        p->v.y *= 0.5f;

        //return fall damage
        if (f2 > FALL_DAMAGE_VELOCITY)
        {
            f2 -= FALL_DAMAGE_VELOCITY;
            return ((long)(f2 * f2 * FALL_DAMAGE_SCALAR));
        }

        return (-1); // no fall damage but play fall sound
    }

    return (0); //no fall damage
}

GrenadeType *create_grenade(Vector *p, Vector *v)
{
    GrenadeType *g = new GrenadeType;
    g->p = *p;
    g->v = *v;
    return g;
}

// returns 1 if there was a collision, 2 if sound should be played
int move_grenade(GrenadeType *g)
{
    Vector fpos = g->p; //old position
    //do velocity & gravity (friction is negligible)
    float f = fsynctics * 32;
    g->v.z += fsynctics;
    g->p.x += g->v.x * f;
    g->p.y += g->v.y * f;
    g->p.z += g->v.z * f;
    //do rotation
    //FIX ME: Loses orientation after 45 degree bounce off wall
    // if(g->v.x > 0.1f || g->v.x < -0.1f || g->v.y > 0.1f || g->v.y < -0.1f)
    // {
    // f *= -0.5;
    // }
    //make it bounce (accurate)
    LongVector lp;
    lp.x = (long)floor(g->p.x);
    lp.y = (long)floor(g->p.y);
    lp.z = (long)floor(g->p.z);

    if (!clipworld(lp.x, lp.y, lp.z))
    {
        return 0; // we didn't hit anything, no collision
    }
    else
    { //hit a wall
        static const float BOUNCE_SOUND_THRESHOLD = 1.1f;

        int ret = 1;
        if (fabs(g->v.x) > BOUNCE_SOUND_THRESHOLD ||
            fabs(g->v.y) > BOUNCE_SOUND_THRESHOLD ||
            fabs(g->v.z) > BOUNCE_SOUND_THRESHOLD)
            ret = 2; // play sound

        LongVector lp2;
        lp2.x = (long)floor(fpos.x);
        lp2.y = (long)floor(fpos.y);
        lp2.z = (long)floor(fpos.z);
        if (lp.z != lp2.z && ((lp.x == lp2.x && lp.y == lp2.y) || !clipworld(lp.x, lp.y, lp2.z)))
            g->v.z = -g->v.z;
        else if (lp.x != lp2.x && ((lp.y == lp2.y && lp.z == lp2.z) || !clipworld(lp2.x, lp.y, lp.z)))
            g->v.x = -g->v.x;
        else if (lp.y != lp2.y && ((lp.x == lp2.x && lp.z == lp2.z) || !clipworld(lp.x, lp2.y, lp.z)))
            g->v.y = -g->v.y;
        g->p = fpos; //set back to old position
        g->v.x *= 0.36f;
        g->v.y *= 0.36f;
        g->v.z *= 0.36f;
        return ret;
    }
}

// C interface

PlayerType *create_player()
{
    PlayerType *player = new PlayerType;
    player->s.x = 0;
    player->s.y = 1;
    player->s.z = 0;
    player->h.x = 0;
    player->h.y = 0;
    player->h.z = 1;
    player->f.x = 1;
    player->f.y = 0;
    player->f.z = 0;
    player->p.x = 0;
    player->p.y = 0;
    player->p.z = 0.0f;
    player->e = player->p;
    player->v.x = player->v.y = player->v.z = 0;
    player->mf = player->mb = player->ml = player->mr = player->jump =
        player->crouch = player->sneak = 0;
    player->airborne = player->wade = 0;
    player->lastclimb = 0;
    player->alive = 1;
    return player;
}

void destroy_player(PlayerType *player)
{
    delete player;
}

void destroy_grenade(GrenadeType *grenade)
{
    delete grenade;
}

void set_globals(MapData *map, float time, float dt)
{
    global_map = map;
    ftotclk = time;
    fsynctics = dt;
}
