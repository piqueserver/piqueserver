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
        if event.packet.data == "SHUTDOWN":
            shutdown_recv = True
