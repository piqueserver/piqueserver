# bugfix.py 1411328459
def apply_script(protocol, connection, config):
    class BugFixConnection(connection):
        def on_login(self, name):
            # prevent invisible client, fix by topo
            if len(name) > 15:
                self.kick(silent=True)
            return connection.on_login(self, name)
        def on_line_build_attempt(self, points):
            # prevent "unlimited tower" crash, fix by Danko
            value = connection.on_line_build_attempt(self, points)
            if value is False:
                return value
            for point in points:
                x,y,z = point
                if x < 0 or x > 511 or y < 0 or y > 511 or z < 0 or z > 61:
                    return False
            return value
    return protocol, BugFixConnection
