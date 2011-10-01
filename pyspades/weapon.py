import math
from twisted.internet import reactor
from pyspades.constants import *

class BaseWeapon(object):
    shoot = False
    reloading = False
    id = None
    shoot_time = None
    next_shot = None
    
    def __init__(self, reload_callback):
        self.reload_callback = reload_callback
        self.reset()
    
    def reset(self):
        self.shoot = False
        if self.reloading:
            self.reload_callback.cancel()
            self.reloading = False
        self.current_ammo = self.ammo
        self.current_stock = self.stock
    
    def set_shoot(self, value):
        if value == self.shoot:
            return
        current_time = reactor.seconds()
        if value:
            if not self.current_ammo:
                return
            elif self.reloading and not self.slow_reload:
                return
            self.shoot_time = max(current_time, self.next_shot)
            if self.reloading:
                self.reloading = False
                self.reload_call.cancel()
        else:
            ammo = self.current_ammo
            self.current_ammo = self.get_ammo()
            self.next_shot = self.shoot_time + self.delay * (
                ammo - self.current_ammo)
        self.shoot = value
    
    def reload(self):
        if self.reloading:
            return
        ammo = self.get_ammo()
        if not self.current_stock or ammo >= self.ammo:
            return
        elif self.slow_reload and self.shoot and ammo:
            return
        self.reloading = True
        self.set_shoot(False)
        self.reload_call = reactor.callLater(self.reload_time, self.on_reload)
    
    def on_reload(self):
        self.reloading = False
        if self.slow_reload:
            self.current_ammo += 1
            self.current_stock -= 1
            self.reload_callback()
            self.reload()
        else:
            new_stock = max(0, self.current_stock - (
                self.ammo - self.current_ammo))
            self.current_ammo += self.current_stock - new_stock
            self.current_stock = new_stock
            self.reload_callback()
    
    def get_ammo(self):
        if self.shoot:
            dt = reactor.seconds() - self.shoot_time
            ammo = self.current_ammo - max(0, int(math.ceil(dt / self.delay)))
        else:
            ammo = self.current_ammo
        return max(0, ammo)
    
    def is_empty(self):
        return self.get_ammo() == 0

class Rifle(BaseWeapon):
    name = 'Rifle'
    delay = 0.5
    ammo = 10
    stock = 50
    reload_time = 2.5
    slow_reload = False
    
    damage = {
        0 : 49,
        1 : 100,
        2 : 33,
        3 : 33
    }

class SMG(BaseWeapon):
    name = 'SMG'
    delay = 0.1
    ammo = 30
    stock = 120
    reload_time = 2.5
    slow_reload = False
    
    damage = {
        0 : 24,
        1 : 75,
        2 : 16,
        3 : 16
    }

class Shotgun(BaseWeapon):
    name = 'Shotgun'
    delay = 1.0
    ammo = 6
    stock = 48
    reload_time = 0.5
    slow_reload = True
    
    damage = {
        0 : 19,
        1 : 33,
        2 : 14,
        3 : 14
    }

WEAPONS = {
    SEMI_WEAPON : Rifle,
    SMG_WEAPON : SMG,
    SHOTGUN_WEAPON : Shotgun
}

for id, weapon in WEAPONS.iteritems():
    weapon.id = id