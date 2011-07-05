cdef class World

cdef class Object:
    cdef:
        double x, y, z
        World world
    
    def __init__(self, World world):
        self.world = world
    
    cdef void update(self):
        pass

cdef class Grenade(Object):
    cdef void update(self):
        pass

cdef class Character(Object):
    cdef void update(self):
        pass

cdef class World:
    cdef public:
        list objects
    
    def __init__(self):
        self.objects = []
    
    def update(self):
        pass
        
    def create_object(self, klass):
        cdef Object new_object = klass(self)
        self.objects.append(new_object)