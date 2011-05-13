/*
    Copyright (c) Mathias Kaerlev 2011.

    This file is part of pyspades.

    pyspades program is free software: you can redistribute it and/or modify
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

#define get_pos(x, y, z) (x + y * 512 + z * 512 * 512)

void load_vxl(unsigned char * v, long * colors, int * geometry)
{
    long i, x, y, z;
    for(z=0;z<64;z++)
      for(y=0;y<512;y++)
         for(x=0;x<512;x++)
            geometry[get_pos(x, y, z)] = 1;

    for(y=0;y<512;y++)
      for(x=0;x<512;x++)
      {
         z = 0;
         while (1)
         {
            for(i=z;i<v[1];i++)
                geometry[get_pos(x, y, i)] = 0;
            for(z=v[1];z<=v[2];z++)
                colors[get_pos(x, y, z)] = *(long *)&v[(z-v[1]+1)<<2];
            if (!v[0]) 
                break;
            z = v[2]-v[1]-v[0]+2; 
            v += v[0]*4;
            for(z+=v[3];z<v[3];z++) 
                colors[get_pos(x, y, z)] = *(long *)&v[(z-v[3])<<2];
         }
         v += ((((long)v[2])-((long)v[1])+2)<<2);
      }
}