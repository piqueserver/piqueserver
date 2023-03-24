"""
Name :recoverhp (Breath to regain hp, like COD)
Reference : medkit.py, smartnade.py
Options
^^^^^^^
.. code-block:: toml
   [recoverhp]
   recoverhp_heal_amount = 1 # how much hp recover a time, depend on on_world_update()
   recoverhp_heal_delay = 5 # delay after hp is lower than 100 recoverhp
.. codeauthor:: tydaytygx
"""

from twisted.internet.reactor import callLater
from piqueserver.config import config
recoverhp_config = config.section("recoverhp")
recoverhp_heal_amount = recoverhp_config.option("recoverhp_heal_amount", 1)
recoverhp_heal_delay = recoverhp_config.option("recoverhp_delay", 5)
def health_regain(player):
    try:
        player.set_hp(player.hp + recoverhp_heal_amount.get())
    except Exception as e:
        print(e)  

def apply_script(protocol, connection, config):
    class RecoverHpProtocol(protocol):
        def on_world_update(self):
            
            for player in list(self.players.values()):
                # print(player.hp)
                if player.hp != 100 and player.hp != None:
                    callLater(recoverhp_heal_delay.get(), health_regain, player)
            return protocol.on_world_update(self)
        
    class RecoverHpConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
    return RecoverHpProtocol, RecoverHpConnection
