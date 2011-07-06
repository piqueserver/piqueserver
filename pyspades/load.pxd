cdef extern from "load_c.cpp":
    enum:
        MAP_X
        MAP_Y
        MAP_Z
        DEFAULT_COLOR
    struct MapData:
        pass
    MapData * load_vxl(unsigned char * v)
    void delete_vxl(MapData * map)
    object save_vxl(MapData * map)
    int check_node(int x, int y, int z, MapData * map, int destroy)
    bint get_solid(int x, int y, int z, MapData * map)
    int get_color(int x, int y, int z, MapData * map)
    void set_point(int x, int y, int z, MapData * map, bint solid, int color)

cdef class VXLData:
    cdef MapData * map

    cpdef int get_solid(self, int x, int y, int z)
    cpdef int get_color(self, int x, int y, int z)
    cpdef int get_z(self, int x, int y, int start = ?)
    cpdef int get_height(self, int x, int y)
    cpdef bint has_neighbors(self, int x, int y, int z)
    cpdef bint is_surface(self, int x, int y, int z)
    cpdef list get_neighbors(self, int x, int y, int z)
    cpdef bint check_node(self, int x, int y, int z, bint destroy = ?)
    cpdef bint set_point(self, int x, int y, int z, tuple color_tuple, 
                         bint user = ?)
    cpdef bint set_point_unsafe(self, int x, int y, int z, tuple color_tuple)