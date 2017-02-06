"""
nosharp.py - kicks player whose name starts with # and also kicks player with no name
by kmsi(kmsiapps@gmail.com)
version 2(2017.01.22)
 - Added options to turn on/off
 - Now puts player on spectator team instead of kicking
"""
def apply_script(protocol,connection,config):
    class noSharpConnection(connection):
        def on_spawn(self, pos):
        
            block_noname = True
            block_sharpname = True
            #Edit here to change options
        
            if len(self.name)==0:
                if block_noname:
                    self.set_team(self.protocol.spectator_team)
                    self.send_chat('N% Your name is empty. Please change your name.')
            elif block_sharpname and self.name[0]=='#':
                    self.set_team(self.protocol.spectator_team)
                    self.send_chat('N% Your name starts with #. Please change your name.')
                    
            return connection.on_spawn(self, pos)
    return protocol,noSharpConnection
