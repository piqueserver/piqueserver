import enet
import random
import sys

try:
    random.seed(sys.argv[1])
except IndexError:
    pass

SHUTDOWN_MSG = b"SHUTDOWN"
MSG_NUMBER = 10

host = enet.Host(None, 1, 0, 0, 0)
peer = host.connect(enet.Address(b"localhost", 54301), 1)

counter = 0
run = True
while run:
    event = host.service(1000)
    if event.type == enet.EVENT_TYPE_CONNECT:
        print("%s: CONNECT" % event.peer.address)
    elif event.type == enet.EVENT_TYPE_DISCONNECT:
        print("%s: DISCONNECT" % event.peer.address)
        run = False
        continue
    elif event.type == enet.EVENT_TYPE_RECEIVE:
        print("%s: IN:  %r" % (event.peer.address, event.packet.data))
        continue
    msg = bytes(bytearray([random.randint(0,255) for i in range(40)]))
    packet = enet.Packet(msg)
    peer.send(0, packet)

    counter += 1
    if counter >= MSG_NUMBER:
        msg = SHUTDOWN_MSG
        peer.send(0, enet.Packet(msg))
        host.service(100)
        peer.disconnect()

    print("%s: OUT: %r" % (peer.address, msg))


# Part of the test to do with intercept callback and socket.send
peer = host.connect(enet.Address(b"localhost", 54301), 1)
shutdown_scheduled = False
run = True

def receive_callback(address, data):
    global shutdown_scheduled

    if shutdown_scheduled:
        return

    if data == b"\xff\xff\xff\xffstatusResponse\n":
        # if the test gets to this point, it means it has passed. Disconnect is a clean up
        shutdown_scheduled = True
    else:
        # error messages are not propagating
        # through cython
        print("data != statusResponse. Instead of expected, got %r" % data)
        assert(False)

while run:
    event = host.service(1000)
    if event.type == enet.EVENT_TYPE_CONNECT:
        print("%s: CONNECT" % event.peer.address)
        msg = bytes(bytearray([random.randint(0,255) for i in range(40)]))
        packet = enet.Packet(msg)
        peer.send(0, packet)

        host.intercept = receive_callback
    elif event.type == enet.EVENT_TYPE_DISCONNECT:
        print("%s: DISCONNECT" % event.peer.address)
        run = False
        continue
    elif event.type == enet.EVENT_TYPE_RECEIVE:
        print("%s: IN:  %r" % (event.peer.address, event.packet.data))
        continue

    if shutdown_scheduled:
        msg = SHUTDOWN_MSG
        peer.send(0, enet.Packet(msg))
        host.service(100)
        peer.disconnect()
        continue

    host.socket.send(peer.address, b"\xff\xff\xff\xffgetstatus\x00")
