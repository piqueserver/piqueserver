from pyspades.load cimport VXLData
from opengl cimport *

cdef extern from "stdlib.h":
    void * malloc(size_t size)

cdef class Renderer:
    cdef VXLData map
    cdef GLfloat * vertex_array
    cdef int count
    def __init__(self, VXLData map):
        self.map = map
        cdef int x_orig, y_orig, z_orig
        cdef int x, y, z
        cdef int count = 0
        for x_orig in range(512):
            for y_orig in range(512):
                for z_orig in range(64):
                    color = map.get_color(x_orig, y_orig, z_orig)
                    if color == 0:
                        continue
                    count += 1
        self.count = count
        self.vertex_array = <GLfloat *>malloc(sizeof(GLfloat) * 24 * 3 * count)
        cdef GLfloat * vertex = self.vertex_array
        # self.color_array = <GLfloat *>malloc(sizeof(GLfloat) * 24 * count)
        count = 0
        for x_orig in range(512):
            for y_orig in range(512):
                for z_orig in range(64):
                    color = map.get_color(x_orig, y_orig, z_orig)
                    if color == 0:
                        continue
                    z = y_orig
                    y = -z_orig
                    x = x_orig
                    
                    # face 1
                    vertex[count * 24 * 3] = x + 0.5
                    vertex[count * 24 * 3 + 1] = y + 0.5
                    vertex[count * 24 * 3 + 2] = z - 0.5
                    
                    vertex[count * 24 * 3 + 3] = x - 0.5
                    vertex[count * 24 * 3 + 4] = y + 0.5
                    vertex[count * 24 * 3 + 5] = z - 0.5
                    
                    vertex[count * 24 * 3 + 6] = x - 0.5
                    vertex[count * 24 * 3 + 7] = y + 0.5
                    vertex[count * 24 * 3 + 8] = z + 0.5
                    
                    vertex[count * 24 * 3 + 9] = x + 0.5
                    vertex[count * 24 * 3 + 10] = y + 0.5
                    vertex[count * 24 * 3 + 11] = z + 0.5
                    # face 2
                    vertex[count * 24 * 3 + 12] = x + 0.5
                    vertex[count * 24 * 3 + 13] = y - 0.5
                    vertex[count * 24 * 3 + 14] = z + 0.5
                    
                    vertex[count * 24 * 3 + 15] = x - 0.5
                    vertex[count * 24 * 3 + 16] = y - 0.5
                    vertex[count * 24 * 3 + 17] = z + 0.5
                    
                    vertex[count * 24 * 3 + 18] = x - 0.5
                    vertex[count * 24 * 3 + 19] = y - 0.5
                    vertex[count * 24 * 3 + 20] = z - 0.5
                    
                    vertex[count * 24 * 3 + 21] = x + 0.5
                    vertex[count * 24 * 3 + 22] = y - 0.5
                    vertex[count * 24 * 3 + 23] = z - 0.5
                    # face 3
                    vertex[count * 24 * 3 + 24] = x + 0.5
                    vertex[count * 24 * 3 + 25] = y + 0.5
                    vertex[count * 24 * 3 + 26] = z + 0.5
                    
                    vertex[count * 24 * 3 + 27] = x - 0.5
                    vertex[count * 24 * 3 + 28] = y + 0.5
                    vertex[count * 24 * 3 + 29] = z + 0.5
                    
                    vertex[count * 24 * 3 + 30] = x - 0.5
                    vertex[count * 24 * 3 + 31] = y - 0.5
                    vertex[count * 24 * 3 + 32] = z + 0.5
                    
                    vertex[count * 24 * 3 + 33] = x + 0.5
                    vertex[count * 24 * 3 + 34] = y - 0.5
                    vertex[count * 24 * 3 + 35] = z + 0.5
                    # face 4
                    vertex[count * 24 * 3 + 36] = x + 0.5
                    vertex[count * 24 * 3 + 37] = y - 0.5
                    vertex[count * 24 * 3 + 38] = z - 0.5
                    
                    vertex[count * 24 * 3 + 39] = x - 0.5
                    vertex[count * 24 * 3 + 40] = y - 0.5
                    vertex[count * 24 * 3 + 41] = z - 0.5
                    
                    vertex[count * 24 * 3 + 42] = x - 0.5
                    vertex[count * 24 * 3 + 43] = y + 0.5
                    vertex[count * 24 * 3 + 44] = z - 0.5
                    
                    vertex[count * 24 * 3 + 45] = x + 0.5
                    vertex[count * 24 * 3 + 46] = y + 0.5
                    vertex[count * 24 * 3 + 47] = z - 0.5
                    # face 5
                    vertex[count * 24 * 3 + 48] = x - 0.5
                    vertex[count * 24 * 3 + 49] = y + 0.5
                    vertex[count * 24 * 3 + 50] = z + 0.5
                    
                    vertex[count * 24 * 3 + 51] = x - 0.5
                    vertex[count * 24 * 3 + 52] = y + 0.5
                    vertex[count * 24 * 3 + 53] = z - 0.5
                    
                    vertex[count * 24 * 3 + 54] = x - 0.5
                    vertex[count * 24 * 3 + 55] = y - 0.5
                    vertex[count * 24 * 3 + 56] = z - 0.5
                    
                    vertex[count * 24 * 3 + 57] = x - 0.5
                    vertex[count * 24 * 3 + 58] = y - 0.5
                    vertex[count * 24 * 3 + 59] = z + 0.5
                    # face 6
                    vertex[count * 24 * 3 + 60] = x + 0.5
                    vertex[count * 24 * 3 + 61] = y + 0.5
                    vertex[count * 24 * 3 + 62] = z - 0.5
                    
                    vertex[count * 24 * 3 + 63] = x + 0.5
                    vertex[count * 24 * 3 + 64] = y + 0.5
                    vertex[count * 24 * 3 + 65] = z + 0.5
                    
                    vertex[count * 24 * 3 + 66] = x + 0.5
                    vertex[count * 24 * 3 + 67] = y - 0.5
                    vertex[count * 24 * 3 + 68] = z + 0.5
                    
                    vertex[count * 24 * 3 + 69] = x + 0.5
                    vertex[count * 24 * 3 + 70] = y - 0.5
                    vertex[count * 24 * 3 + 71] = z - 0.5
                    
                    count += 1
    
    def draw(self):
        glEnable(GL_TEXTURE_2D)
        glNormal3f(0.0, 0.0, 1.0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, &self.vertex_array[0])
        glDrawArrays(GL_QUADS, 0, self.count * 24)
        glDisableClientState(GL_VERTEX_ARRAY)
        return
        cdef int x_orig, y_orig, z_orig
        cdef int x, y, z
        cdef bint solid
        cdef int color
        cdef int r, g, b, a
        glBegin(GL_QUADS)
        for x_orig in range(40):
            for y_orig in range(40):
                for z_orig in range(64):
                    color = self.map.get_color(x_orig, y_orig, z_orig)
                    if color == 0:
                        continue
                    b = color & 0xFF
                    g = (color & 0xFF00) >> 8
                    r = (color & 0xFF0000) >> 16
                    a = (((color & 0xFF000000) >> 24) / 128.0) * 255
                    glColor4ub(r, g, b, 255)
                    
                    z = y_orig
                    y = -z_orig
                    x = x_orig
                    
                    glVertex3f(x + 0.5, y + 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y + 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y + 0.5, z + 0.5)
                    glVertex3f(x + 0.5, y + 0.5, z + 0.5)
                    
                    glVertex3f(x + 0.5, y - 0.5, z + 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z + 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z - 0.5)
                    glVertex3f(x + 0.5, y - 0.5, z - 0.5)
                    
                    glVertex3f(x + 0.5, y + 0.5, z + 0.5)
                    glVertex3f(x - 0.5, y + 0.5, z + 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z + 0.5)
                    glVertex3f(x + 0.5, y - 0.5, z + 0.5)
                    
                    glVertex3f(x + 0.5, y - 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y + 0.5, z - 0.5)
                    glVertex3f(x + 0.5, y + 0.5, z - 0.5)
                    
                    glVertex3f(x - 0.5, y + 0.5, z + 0.5)
                    glVertex3f(x - 0.5, y + 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z - 0.5)
                    glVertex3f(x - 0.5, y - 0.5, z + 0.5)
                    
                    glVertex3f(x + 0.5, y + 0.5, z - 0.5)
                    glVertex3f(x + 0.5, y + 0.5, z + 0.5)
                    glVertex3f(x + 0.5, y - 0.5, z + 0.5)
                    glVertex3f(x + 0.5, y - 0.5, z - 0.5)
        glEnd()