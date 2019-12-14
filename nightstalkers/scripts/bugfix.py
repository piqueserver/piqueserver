"""
Derived from bugfix.py 1411328459

Ported to piqueserver by GreaseMonkey in 2019

TODO: Get this specific bugfix into piqueserver itself
"""

from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type

from pyspades.player import ServerConnection
from pyspades.server import ServerProtocol


class BugFixConnectionInterface(ServerConnection, metaclass=ABCMeta):
    pass


def apply_script(protocol: Type[ServerProtocol], connection: Type[ServerConnection], config: Any) -> Tuple[Type[ServerProtocol], Type[ServerConnection]]:
    class BugFixConnection(BugFixConnectionInterface, connection):
        def on_line_build_attempt(self, points: Sequence[Tuple[int, int, int]]) -> Optional[bool]:
            # prevent "unlimited tower" crash, fix by Danko
            value = connection.on_line_build_attempt(self, points) # type: Optional[bool]
            if value is False:
                return value
            for point in points:
                x,y,z = point
                if x < 0 or x > 511 or y < 0 or y > 511 or z < 0 or z > 61:
                    return False
            return value

    return protocol, BugFixConnection

