"""
Author: Nick Christensen AKA a_girl
Distant Drag Build Client Bug Patch for (0.75) and possibly (0.76)
This server side script prevents exploitation of a mostly unknown client bug regarding drag building.
Exploiters of this bug are able to drag build from any remote point to which they have a clear line of sight
to their current location (as long as they don't crash their client by going too far out).
Obviously this ability has some heavy implications in situations involving bridging or towering.
I strongly recommended that this script be implemented in any building oriented game mode such as babel or push.
Just add it to your script list in your config file and it will do the rest.
To avoid the proliferation of the knowledge of this bug, I will not go into details on how to perform it.
"""

from pyspades.world import *

def distance(a, b):                                                             #calculate the distance between an object with x, y, and z members and a tuple containing (x, y, z) coords.
    x1, y1, z1 = a.x, a.y, a.z
    x2, y2, z2 = b
    x = x2 - x1
    y = y2 - y1
    z = z2 - z1
    sum = (x ** 2) + (y ** 2) + (z ** 2)
    return math.sqrt(sum)

def apply_script(protocol, connection, config):
    class fbpatchConnection(connection):

        line_build = True

        def on_secondary_fire_set(self, secondary):
            if secondary == True:                                                  #if right mouse button has been clicked to initiate drag building; distinguishes from the right click release that marks the end point.
                if self.tool == 1:                                                 #1 refers to block tool; if the tool in hand is a block
                    position = self.world_object.position                         #grab player current position at drag build start
                    vector = self.world_object.orientation                         #grab player current orientation at drag build start
                    vector.normalize()                                             #probably unnecessary, but makes sure vector values are between 0 and 1 inclusive
                    c = Character(self.world_object.world, position, vector)    #creates a line object starting at player and following their point of view.
                    line_start = c.cast_ray()                                     #finds coordinates of the first block this line strikes.
                    if line_start:                                                 #if player is pointing at a valid point.  Distant solid blocks will return False
                        if distance(position, line_start) > 6:                  #5.5 is pretty close to the max distance you can place a block. Rounded up to 6 for safety.
                            self.line_build = False
                        else:                                                    #line build will only be allowed if the remote point is within 6 blocks of where they were when they first clicked.
                            self.line_build = True
                    else:                                                        #if the remote point is distant, or it isn't a valid point, no line build will be considered
                        self.line_build = False
            return connection.on_secondary_fire_set(self, secondary)

        def on_line_build_attempt(self, points):
            if self.line_build:                                                 #allow build if other scripts also allow it.
                return connection.on_line_build_attempt(self, points)
            else:                                                                  #Deny build
                return False

    return protocol, fbpatchConnection
