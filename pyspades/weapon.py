from abc import ABCMeta, abstractmethod
import math
from typing import Callable, Dict
from twisted.internet import reactor
from pyspades.constants import (RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON,
                                HEAD, TORSO, ARMS, LEGS, CLIP_TOLERANCE)


class BaseWeapon(object, metaclass=ABCMeta):
    """
    Base class for all weapons for all game versions.
    """
    shoot = False
    reloading = False
    id = None  # type: int
    shoot_time = None
    next_shot = 0
    start = None

    # Weapon parameters
    # Total number of rounds
    stock = None  # type: int
    # Number of rounds that fit in the weapon at once
    ammo = None  # type: int
    # If the weapon should be reloaded one round at a time like the shotgun
    slow_reload = False
    # Time between shots
    delay = 0.0
    # Time between reloading and being able to shoot again
    reload_time = 0.0
    # Dict of damages
    damage = None  # type: Dict[int, int]

    def __init__(self, reload_callback: Callable) -> None:
        self.reload_callback = reload_callback
        self.reset()

    def restock(self) -> None:
        self.current_stock = self.stock

    def reset(self) -> None:
        self.shoot = False
        if self.reloading:
            self.reload_call.cancel()
            self.reloading = False
        self.current_ammo = self.ammo
        self.current_stock = self.stock

    def set_shoot(self, value: bool) -> None:
        if value == self.shoot:
            return
        current_time = reactor.seconds()
        if value:
            self.start = current_time
            if self.current_ammo <= 0:
                return
            elif self.reloading and not self.slow_reload:
                return
            self.shoot_time = max(current_time, self.next_shot)
            if self.reloading:
                self.reloading = False
                self.reload_call.cancel()
        else:
            ammo = self.current_ammo
            self.current_ammo = self.get_ammo(True)
            self.next_shot = self.shoot_time + self.delay * (
                ammo - self.current_ammo)
        self.shoot = value

    def reload(self) -> None:
        if self.reloading:
            return
        ammo = self.get_ammo()
        if not self.current_stock or ammo >= self.ammo:
            return
        elif self.slow_reload and self.shoot and ammo:
            return
        self.reloading = True
        self.set_shoot(False)
        self.current_ammo = ammo
        self.reload_call = reactor.callLater(self.reload_time, self.on_reload)

    def on_reload(self) -> None:
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

    def get_ammo(self, no_max: bool = False) -> int:
        if self.shoot:
            dt = reactor.seconds() - self.shoot_time
            ammo = self.current_ammo - max(0, int(
                math.ceil(dt / self.delay)))
        else:
            ammo = self.current_ammo
        if no_max:
            return ammo
        return max(0, ammo)

    def is_empty(self, tolerance=CLIP_TOLERANCE) -> bool:
        return self.get_ammo(True) < -tolerance or not self.shoot

    @abstractmethod
    def get_damage(self, value, position1, position2) -> int:
        raise NotImplementedError()


class BaseWeapon075(BaseWeapon):
    """
    Base class for all weapons for AoS 0.75.
    """
    def get_damage(self, value, position1, position2) -> int:
        return self.damage[value]


class BaseWeapon076(BaseWeapon):
    """
    Base class for all weapons for AoS 0.76.
    """
    def get_damage(self, value, position1, position2) -> int:
        falloff = 1 - ((pyspades.collision.distance_3d_vector(position1, position2)**1.5)*0.0004)
        return math.ceil(self.damage[value] * falloff)


class Rifle075(BaseWeapon075):
    """
    Weapon definition: AoS 0.75 rifle.
    """
    id = RIFLE_WEAPON
    name = 'Rifle'
    delay = 0.5
    ammo = 10
    stock = 50
    reload_time = 2.5
    slow_reload = False

    damage = {
        TORSO: 49,
        HEAD: 100,
        ARMS: 33,
        LEGS: 33
    }


class SMG075(BaseWeapon075):
    """
    Weapon definition: AoS 0.75 SMG.
    """
    id = SMG_WEAPON
    name = 'SMG'
    delay = 0.11  # actually 0.1, but due to AoS scheduling, it's usually 0.11
    ammo = 30
    stock = 120
    reload_time = 2.5
    slow_reload = False

    damage = {
        TORSO: 29,
        HEAD: 75,
        ARMS: 18,
        LEGS: 18
    }


class Shotgun075(BaseWeapon075):
    """
    Weapon definition: AoS 0.75 shotgun.
    """
    id = SHOTGUN_WEAPON
    name = 'Shotgun'
    delay = 1.0
    ammo = 6
    stock = 48
    reload_time = 0.5
    slow_reload = True

    damage = {
        TORSO: 27,
        HEAD: 37,
        ARMS: 16,
        LEGS: 16
    }


class Rifle076(BaseWeapon076):
    """
    Weapon definition: AoS 0.76 rifle.
    """
    id = RIFLE_WEAPON
    name = 'Rifle'
    delay = 0.6
    ammo = 8
    stock = 48
    reload_time = 2.5
    slow_reload = False

    damage = {
        TORSO: 60,
        HEAD: 250,
        ARMS: 50,
        LEGS: 50
    }


class SMG076(BaseWeapon076):
    """
    Weapon definition: AoS 0.76 SMG.
    """
    id = SMG_WEAPON
    name = 'SMG'
    delay = 0.11  # actually 0.1, but due to AoS scheduling, it's usually 0.11
    ammo = 30
    stock = 150
    reload_time = 2.5
    slow_reload = False

    damage = {
        TORSO: 40,
        HEAD: 60,
        ARMS: 20,
        LEGS: 20
    }


class Shotgun076(BaseWeapon076):
    """
    Weapon definition: AoS 0.76 shotgun.
    """
    id = SHOTGUN_WEAPON
    name = 'Shotgun'
    delay = 0.8
    ammo = 8
    stock = 48
    reload_time = 0.4
    slow_reload = True

    damage = {
        TORSO: 40,
        HEAD: 60,
        ARMS: 20,
        LEGS: 20
    }


# 0.75 weapon set
WEAPONS_075 = {
    RIFLE_WEAPON: Rifle075,
    SMG_WEAPON: SMG075,
    SHOTGUN_WEAPON: Shotgun075,
}

# 0.76 weapon set
WEAPONS_076 = {
    RIFLE_WEAPON: Rifle076,
    SMG_WEAPON: SMG076,
    SHOTGUN_WEAPON: Shotgun076,
}


# Currently used weapon set
def get_weapon_class_by_id(weapon_id: int) -> BaseWeapon:
    return WEAPONS_075[weapon_id]
