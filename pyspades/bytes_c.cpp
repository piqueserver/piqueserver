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

#include <iostream>
#include <sstream>
#include <string>
#include "Python.h"
using namespace std;

void * create_stream()
{
    stringstream * ss = new stringstream(stringstream::out | stringstream::binary);
    return (void*)ss;
}

void delete_stream(void * ss)
{
    delete (stringstream*)ss;
}

/*
read methods
*/

// byte

inline char read_byte(char * data)
{
    return data[0];
}

inline unsigned char read_ubyte(char * data)
{
    return ((unsigned char*)data)[0];
}

// short

inline short read_short(char * data, int big_endian)
{
    unsigned char * bytes = (unsigned char*)data;
    if (big_endian)
    {
        return (bytes[0] << 8) | bytes[1];
    }
    else
    {
        return bytes[0] | (bytes[1] << 8);
    }
}

inline unsigned short read_ushort(char * data, int big_endian)
{
    return (unsigned short)read_short(data, big_endian);
}

// int

inline int read_int(char * data, int big_endian)
{
    unsigned char * bytes = (unsigned char*)data;
    if (big_endian)
    {
        return (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3];
    }
    else
    {
        return bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24);
    }
}

inline unsigned int read_uint(char * data, int big_endian)
{
    return (unsigned int)read_int(data, big_endian);
}

// float

inline double read_float(char * data, int big_endian)
{
    return _PyFloat_Unpack4((const unsigned char*)data, !big_endian);
}

/*
write methods
*/

// byte

inline void write_byte(void * stream, char value)
{
    stringstream * ss = (stringstream*)stream;
    ss->put(value);
}

inline void write_ubyte(void * stream, unsigned char value)
{
    stringstream * ss = (stringstream*)stream;
    ss->put((char)value);
}

// short

inline void write_short(void * stream, short value, int big_endian)
{
    stringstream * ss = (stringstream*)stream;
    if (big_endian)
    {
        ss->put((char)(value >> 8));
        ss->put((char)value);
    }
    else
    {
        ss->put((char)value);
        ss->put((char)(value >> 8));
    }
}

inline void write_ushort(void * stream, unsigned short value, 
                         int big_endian)
{
    write_short(stream, (short)value, big_endian);
}

// int

inline void write_int(void * stream, int value, int big_endian)
{
    stringstream * ss = (stringstream*)stream;
    if (big_endian)
    {
        ss->put((char)(value >> 24));
        ss->put((char)(value >> 16));
        ss->put((char)(value >> 8));
        ss->put((char)value);
    }
    else
    {
        ss->put((char)value);
        ss->put((char)(value >> 8));
        ss->put((char)(value >> 16));
        ss->put((char)(value >> 24));
    }
}

inline void write_uint(void * stream, unsigned int value, 
                               int big_endian)
{
    write_int(stream, (int)value, big_endian);
}

// float

inline void write_float(void * stream, double value, int big_endian)
{
    stringstream * ss = (stringstream*)stream;
    char out[4];
    _PyFloat_Pack4(value, (unsigned char *)&out, !big_endian);
    ss->write(out, 4);
}

inline void write_string(void * stream, char * data, size_t size)
{
    stringstream * ss = (stringstream*)stream;
    ss->write(data, size);
    ss->put(0);
}

inline void write(void * stream, char * data, size_t size)
{
    stringstream * ss = (stringstream*)stream;
    ss->write(data, size);
}

inline void rewind_stream(void * stream, int bytes)
{
    stringstream * ss = (stringstream*)stream;
    ss->seekp(-bytes, stringstream::cur);
}

inline size_t get_stream_size(void * stream)
{
    stringstream * ss = (stringstream*)stream;
    return ss->str().length();
}

inline size_t get_stream_pos(void * stream)
{
    stringstream * ss = (stringstream*)stream;
    streampos pos = ss->tellp();
    if (pos == (streampos)-1)
        return 0;
    return pos;
}

inline PyObject * get_stream(void * stream)
{
    stringstream * ss = (stringstream*)stream;
    const string tmp = ss->str();
    return PyString_FromStringAndSize(tmp.c_str(), tmp.length());
}