from typing import Tuple, Dict, List
from collections import defaultdict
import abc
from piqueserver.config import config, _Option
login_retries = config.option('login_retries', 3)

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
    def has_permission(self, connection, action: str) -> bool:
        """Checks if a player has permission to perfom specific action."""
        pass

    @abc.abstractmethod
    def get_rights(self, user_type: str) -> List[str]:
        """Returns list of actions an user type can perform"""
        pass

    def set_user_type(self, connection, user_type: str) -> None:
        if user_type == 'admin':
            connection.admin = True
            connection.speedhack_detect = False
        connection.user_types.add(user_type)
        rights = set(self.get_rights(user_type))
        connection.rights.update(rights)


def notify_login(connection, user_type: str) -> None:
    connection.on_user_login(user_type, True)
    message = '{} logged in as ' + user_type
    connection.send_chat(message.format('You'))
    connection.protocol.irc_say(message.format('* ' + connection.name))

_login_retries: Dict[str, int] = defaultdict(login_retries.get)

def retries_left(connection) -> int:
    return _login_retries[connection.address[0]]

def log_failed_attempt(connection):
    _login_retries[connection.address[0]] -= 1

class ConfigAuthBackend(BaseAuthBackend):
    """Auth backend that uses the [passwords] section of the config for
    authentication"""

    def __init__(self):
        self.passwords: _Option = config.option('passwords', default={})
        self.rights: _Option = config.option('rights', default={})

    def login(self, details: Details) -> str:
        _, password = details
        for user_type, passwords in self.passwords.get().items():
            if password in passwords:
                return user_type
        raise AuthError

    def has_permission(self, connection, action: str) -> bool:
        return connection.admin or action in connection.rights

    def get_rights(self, user_type: str) -> List[str]:
        rights = self.rights.get()
        return rights.get(user_type, [])


auth = ConfigAuthBackend()
