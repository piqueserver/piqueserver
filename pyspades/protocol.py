# Copyright (c) Mathias Kaerlev 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from pyspades.bytes import ByteReader, ByteWriter
from pyspades.packet import Packet, load_server_packet, generate_loader_data
from pyspades.loaders import Ack
from twisted.internet.defer import Deferred
from pyspades.loaders import *
from twisted.internet.task import LoopingCall

import time

def timer():
    return int(time.time() * 1000)

class Timer(object):
    offset = None
    latency = None
    def __init__(self, offset = 0):
        self.set_current(offset)
    
    def get_value(self):
        return int((self.offset + timer() - self.current) & 0xFFFF)
    
    def set_current(self, value):
        self.offset = value
        self.current = timer()

class PacketHandler(object):
    other_sequence = None
    sequence = 0
    pending = None
    callback = None
    def __init__(self, connection):
        self.pending = {}
        self.connection = connection
    
    def loader_received(self, loader):
        if self.other_sequence is None:
            self.other_sequence = loader.sequence - 1
        connection = self.connection
        sequence = loader.sequence
        self.pending[sequence] = loader
        self.receive()
    
    def receive(self):
        if not self.pending:
            return
        connection = self.connection
        while 1:
            try:
                next_sequence = (self.other_sequence + 1) & 0xFFFF
                loader = self.pending.pop(next_sequence)
                self.other_sequence = next_sequence
                connection.loader_received(loader)
            except KeyError:
                break
    
    def get_sequence(self, ack):
        if ack:
            self.sequence = (self.sequence + 1) & 0xFFFF
        return self.sequence

ack_packet = Ack()
ping = Ping()
in_packet = Packet()
out_packet = Packet()
sized_sequence = SizedSequenceData()
sized_data = SizedData()

class BaseConnection(object):
    unique = None
    send_id = True
    connection_id = None
    
    in_packet = None
    out_packet = None
    
    timer = None
    other_timer = None
    
    packet_handlers = None
    packet_deferreds = None
    
    disconnected = False
    
    latency = None
    resend_interval = 0.5
    ping_loop = None
    ping_time = None
    ping_interval = 5
    ping_call = None
    ping_defer = None
    timeout = 10
    
    def __init__(self):
        self.packet_handler1 = PacketHandler(self)
        self.packet_handler2 = PacketHandler(self)
        self.timer = Timer(0)
        self.packets = {}
        self.packet_deferreds = {}
        ping_loop = LoopingCall(self.ping)
        ping_loop.start(self.ping_interval, False)
        self.ping_loop = ping_loop
    
    def data_received(self, data):
        reader = ByteReader(data)
        in_packet.read(data)
        if in_packet.timer is not None:
            if self.other_timer is None:
                self.other_timer = Timer(in_packet.timer)
            else:
                self.other_timer.set_current(in_packet.timer)
        # print in_packet.timer,
        for loader in in_packet.items:
            if self.disconnected:
                return
            if loader.ack:
                self.get_packet_handler(loader.byte).loader_received(loader)
            else:
                self.loader_received(loader)
            if self.connection_id is not None:
                if loader.ack and loader.id:
                    ack_packet.timer = in_packet.timer
                    ack_packet.sequence2 = loader.sequence
                    self.send_loader(ack_packet, False, loader.byte)
                elif loader.id == Ack.id:
                    self.ack_received(loader)
        if self.disconnected:
            return
    
    def disconnect(self):
        if self.disconnected:
            return
        self.disconnected = True
        if self.ping_loop is not None and self.ping_loop.running:
            self.ping_loop.stop()
        if self.ping_call is not None:
            self.ping_call.cancel()
            self.ping_call = None
        for _, call in self.packet_deferreds.values():
            call.cancel()
        self.packet_deferreds = {}
    
    def loader_received(self, loader):
        raise NotImplementedError('loader_received() not implemented')
    
    def send_data(self, data):
        raise NotImplementedError('send_data() not implemented')

    def ack_received(self, loader):
        sequence = loader.sequence2
        timer = loader.timer
        byte = loader.byte
        try:
            defer, call = self.packet_deferreds.pop((sequence, byte))
            defer.callback(loader)
            call.cancel()
        except KeyError:
            return
    
    def resend(self, key, loader, resend_interval):
        defer, _ = self.packet_deferreds.pop(key)
        timer = self.timer.get_value()
        out_packet.unique = self.unique
        if self.send_id:
            out_packet.connection_id = self.connection_id
        else:
            out_packet.connection_id = 0
        out_packet.timer = timer
        out_packet.data = loader
        self.send_data(str(out_packet.generate()))
        call = reactor.callLater(resend_interval, self.resend, key, loader, 
            resend_interval)
        self.packet_deferreds[key] = (defer, call)

    def send_loader(self, loader, ack = False, byte = 0, resend_interval = None):
        if self.disconnected:
            return
        if resend_interval is None:
            resend_interval = self.resend_interval
        sequence = self.get_packet_handler(byte).get_sequence(ack)
        timer = self.timer.get_value()
        loader.byte = byte
        loader.sequence = sequence
        loader.ack = ack
        loader = generate_loader_data(loader)
        out_packet.unique = self.unique
        if self.send_id:
            out_packet.connection_id = self.connection_id
        else:
            out_packet.connection_id = 0
        out_packet.timer = timer
        out_packet.data = loader
        self.send_data(str(out_packet.generate()))
        if ack:
            defer = Deferred()
            key = (sequence, byte)
            call = reactor.callLater(resend_interval, self.resend, key, loader, 
                resend_interval)
            self.packet_deferreds[key] = (defer, call)
            return defer
    
    def get_packet_handler(self, byte):
        if byte == 0:
            return self.packet_handler1
        elif byte == 0xFF:
            return self.packet_handler2
        else:
            raise NotImplementedError('invalid byte')
            
    def ping(self, timeout = None):
        if self.ping_call is not None:
            return self.ping_defer
        if timeout is None:
            timeout = self.timeout
        self.ping_call = reactor.callLater(timeout, self.timed_out)
        self.ping_time = reactor.seconds()
        self.ping_defer = self.send_loader(ping, True, 0xFF).addCallback(
            self.got_ping)
        return self.ping_defer
        
    def got_ping(self, ack):
        if self.ping_call is not None:
            self.ping_call.cancel()
            self.latency = reactor.seconds() - self.ping_time
            self.other_timer.set_latency(self.latency)
            self.ping_call = None
    
    def timed_out(self):
        self.ping_call = None
        self.disconnect()
    
    def send_contained(self, contained, sequence = None):
        if sequence is not None:
            loader = sized_sequence
            loader.sequence2 = sequence
        else:
            loader = sized_data
        data = ByteWriter()
        contained.write(data)
        loader.data = data
        return self.send_loader(loader, sequence is None)