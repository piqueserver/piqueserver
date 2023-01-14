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

#include "Python.h"
#include <iostream>
#include <sstream>
#include <string>
using namespace std;

stringstream *create_stream()
{
    stringstream *ss = new stringstream(stringstream::out | stringstream::binary);
    return ss;
}

void delete_stream(stringstream *ss)
{
    delete ss;
}

/*
read methods
*/

// byte

inline int8_t read_byte(char *data)
{
    return data[0];
}

inline uint8_t read_ubyte(char *data)
{
    return ((unsigned char *)data)[0];
}

// short

inline int16_t read_short(char *data, int big_endian)
{
    unsigned char *bytes = (unsigned char *)data;
    if (big_endian)
    {
        return (bytes[0] << 8) | bytes[1];
    }
    else
    {
        return bytes[0] | (bytes[1] << 8);
    }
}

inline uint16_t read_ushort(char *data, int big_endian)
{
    return (unsigned short)read_short(data, big_endian);
}

// int

inline int32_t read_int(char *data, int big_endian)
{
    unsigned char *bytes = (unsigned char *)data;
    if (big_endian)
    {
        return (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3];
    }
    else
    {
        return bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24);
    }
}

inline uint32_t read_uint(char *data, int big_endian)
{
    return (unsigned int)read_int(data, big_endian);
}

// float

inline double read_float(char *data, int big_endian)
{
    #if (PY_MAJOR_VERSION >= 3 && PY_MINOR_VERSION >= 11)
        return PyFloat_Unpack4((const char *)data, !big_endian);
    #else
        return _PyFloat_Unpack4((const unsigned char *)data, !big_endian);
    #endif
}

/*
write methods
*/

// byte

inline void write_byte(stringstream *ss, int8_t value)
{
    ss->put(value);
}

inline void write_ubyte(stringstream *ss, uint8_t value)
{
    ss->put((char)value);
}

// short

inline void write_short(stringstream *ss, int16_t value, int big_endian)
{
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

inline void write_ushort(stringstream *ss, uint16_t value,
                         int big_endian)
{
    write_short(ss, (short)value, big_endian);
}

// int

inline void write_int(stringstream *ss, int32_t value, int big_endian)
{
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

inline void write_uint(stringstream *ss, uint32_t value,
                       int big_endian)
{
    write_int(ss, (int)value, big_endian);
}

// float

inline void write_float(stringstream *ss, double value, int big_endian)
{
    char out[4];
    #if (PY_MAJOR_VERSION >= 3 && PY_MINOR_VERSION >= 11)
        PyFloat_Pack4(value, (char *)&out, !big_endian);
    #else
        _PyFloat_Pack4(value, (unsigned char *)&out, !big_endian);
    #endif
    ss->write(out, 4);
}

inline void write_string(stringstream *ss, char *data, size_t size)
{
    ss->write(data, size);
    ss->put(0);
}

inline void write(stringstream *ss, char *data, size_t size)
{
    ss->write(data, size);
}

inline void rewind_stream(stringstream *ss, int bytes)
{
    ss->seekp(-bytes, stringstream::cur);
}

inline size_t get_stream_size(stringstream *ss)
{
    return ss->str().length();
}

inline size_t get_stream_pos(stringstream *ss)
{
    streampos pos = ss->tellp();
    if (pos == (streampos)-1)
        return 0;
    return pos;
}

inline PyObject *get_stream(stringstream *ss)
{
    const string tmp = ss->str();
    return PyBytes_FromStringAndSize(tmp.c_str(), tmp.length());
}
