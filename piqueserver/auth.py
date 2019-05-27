import abc
from typing import Tuple


class BaseAuthBackend(abc.ABC):
    @abc.abstractmethod
    def login(self, details: Tuple):
        pass

class ConfigAuthBackend(BaseAuthBackend):
    """Auth backend that uses the [passwords] section of the connfig for
    authentication"""
    def login(self, username):
        pass
