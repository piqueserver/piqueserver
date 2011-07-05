import world
import pyglet

new_world = world.World()
nade = new_world.create_object(world.Grenade)

def update(dt):
    print 'update -> %s' % (1 / dt)

pyglet.clock.schedule_interval(update, 1 / 60.0)
pyglet.app.run()