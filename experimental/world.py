class Object(object):
    x = y = z = None
    world = None
    
    def __init__(self, world):
        self.world = world
    
    def update(self):
        pass

class Grenade(Object):
    def update(self):
        pass

class Character(Object):
    def update(self):
        pass

class World(object):
    objects = None
    map = None
    
    def __init__(self):
        self.objects = []
    
    def update(self):
        pass
        
    def create_object(self, klass):
        new_object = klass(self)
        self.objects.append(new_object)