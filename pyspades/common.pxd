# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

cdef extern from "Python.h":
    object PyBytes_FromStringAndSize(char*,Py_ssize_t)
    char* PyBytes_AsString(object)

cdef inline object allocate_memory(int size, char ** i):
    if size < 0:
        size = 0
    cdef object ob = PyBytes_FromStringAndSize(NULL, size)
    i[0] = PyBytes_AsString(ob)
    return ob

cdef extern from "common_c.h":
    cdef cppclass Vector:
        float x, y, z
        Vector()
        Vector(float x, float y, float z)
        void set(float x, float y, float z)

    struct LongVector:
        int x, y, z

    void destroy_vector(Vector*)

cdef inline int check_default_int(int value, int default) except -1:
    if value != default:
        raise ValueError(
            'check_default() failed: was %s, should be %s' % (value, default))
    return 0

cdef class Quaternion
cdef class Vertex3:
    cdef Vector * value
    cdef bint is_ref
    cpdef Quaternion get_rotation_to(self, Vertex3 A)

cdef class Quaternion:
    cdef public:
        double w, x, y, z
    cpdef Quaternion set_angle_axis(self, double radians, Vertex3 axis)
    cpdef Quaternion slerp(self, Quaternion q, double t)
    cpdef Quaternion nlerp(self, Quaternion q, double t)
    cpdef Vertex3 transform_vector(self, Vertex3 v)
    cpdef Vertex3 inverse_transform_vector(self, Vertex3 v)

cdef inline Vertex3 create_proxy_vector(Vector * v):
    cdef Vertex3 new_vector = Vertex3(is_ref = True)
    new_vector.value = v
    return new_vector

cdef inline Vertex3 create_vertex3(float x, float y, float z):
    # faster way of creating Vertex3 instances
    cdef Vertex3 new_vertex = Vertex3(is_ref = True)
    new_vertex.value = new Vector(x, y, z)
    new_vertex.is_ref = False
    return new_vertex
