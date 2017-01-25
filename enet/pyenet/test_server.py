import enet

SHUTDOWN_MSG = "SHUTDOWN"

host = enet.Host(enet.Address(b"localhost", 54301), 10, 0, 0, 0)

connect_count = 0
run = True
shutdown_recv = False
while run:
    # Wait 1 second for an event
    event = host.service(1000)
    if event.type == enet.EVENT_TYPE_CONNECT:
        print("%s: CONNECT" % event.peer.address)
        connect_count += 1
    elif event.type == enet.EVENT_TYPE_DISCONNECT:
        print("%s: DISCONNECT" % event.peer.address)
        connect_count -= 1
        if connect_count <= 0 and shutdown_recv:
            run = False
    elif event.type == enet.EVENT_TYPE_RECEIVE:
        print("%s: IN:  %r" % (event.peer.address, event.packet.data))
        msg = event.packet.data
        if event.peer.send(0, enet.Packet(msg)) < 0:
            print("%s: Error sending echo packet!" % event.peer.address)
        else:
            print("%s: OUT: %r" % (event.peer.address, msg))
        if event.packet.data == b"SHUTDOWN":
            shutdown_recv = True

# Part of the test to do with intercept callback and socket.send

connect_count = 0
run = True
shutdown_recv = False

def receive_callback(address, data):
    if data and data == b"\xff\xff\xff\xffgetstatus\x00":
        host.socket.send(address, b"\xff\xff\xff\xffstatusResponse\n")

host.intercept = receive_callback

while run:
    # Wait 1 second for an event
    event = host.service(1000)
    if event.type == enet.EVENT_TYPE_CONNECT:
        print("%s: CONNECT" % event.peer.address)
        connect_count += 1
    elif event.type == enet.EVENT_TYPE_DISCONNECT:
        print("%s: DISCONNECT" % event.peer.address)
        connect_count -= 1
        if connect_count <= 0 and shutdown_recv:
            run = False
    elif event.type == enet.EVENT_TYPE_RECEIVE:
        print("%s: IN:  %r" % (event.peer.address, event.packet.data))

        # This packet echo is used to mimick the usual use case when packets are going back&forth while the intercept callback is used
        msg = event.packet.data
        if event.peer.send(0, enet.Packet(msg)) < 0:
            print("%s: Error sending echo packet!" % event.peer.address)
        else:
            print("%s: OUT: %r" % (event.peer.address, msg))
        if event.packet.data == b"SHUTDOWN":
            shutdown_recv = True
