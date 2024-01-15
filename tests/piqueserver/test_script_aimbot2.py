import unittest
from time import monotonic
from piqueserver.scripts import aimbot2
from piqueserver.server import FeatureConnection, FeatureProtocol

class TestCopytree(unittest.TestCase):
    """
        Tests for functions in the Aimbot2Connection class.
        Due to the nature of it, most functions cannot be tested easily since
        some functions are called inside another. This will not work since we'd have
        to provide the same connection as argument, as it would otherwise not find self.
    """
    
    def test_get_headshot_snap_count(self):
        connection = FeatureConnection
        protocol = FeatureProtocol
        aimbot2protocol, aimbot2connection = aimbot2.apply_script(protocol, connection, None)
        time_now = monotonic()
        aimbot2connection.headshot_snap_times = [time_now]
        snap_count = aimbot2connection.get_headshot_snap_count(aimbot2connection)

        self.assertEquals(snap_count, 1)

    def test_get_kill_count(self):
        connection = FeatureConnection
        protocol = FeatureProtocol
        aimbot2protocol, aimbot2connection = aimbot2.apply_script(protocol, connection, None)
        time_now = monotonic()
        aimbot2connection.kill_times = [time_now]

        kill_count = aimbot2connection.get_kill_count(aimbot2connection)
        self.assertEqual(kill_count, 1)