/*
    Copyright (c) Mathias Kaerlev 2011.

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

#define MAP_X 512
#define MAP_Y 512
#define MAP_Z 64
#define get_pos(x, y, z) (x + (y) * MAP_Y + (z) * MAP_X * MAP_Y)
#define DEFAULT_COLOR 0xFF674028

#include <iostream>
#include <sstream>
#include "Python.h"
#include <vector>
#include <map>
#include <bitset>
using namespace std;

struct MapData
{
    bitset<MAP_X * MAP_Y * MAP_Z> geometry;
    std::map<int, int> colors;
};

int inline get_solid(int x, int y, int z, MapData * map)
{
    return map->geometry[get_pos(x, y, z)];
}

int inline get_color(int x, int y, int z, MapData * map)
{
    return map->colors[get_pos(x, y, z)];
}

void inline set_point(int x, int y, int z, MapData * map, bool solid, int color)
{
    int i = get_pos(x, y, z);
    map->geometry[i] = solid;
    if (!solid)
        map->colors.erase(i);
    else
        map->colors[i] = color;
}

MapData * load_vxl(unsigned char * v)
{
   MapData * map = new MapData;
   if (v == NULL)
    return map;
   int x,y,z;
   for (y=0; y < 512; ++y) {
      for (x=0; x < 512; ++x) {
         for (z=0; z < 64; ++z) {
            map->geometry[get_pos(x, y, z)] = 1;
         }
         z = 0;
         for(;;) {
            int *color;
            int i;
            int number_4byte_chunks = v[0];
            int top_color_start = v[1];
            int top_color_end   = v[2]; // inclusive
            int bottom_color_start;
            int bottom_color_end; // exclusive
            int len_top;
            int len_bottom;
            for(i=z; i < top_color_start; i++)
               map->geometry[get_pos(x, y, i)] = 0;
            color = (int *) (v+4);
            for(z=top_color_start; z <= top_color_end; z++)
               map->colors[get_pos(x, y, z)] = *color++;
            len_bottom = top_color_end - top_color_start + 1;

            // check for end of data marker
            if (number_4byte_chunks == 0) {
               // infer ACTUAL number of 4-byte chunks from the length of the color data
               v += 4 * (len_bottom + 1);
               break;
            }
            
            // infer the number of bottom colors in next span from chunk length
            len_top = (number_4byte_chunks-1) - len_bottom;

            // now skip the v pointer past the data to the beginning of the next span
            v += v[0]*4;

            bottom_color_end   = v[3]; // aka air start
            bottom_color_start = bottom_color_end - len_top;
            for(z=bottom_color_start; z < bottom_color_end; ++z) {
               map->colors[get_pos(x, y, z)] = *color++;
            }
         }
      }
   }
   return map;
}

void inline delete_vxl(MapData * map)
{
    delete map;
}

struct Position {
    int x; 
    int y;
    int z;
    
    bool operator == (Position const& pos) const
        {
        return (x == pos.x && y == pos.y && z == pos.z);
    }
};

inline void add_node(int x, int y, int z, MapData * map,
                     vector<Position> & nodes)
{
    if (x < 0 || x > 511 ||
        y < 0 || y > 511 ||
        z < 0 || z > 63)
        return;
    if (!map->geometry[get_pos(x, y, z)])
        return;
    Position new_pos;
    new_pos.x = x;
    new_pos.y = y;
    new_pos.z = z;
    nodes.push_back(new_pos);
}

int check_node(int x, int y, int z, MapData * map, int destroy)
{
    vector<Position> nodes;
    
    std::map<int, bool> marked;
    Position new_pos;
    new_pos.x = x;
    new_pos.y = y;
    new_pos.z = z;
    nodes.push_back(new_pos);
    
    while (!nodes.empty()) {
        Position node = nodes.back();
        nodes.pop_back();
        
        if (node.z >= 62) {
            return 1;
        }
        
        x = node.x;
        y = node.y;
        z = node.z;
        
        int i = get_pos(x, y, z);
	
        // already visited?
        if (!marked[i]) {
            marked[i] = true;
            
            add_node(x, y, z - 1, map, nodes);
            add_node(x, y - 1, z, map, nodes);
            add_node(x, y + 1, z, map, nodes);
            add_node(x - 1, y, z, map, nodes);
            add_node(x + 1, y, z, map, nodes);
            add_node(x, y, z + 1, map, nodes);
        }
    }

    // destroy the node's path!
    
    if (destroy) {
        for (std::map<int, bool>::const_iterator iter = marked.begin(); 
             iter != marked.end(); ++iter)
        {
            map->geometry[iter->first] = 0;
            map->colors[iter->first] = 0;
        }
    }
    
    return 0;
}

// write_map/save_vxl function from stb/nothings - thanks a lot for the 
// public-domain code!

inline int is_surface(MapData * map, int x, int y, int z)
{
   if (z == 0) return 1;
   if (map->geometry[get_pos(x, y, z)]==0) return 0;
   if (x   >   0 && map->geometry[get_pos(x-1, y, z)]==0) return 1;
   if (x+1 < 512 && map->geometry[get_pos(x+1, y, z)]==0) return 1;
   if (y   >   0 && map->geometry[get_pos(x, y-1, z)]==0) return 1;
   if (y+1 < 512 && map->geometry[get_pos(x, y+1, z)]==0) return 1;
   if (z   >   0 && map->geometry[get_pos(x, y, z-1)]==0) return 1;
   if (z+1 <  64 && map->geometry[get_pos(x, y, z+1)]==0) return 1;
   return 0;
}

inline void write_color(char * out, int color)
{
   // assume color is ARGB native, but endianness is unknown
   if (color == 0)
       color = DEFAULT_COLOR;
   // file format endianness is ARGB little endian, i.e. B,G,R,A
   *out = (char)(color >> 0);
   out += 1;
   *out = (char) (color >> 8);
   out += 1;
   *out = (char) (color >> 16);
   out += 1;
   *out = (char) (color >> 24);
   out += 1;
}

char * out_global = 0;

PyObject * save_vxl(MapData * map)
{
   int i,j,k;
   if (out_global == 0)
   {
       out_global = (char *)malloc(6 * 1024 * 1024); // allocate 6 mb
   }
   char * out = out_global;

   for (j=0; j < MAP_Y; ++j) {
      for (i=0; i < MAP_X; ++i) {
         int written_colors = 0;
         int previous_bottom_colors = 0;
         int current_bottom_colors = 0;
         int middle_start = 0;

         k = 0;
         while (k < MAP_Z) {
            int z;

            int air_start;
            int top_colors_start;
            int top_colors_end; // exclusive
            int bottom_colors_start;
            int bottom_colors_end; // exclusive
            int top_colors_len;
            int bottom_colors_len;
            int colors;
            // find the air region
            air_start = k;
            while (k < MAP_Z && !map->geometry[get_pos(i, j, k)])
               ++k;
            // find the top region
            top_colors_start = k;
            while (k < MAP_Z && is_surface(map, i, j, k))
               ++k;
            top_colors_end = k;

            // now skip past the solid voxels
            while (k < MAP_Z && map->geometry[get_pos(i, j, k)] && 
                   !is_surface(map, i,j,k))
               ++k;

            // at the end of the solid voxels, we have colored voxels.
            // in the "normal" case they're bottom colors; but it's
            // possible to have air-color-solid-color-solid-color-air,
            // which we encode as air-color-solid-0, 0-color-solid-air
          
            // so figure out if we have any bottom colors at this point
            bottom_colors_start = k;

            z = k;
            while (z < MAP_Z && is_surface(map, i,j, z))
               ++z;

            if (z == MAP_Z)
               ; // in this case, the bottom colors of this span are empty, because we'l emit as top colors
            else {
               // otherwise, these are real bottom colors so we can write them
               while (is_surface(map, i,j,k))  
                  ++k;
            }
            bottom_colors_end = k;

            // now we're ready to write a span
            top_colors_len    = top_colors_end    - top_colors_start;
            bottom_colors_len = bottom_colors_end - bottom_colors_start;

            colors = top_colors_len + bottom_colors_len;

            if (k == MAP_Z)
            {
               *out = 0;
               out += 1;
            }
            else
            {
               *out = colors + 1;
               out += 1;
            }
            *out = top_colors_start;
            out += 1;
            *out = top_colors_end - 1;
            out += 1;
            *out = air_start;
            out += 1;

            for (z=0; z < top_colors_len; ++z)
            {
               // printf("writing top color at %d\n", out - out_global);
               write_color(out, map->colors[get_pos(i, j, 
                   top_colors_start + z)]);
               out += 4;
            }
            for (z=0; z < bottom_colors_len; ++z)
            {
               // printf("writing top color at %d\n", out - out_global);
               write_color(out, map->colors[get_pos(i, j, 
                   bottom_colors_start + z)]);
               out += 4;
            }
         }  
      }
   }
   return PyString_FromStringAndSize((char *)out_global, out - out_global);
}