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
#include <bitset>

#ifdef _MSC_VER
#include <hash_map>
#define map_type stdext::hash_map
#else
#include <tr1/unordered_map>
#define map_type std::tr1::unordered_map
#endif

using namespace std;

void inline limit(int * value, int min, int max)
{
    if (*value > max) {
        *value = max;
    } 
    else if (*value < min)
    {
        *value = min;
    }
}

int inline valid_position(int x, int y, int z)
{
    return x >= 0 && x < 512 && y >= 0 && y < 512 && z >= 0 && z < 64;
}

struct MapData
{
    bitset<MAP_X * MAP_Y * MAP_Z> geometry;
    map_type<int, int> colors;

};

int inline get_solid(int x, int y, int z, MapData * map)
{
    if (!valid_position(x, y, z))
        return 0;
    return map->geometry[get_pos(x, y, z)];
}

int inline get_color(int x, int y, int z, MapData * map)
{
    if (!valid_position(x, y, z))
        return 0;
    map_type<int, int>::const_iterator iter = map->colors.find(
        get_pos(x, y, z));
    if (iter == map->colors.end())
        return 0;
    return iter->second;
}

void inline set_point(int x, int y, int z, MapData * map, bool solid, int color)
{
    if (!valid_position(x, y, z))
        return;
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
    
    map_type<int, bool> marked;
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
        for (map_type<int, bool>::const_iterator iter = marked.begin(); 
             iter != marked.end(); ++iter)
        {
            map->geometry[iter->first] = 0;
            map->colors.erase(iter->first);
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

inline int get_write_color(MapData * map, int x, int y, int z)
{
    map_type<int, int>::const_iterator iter = map->colors.find(
        get_pos(x, y, z));
    if (iter == map->colors.end())
        return DEFAULT_COLOR;
    return iter->second;
}

inline void write_color(char ** out, int color)
{
   // assume color is ARGB native, but endianness is unknown
   // file format endianness is ARGB little endian, i.e. B,G,R,A
   **out = (char)(color >> 0);
   *out += 1;
   **out = (char) (color >> 8);
   *out += 1;
   **out = (char) (color >> 16);
   *out += 1;
   **out = (char) (color >> 24);
   *out += 1;
}

char * out_global = 0;

void create_temp()
{
   if (out_global == 0)
       out_global = (char *)malloc(10 * 1024 * 1024); // allocate 10 mb
}

PyObject * save_vxl(MapData * map)
{
   int i,j,k;
   create_temp();
   char * out = out_global;

   for (j=0; j < MAP_Y; ++j) {
      for (i=0; i < MAP_X; ++i) {
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
               write_color(&out, get_write_color(map, i, j, 
                   top_colors_start + z));
            }
            for (z=0; z < bottom_colors_len; ++z)
            {
               write_color(&out, get_write_color(map, i, j, 
                   bottom_colors_start + z));
            }
         }  
      }
   }
   return PyString_FromStringAndSize((char *)out_global, out - out_global);
}

inline MapData * copy_map(MapData * map)
{
    return new MapData(*map);
}

struct Point2D
{
    int x, y;
};

inline unsigned int random(unsigned int a, unsigned int b, float value)
{
    return (unsigned int)(value * (b - a) + a);
}

inline void get_random_point(int x1, int y1, int x2, int y2, MapData * map,
                             float random_1, float random_2,
                             int * end_x, int * end_y)
{
    limit(&x1, 0, 511);
    limit(&y1, 0, 511);
    limit(&x2, 0, 511);
    limit(&y2, 0, 511);
    vector<Point2D> items;
    int size = 0;
    int x, y;
    for(x = x1; x < x2; x++){
        for(y = y1; y < y2; y++) {
            if (map->geometry[get_pos(x, y, 62)]) {
                Point2D item;
                item.x = x;
                item.y = y;
                items.push_back(item);
                size += 1;
            }
        }
    }
    if (size == 0) {
        *end_x = random(x1, x2, random_1);
        *end_y = random(y1, y2, random_2);
    } else {
        Point2D item = items[random(0, size, random_1)];
        *end_x = item.x;
        *end_y = item.y;
    }
}

struct MapGenerator
{
    MapData * map;
    int x, y;
};

MapGenerator * create_map_generator(MapData * original)
{
    MapGenerator * generator = new MapGenerator;
    generator->map = copy_map(original);
    generator->x = 0;
    generator->y = 0;
    return generator;
}

void delete_map_generator(MapGenerator * generator)
{
    delete_vxl(generator->map);
    delete generator;
}

PyObject * get_generator_data(MapGenerator * generator, int columns)
{
   int i, j, k;
   create_temp();
   char * out = out_global;
   int column = 0;
   MapData * map = generator->map;

   for (j=generator->y; j < MAP_Y; ++j) {
      for (i=generator->x; i < MAP_X; ++i) {
         if (column == columns)
         {
             goto done;
         }
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
               write_color(&out, get_write_color(map, i, j, 
                   top_colors_start + z));
            }
            for (z=0; z < bottom_colors_len; ++z)
            {
               write_color(&out, get_write_color(map, i, j, 
                   bottom_colors_start + z));
            }
         }
         column++;
      }
   generator->x = 0;
   }
done:
   generator->x = i;
   generator->y = j;
   return PyString_FromStringAndSize((char *)out_global, out - out_global);
}