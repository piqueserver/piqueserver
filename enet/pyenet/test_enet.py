import unittest
import enet

class TestAddress(unittest.TestCase):
    def test_host(self):
        self.assertEquals(enet.Address("127.0.0.1", 9999).host, "127.0.0.1")
        self.assertEquals(enet.Address("localhost", 9999).host, "127.0.0.1")
        self.assertEquals(enet.Address(None, 9999).host, "*")
        self.assertRaises(IOError, enet.Address, "foo.bar.baz.999", 9999)

    def test_port(self):
        self.assertEquals(enet.Address("127.0.0.1", 9999).port, 9999)
        self.assertRaises(TypeError, enet.Address, "127.0.0.1", "foo")

    def test_hostname(self):
        import socket
        self.assertEquals(enet.Address(socket.gethostname(), 9999).hostname, socket.gethostname())
        self.assertEquals(enet.Address(None, 9999).hostname, "*")

    def test_str(self):
        self.assertEquals(enet.Address("127.0.0.1", 9999).__str__(), "127.0.0.1:9999")

    def test_richcmp(self):
        self.assertTrue(enet.Address("127.0.0.1", 9999) == enet.Address("127.0.0.1", 9999))
        self.assertTrue(enet.Address("127.0.0.1", 9999) != enet.Address("127.0.0.1", 8888))
        self.assertFalse(enet.Address("127.1.1.1", 1992) == enet.Address("127.0.0.1", 9999))

class TestPacket(unittest.TestCase):
    def test_data(self):
        self.assertEquals(enet.Packet(b"foo\0bar").data, b"foo\0bar")
        self.assertRaises(MemoryError, getattr, enet.Packet(), "data")

    def test_dataLength(self):
        self.assertEquals(enet.Packet(b"foobar").dataLength, 6)
        self.assertEquals(enet.Packet(b"foo\0bar").dataLength, 7)
        self.assertRaises(MemoryError, getattr, enet.Packet(), "dataLength")

    def test_flags(self):
        self.assertEquals(enet.Packet(b"foobar").flags, 0)
        self.assertEquals(enet.Packet(b"foobar", enet.PACKET_FLAG_UNSEQUENCED).flags, enet.PACKET_FLAG_UNSEQUENCED)
        self.assertRaises(MemoryError, getattr, enet.Packet(), "flags")

class TestHost(unittest.TestCase):
    def setUp(self):
        self.client = enet.Host(None, 1, 0, 0, 0)
        self.server = enet.Host(enet.Address("localhost", 54301), 1, 0, 0, 0)
        self.peer = self.client.connect(enet.Address("localhost", 54301), 1)
        self.assertEquals(self.peer.state, enet.PEER_STATE_CONNECTING)

    def tearDown(self):
        del self.client
        del self.server
        del self.peer

    def test_connect(self):
        client_connected = False
        server_connected = False

        counter = 0
        while counter < 100 or not (client_connected and server_connected):
            event = self.client.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)
                client_connected = True
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)
                server_connected = True
            counter += 1

        self.assertEquals(client_connected, True)
        self.assertEquals(server_connected, True)

    def test_broadcast(self):
        broadcast_done = False
        broadcast_msg = b"foo\0bar\n baz!"

        while not broadcast_done:
            event = self.client.service(0)
            if event.type == enet.EVENT_TYPE_RECEIVE:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)
                self.assertEquals(event.packet.data, broadcast_msg)
                broadcast_done = True
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)
                self.server.broadcast(0, enet.Packet(broadcast_msg))

class TestPeer(unittest.TestCase):
    def setUp(self):
        self.client = enet.Host(None, 1, 0, 0, 0)
        self.server = enet.Host(enet.Address("localhost", 54301), 1, 0, 0, 0)
        self.peer = self.client.connect(enet.Address("localhost", 54301), 1)
        self.assertEquals(self.peer.state, enet.PEER_STATE_CONNECTING)
        self.assertTrue(self.peer == self.peer)
        self.assertFalse(self.peer != self.peer)

    def tearDown(self):
        del self.client
        del self.server
        del self.peer

    def test_access(self):
        self.assertRaises(MemoryError, enet.Peer().reset)

    def test_send(self):
        msg = b"foo\0bar"
        msg_received = False

        while not msg_received:
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_RECEIVE:
                msg_received = True
                self.assertEquals(event.packet.data, msg)

            event = self.client.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                packet = enet.Packet(msg)
                self.assertEquals(packet.sent, False)
                ret = self.peer.send(0, packet)
                self.assertEquals(ret, 0)
                self.assertEquals(packet.sent, True)

    def test_reset(self):
        reset_done = False
        while not reset_done:
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)
                event.peer.reset()
                self.assertEquals(event.peer.state, enet.PEER_STATE_DISCONNECTED)
                reset_done = True
            event = self.client.service(0)

    def test_disconnect(self):
        connected = True
        while connected:
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_DISCONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_DISCONNECTED)
                connected = False
            elif event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(self.peer.state, enet.PEER_STATE_CONNECTED)
                self.peer.disconnect()
                self.assertEquals(self.peer.state, enet.PEER_STATE_DISCONNECTING)

            event = self.client.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)

    def test_disconnect_later(self):
        connected = True
        while connected:
            event = self.server.service(0)
            if event.type == enet.EVENT_TYPE_DISCONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_DISCONNECTED)
                connected = False
            elif event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(self.peer.state, enet.PEER_STATE_CONNECTED)
                self.peer.disconnect_later()
                self.assertEquals(self.peer.state, enet.PEER_STATE_DISCONNECT_LATER)

            event = self.client.service(0)
            if event.type == enet.EVENT_TYPE_CONNECT:
                self.assertEquals(event.peer.state, enet.PEER_STATE_CONNECTED)

if __name__ == '__main__':
    unittest.main()
