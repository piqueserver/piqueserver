cdef extern from "vxl_c.cpp":
    enum:
        MAP_X
        MAP_Y
        MAP_Z
        DEFAULT_COLOR
    struct MapData:
        pass
    struct MapGenerator:
        pass
    MapGenerator * create_map_generator(MapData * original)
    void delete_map_generator(MapGenerator * generator)
    object get_generator_data(MapGenerator * generator, int columns)
    MapData * load_vxl(unsigned char * v)
    MapData * copy_map(MapData * map)
    void delete_vxl(MapData * map)
    object save_vxl(MapData * map)
    int check_node(int x, int y, int z, MapData * map, int destroy)
    bint get_solid(int x, int y, int z, MapData * map)
    int get_color(int x, int y, int z, MapData * map)
    void set_point(int x, int y, int z, MapData * map, bint solid, int color)
    void set_column_solid(int x, int y, int start_z, int end_z,
        MapData * map, bint solid)
    void set_column_color(int x, int y, int start_z, int end_z,
        MapData * map, int color)
    int get_random_point(int x1, int y1, int x2, int y2, MapData * map, 
        float random_1, float random_2, int * x, int * y)
    bint is_valid_position(int x, int y, int z)
    void update_shadows(MapData * map)

cdef class VXLData:
    cdef MapData * map
    
    cpdef get_solid(self, int x, int y, int z)
    cpdef get_color(self, int x, int y, int z)
    cpdef tuple get_random_point(self, int x1, int y1, int x2, int y2)
    cpdef int get_z(self, int x, int y, int start = ?)
    cpdef int get_height(self, int x, int y)
    cpdef bint has_neighbors(self, int x, int y, int z)
    cpdef bint is_surface(self, int x, int y, int z)
    cpdef list get_neighbors(self, int x, int y, int z)
    cpdef int check_node(self, int x, int y, int z, bint destroy = ?)
    cpdef bint build_point(self, int x, int y, int z, tuple color)
    cpdef bint set_column_fast(self, int x, int y, int start_z,
        int end_z, int end_color_z, int color)
    cpdef update_shadows(self)