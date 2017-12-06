from six import text_type
from datetime import datetime, timedelta
from ipaddress import ip_network, ip_address


def is_expired(ban):
    return datetime.utcnow() > ban['expiry']


class BanManager(object):
    def __init__(self):
        self.bans = []

    def ban(self, ip, duration, reason, name=None):
        ban = {
            'network': ip_network(text_type(ip), strict=False),
            'duration': duration,
            'expiry': datetime.utcnow() + timedelta(minutes=duration),
            'reason': reason,
            'name': name,
            'source': 'local'
        }
        self.bans.append(ban)

    def unban(self, ip):
        player_ip = ip_address(text_type(ip))
        self.bans = [
            ban for ban in self.bans if player_ip not in ban['network']]

    def freeup_bans(self):
        self.bans = [ban for ban in self.bans if not is_expired(ban)]

    def undo_ban(self):
        self.bans.pop()

    def is_banned(self, ip):
        player_ip = ip_address(text_type(ip))
        for ban in self.bans:
            if player_ip in ban['network'] and not is_expired(ban):
                return True
        return False

    def save_to_file(self, path):
        pass

    def load_from_file(self, path):
        pass
