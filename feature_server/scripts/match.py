def apply_script(protocol, connection, config):
    class MatchConnection(connection):
        def on_flag_take(self):
            self.protocol.irc_say("%s took %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_take(self)
        
        def on_flag_drop(self):
            self.protocol.irc_say("%s dropped %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_drop(self)
                
        def on_flag_capture(self):
            self.protocol.irc_say("%s captured %s's flag!" %
                (self.printable_name, self.team.other.name.lower()))
            return connection.on_flag_capture(self)
        
        def on_kill(self, killer):
            self.protocol.irc_say("%s was killed by %s!" %
                (self.printable_name, killer.printable_name))
            return connection.on_kill(self, killer)
        
    return protocol, MatchConnection