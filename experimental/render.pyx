from pyspades.load cimport VXLData
from opengl cimport *

cdef extern from "stdlib.h":
    void * malloc(size_t size)

cdef class Renderer:
    cdef VXLData map
    cdef GLfloat * vertex_array
    def __init__(self, VXLData map):
        self.map = map
        self.points = []
        cdef int x_orig, y_orig, z_orig
        cdef int x, y, z
        cdef int count
        cdef Point point
        for x_orig in range(512):
            for y_orig in range(512):
                for z_orig in range(64):
                    color = map.get_color(x_orig, y_orig, z_orig)
                    if color == 0:
                        continue
                    count += 1
        self.vertex_array = <GLfloat *>malloc(sizeof(GLfloat) * 24)
    
    def draw(self):
        glEnable(GL_TEXTURE_2D)
        glNormal3f(0.0, 0.0, 1.0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(4, GL_FLOAT, 0, &self.vertex_array[0])
        glDrawArrays(GL_QUADS, 0, 4)
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