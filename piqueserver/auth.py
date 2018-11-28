from typing import Tuple
import abc
from piqueserver.config import config

Details = Tuple[str, str]  # username, password


class AuthError(Exception):
    pass


class BaseAuthBackend(abc.ABC):
    @abc.abstractmethod
    def login(self, details: Details) -> str:
        """Verifies details and returns an user_role. 
        Raises AuthError if details are incorrect."""
        pass

    @abc.abstractmethod
    def has_permision(self, connection, action: str) -> bool:
        """Checks if a player has permission to perfom specific action."""
        pass


class ConfigAuthBackend(BaseAuthBackend):
    """Auth backend that uses the [passwords] section of the connfig for
    authentication"""

    def __init__(self):
        self.passwords = config.option('passwords', default={})

    def login(self, details: Details) -> str:
        _, password = details
        for user_type, passwords in self.passwords.get().items():
            if password in passwords:
                return user_type
        raise AuthError

    def has_permision(self, connection, action: str) -> bool:
        return connection.admin or action in connection.rights


auth = ConfigAuthBackend()
