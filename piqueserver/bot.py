"""
Bot API for piqueserver.

Provides server-side bots that appear as real players to connected clients.
Physics, block operations, grenades, and multi-bot management are all
handled without touching the network layer.

Public API
----------
FakePeer        — absorbs enet.Peer calls; one instance per bot
BotConnection   — headless ServerConnection (no real network peer)
Bot             — high-level AI controller; subclass and override think()
BotManagerMixin — protocol mixin for automatic per-tick bot management

Minimal example
---------------
    from piqueserver.bot import Bot, BotManagerMixin
    from pyspades.constants import RIFLE_WEAPON

    class MyBot(Bot):
        def think(self, dt):
            enemies = self.get_enemies()
            if enemies:
                target = self.closest(enemies)
                self.look_toward(target)
                if self.can_see(target):
                    self.shoot_at(target)

    def apply_script(protocol, connection, config):
        class P(BotManagerMixin, protocol):
            def on_map_change(self, map_):
                super().on_map_change(map_)
                self.add_bot(MyBot.create(self, 'Bot', self.team_1, RIFLE_WEAPON))
        return P, connection
"""

import math
from typing import List, Optional, Tuple, Union

from pyspades import contained as loaders
from pyspades import world
from pyspades.common import Vertex3
from pyspades.constants import (
    BUILD_BLOCK,
    CHAT_ALL,
    CHAT_TEAM,
    DESTROY_BLOCK,
    GAME_VERSION,
    RIFLE_WEAPON,
    TORSO,
    UPDATE_FREQUENCY,
    WEAPON_KILL,
)
from pyspades.player import ServerConnection


# ---------------------------------------------------------------------------
# FakePeer
# ---------------------------------------------------------------------------

class FakePeer:
    """
    Drop-in replacement for ``enet.Peer`` used by bot connections.

    Each bot receives its own ``FakePeer()`` instance so that
    ``protocol.connections`` has a unique key per bot (Python objects are
    hashable by identity by default).  All network operations are silently
    discarded.
    """

    reliableDataInTransit: int = 0
    roundTripTime: int = 0
    # The version check in on_connect() is skipped for local=True connections,
    # but the correct value is provided here as a safety net.
    eventData: int = GAME_VERSION

    class address:
        host: int = 0
        port: int = 0

    def disconnect(self, data: int = 0) -> None:
        pass

    def send(self, channel: int, packet) -> None:
        pass


# ---------------------------------------------------------------------------
# BotConnection
# ---------------------------------------------------------------------------

class BotConnection(ServerConnection):
    """
    A ``ServerConnection`` with no real network peer.

    Registers in ``protocol.connections`` (keyed by its ``FakePeer``) and in
    ``protocol.players`` (keyed by player ID) exactly like a real player, so
    all existing broadcast and update logic works unchanged.

    Overrides only what must differ for a headless player:

    * ``send_contained()``      — no-op (bot does not receive its own packets)
    * ``loader_received()``     — no-op (no inbound network packets)
    * ``continue_map_transfer`` — no-op (no map transfer)
    * ``disconnect()``          — cleans up without calling ``peer.disconnect()``
    """

    local: bool = True   # bypasses version check, speedhack, and rapid-hack detection
    is_bot: bool = True  # lets scripts identify bots vs real players
    map_data = None      # skips the map-transfer loop in server.update()
    saved_loaders = None # bots never buffer queued packets

    # ------------------------------------------------------------------
    # Silence all outbound / inbound network I/O
    # ------------------------------------------------------------------

    def send_contained(self, contained, sequence: bool = False) -> None:
        pass

    def loader_received(self, loader) -> None:
        pass

    def continue_map_transfer(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Clean disconnect — does not call peer.disconnect()
    # ------------------------------------------------------------------

    def disconnect(self, data: int = 0) -> None:
        if self.disconnected:
            return
        self.disconnected = True
        # Remove from the connections dict (FakePeer is the key)
        self.protocol.connections.pop(self.peer, None)
        # Inherited on_disconnect() handles:
        #   drop_flag()
        #   broadcast PlayerLeft to all clients
        #   del protocol.players[player_id]
        #   protocol.player_ids.put_back(player_id)
        #   reset() → cancel spawn_call, delete world_object, clear team
        self.on_disconnect()


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class Bot:
    """
    High-level bot controller.  Subclass this and override ``think(dt)``.

    Create bots via the class factory ``Bot.create(...)`` — never instantiate
    directly.  The ``think()`` method is called automatically every game tick
    when the bot is registered with a ``BotManagerMixin`` protocol.

    Quick reference
    ---------------
    Positioning     move_to(x, y, z), look_toward(target), set_walk(...)
    Combat          shoot_at(target), throw_grenade(fuse, velocity)
    Building        build_block(x, y, z), destroy_block(x, y, z)
    Communication   chat(message, global_message)
    Queries         can_see(target), distance_to(target),
                    get_enemies(), closest(players)
    Lifecycle       remove()
    """

    connection: BotConnection
    protocol: object  # ServerProtocol at runtime
    _walk_state: Optional[tuple] = None  # last InputData state sent to clients

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        protocol,
        name: str,
        team,
        weapon: int = RIFLE_WEAPON,
        color: Tuple[int, int, int] = (0x70, 0x70, 0x70),
    ) -> 'Bot':
        """
        Spawn a bot and register it with the protocol.

        The bot appears to all connected clients immediately via the
        ``CreatePlayer`` broadcast from ``spawn()``.  Players who join later
        receive an ``ExistingPlayer`` packet automatically through the normal
        ``_send_connection_data()`` path because the bot is registered in
        ``protocol.players``.

        Parameters
        ----------
        protocol:
            The server protocol instance.
        name:
            Desired display name.  Uniqueness is enforced by
            ``protocol.get_name()`` (a suffix is appended if needed).
        team:
            The team the bot joins (e.g. ``protocol.team_1``).
        weapon:
            Weapon constant — ``RIFLE_WEAPON``, ``SMG_WEAPON``, or
            ``SHOTGUN_WEAPON``.
        color:
            Block-placement color as an ``(R, G, B)`` tuple.
        """
        peer = FakePeer()
        # Dynamically build a connection class that combines:
        #   BotConnection  — no-op send_contained / loader_received / disconnect
        #   protocol.connection_class — the fully script-stacked connection class
        #
        # BotConnection comes first in the MRO so its overrides take precedence,
        # but the stacked class's __init__ chain runs (old-style scripts call the
        # wrapped class's __init__ directly), ensuring every script-added attribute
        # (ratio_kills, squad_pref, …) is initialised on the bot instance.
        DynBotConn = type('BotConnection', (BotConnection, protocol.connection_class), {})
        conn = DynBotConn(protocol, peer)
        conn.player_id = protocol.player_ids.pop()
        conn.name = protocol.get_name(name)
        conn.color = color
        conn.set_weapon(weapon, local=True)  # sets weapon_object; no broadcast, no kill
        conn.team = team

        # Register in both protocol dicts before calling spawn()
        protocol.connections[peer] = conn
        protocol.players[conn.player_id] = conn

        # spawn() creates the world_object (world.Character), broadcasts
        # CreatePlayer to all current clients, and fires the on_spawn() hook.
        conn.spawn()

        bot = cls.__new__(cls)
        bot.connection = conn
        bot.protocol = protocol
        bot.__init_bot__()
        return bot

    def __init_bot__(self) -> None:
        """Called after the connection is fully set up.  Override for custom init."""
        self._walk_state = None  # None forces broadcast on first set_walk call

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def remove(self) -> None:
        """
        Cleanly remove the bot from the game.

        Broadcasts ``PlayerLeft`` to all clients, returns the player ID to the
        pool, and deletes the physics object.
        """
        self.connection.disconnect()

    # ------------------------------------------------------------------
    # AI entry point
    # ------------------------------------------------------------------

    def think(self, dt: float = UPDATE_FREQUENCY) -> None:
        """
        Called every game tick (~60 Hz).  Override to implement AI logic.

        ``dt`` is the time step in seconds (default ``UPDATE_FREQUENCY`` ≈
        1/60 s).  The bot's ``world_object`` physics are advanced by the engine
        before ``think()`` is called.
        """
        pass

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    @property
    def position(self) -> Optional[Tuple[float, float, float]]:
        """Current world position as ``(x, y, z)``, or ``None`` if not spawned."""
        wo = self.connection.world_object
        if wo is None:
            return None
        return wo.position.get()

    def move_to(self, x: float, y: float, z: float) -> None:
        """
        Teleport the bot to ``(x, y, z)``.

        The new position is picked up automatically by the 30 Hz
        ``update_network()`` ``WorldUpdate`` broadcast — no extra packet needed.
        For physics-driven movement use ``set_walk()`` instead.
        """
        conn = self.connection
        if conn.world_object is None or not conn.hp:
            return
        conn.world_object.set_position(x, y, z)

    def look_toward(
        self, target: Union[object, Tuple[float, float, float]]
    ) -> None:
        """
        Orient the bot toward ``target``.

        ``target`` may be a player/connection object (with a ``world_object``)
        or a plain ``(x, y, z)`` tuple.

        Orientation is included in the 30 Hz ``WorldUpdate`` broadcast
        automatically — no extra packet needed.
        """
        conn = self.connection
        if conn.world_object is None:
            return
        if hasattr(target, 'world_object') and target.world_object is not None:
            tx, ty, tz = target.world_object.position.get()
        else:
            tx, ty, tz = target
        bx, by, bz = conn.world_object.position.get()
        dx, dy, dz = tx - bx, ty - by, tz - bz
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.001:
            return
        conn.world_object.set_orientation(dx / length, dy / length, dz / length)

    def look_horizontal_toward(
        self, target: Union[object, Tuple[float, float, float]]
    ) -> None:
        """
        Orient the bot toward ``target`` using only the horizontal (XY) plane.

        AoS forward movement adds ``p->f.x`` and ``p->f.y`` to velocity.
        When the bot looks steeply up or down (pitched view), those components
        shrink toward zero and ``mf=True`` produces little horizontal thrust —
        the bot jumps in place.  This method zeroes the Z component so the
        full orientation magnitude is horizontal, giving maximum forward speed.

        Use this when walking toward a target.  Use ``look_toward`` when
        aiming to shoot (where vertical accuracy matters).
        """
        conn = self.connection
        if conn.world_object is None:
            return
        if hasattr(target, 'world_object') and target.world_object is not None:
            tx, ty, _ = target.world_object.position.get()
        else:
            tx, ty, _ = target
        bx, by, _ = conn.world_object.position.get()
        dx, dy = tx - bx, ty - by
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return
        conn.world_object.set_orientation(dx / length, dy / length, 0.0)

    def set_walk(
        self,
        up: bool = False,
        down: bool = False,
        left: bool = False,
        right: bool = False,
        jump: bool = False,
        crouch: bool = False,
        sneak: bool = False,
        sprint: bool = False,
    ) -> None:
        """
        Set the bot's movement and animation state and broadcast it to clients.

        Movement flags (``up``, ``down``, ``left``, ``right``) are fed into the
        C physics engine, which advances the bot's position each tick.
        ``InputData`` is broadcast manually here because walk state is not
        covered by the 30 Hz ``WorldUpdate`` — clients need it to play walk
        animations and update their local prediction.

        Call ``set_walk()`` with no arguments to stop all movement.
        """
        conn = self.connection
        if conn.world_object is None or not conn.hp:
            return
        new_state = (up, down, left, right, jump, crouch, sneak, sprint)
        conn.world_object.set_walk(up, down, left, right)
        conn.world_object.set_animation(jump, crouch, sneak, sprint)

        if new_state == self._walk_state:
            # State unchanged — physics already has the correct flags,
            # no need to re-send InputData to clients.
            return

        # jump is one-shot: the C physics engine clears player.jump after one
        # tick (world_c.cpp move_player), so store the post-consume state so
        # a subsequent set_walk(up=True) call is not suppressed as "no change".
        self._walk_state = (up, down, left, right, False, crouch, sneak, sprint)

        inp = loaders.InputData()
        inp.player_id = conn.player_id
        inp.up = up
        inp.down = down
        inp.left = left
        inp.right = right
        inp.jump = jump
        inp.crouch = crouch
        inp.sneak = sneak
        inp.sprint = sprint
        self.protocol.broadcast_contained(inp, sender=conn)

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------

    def shoot_at(self, target) -> None:
        """
        Deal weapon damage to ``target`` (server-authoritative hit).

        Damage is calculated from the weapon's damage model and applied
        through the normal ``hit()`` path, which handles friendly-fire rules,
        ``on_hit`` hooks, and kill/respawn logic.  No shot packet is sent to
        clients — the damage and any resulting kill packet are broadcast as
        usual.
        """
        conn = self.connection
        if not conn.hp or target.hp is None or target.world_object is None:
            return
        if conn.world_object is None:
            return
        dmg = conn.weapon_object.get_damage(
            TORSO,
            conn.world_object.position,
            target.world_object.position,
        )
        target.hit(dmg, conn, WEAPON_KILL)

    def throw_grenade(
        self,
        fuse: float = 3.0,
        velocity: Tuple[float, float, float] = (0.0, 0.0, -0.5),
    ) -> Optional[world.Grenade]:
        """
        Throw a grenade from the bot's current position.

        Parameters
        ----------
        fuse:
            Time in seconds before the grenade explodes.
        velocity:
            Launch velocity vector in world-space units/tick.

        The ``grenade_exploded`` callback inherited from ``ServerConnection``
        handles damage calculation, block destruction, and the
        ``BlockAction(GRENADE_DESTROY)`` broadcast automatically.

        Returns the ``world.Grenade`` object, or ``None`` if the bot is dead
        or has no grenades remaining.
        """
        conn = self.connection
        if not conn.hp or not conn.grenades or conn.world_object is None:
            return None
        conn.grenades -= 1

        pos = conn.world_object.position.get()
        grenade = self.protocol.world.create_object(
            world.Grenade,
            fuse,
            Vertex3(*pos),
            None,
            Vertex3(*velocity),
            conn.grenade_exploded,  # inherited; handles damage + BlockAction broadcast
        )
        grenade.team = conn.team

        # Broadcast so clients render the grenade arc
        pkt = loaders.GrenadePacket()
        pkt.player_id = conn.player_id
        pkt.value = fuse
        pkt.position = pos
        pkt.velocity = velocity
        self.protocol.broadcast_contained(pkt)
        return grenade

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build_block(self, x: int, y: int, z: int) -> bool:
        """
        Place a block at ``(x, y, z)`` in the bot's current color.

        Returns ``True`` if the block was placed, ``False`` otherwise
        (position already solid, bot is dead, or map rejected the placement).
        """
        conn = self.connection
        if not conn.hp:
            return False
        map_ = self.protocol.map
        if not map_.build_point(x, y, z, conn.color):
            return False
        block_action = loaders.BlockAction()
        block_action.x = x
        block_action.y = y
        block_action.z = z
        block_action.value = BUILD_BLOCK
        block_action.player_id = conn.player_id
        self.protocol.broadcast_contained(block_action, save=True)
        self.protocol.update_entities()
        return True

    def destroy_block(self, x: int, y: int, z: int) -> bool:
        """
        Remove the block at ``(x, y, z)``.

        Returns ``True`` if a block was destroyed, ``False`` otherwise
        (position is air, bot is dead, or map rejected the operation).
        """
        conn = self.connection
        if not conn.hp:
            return False
        map_ = self.protocol.map
        if not map_.get_solid(x, y, z):
            return False
        count = map_.destroy_point(x, y, z)
        if not count:
            return False
        conn.total_blocks_removed += count
        block_action = loaders.BlockAction()
        block_action.x = x
        block_action.y = y
        block_action.z = z
        block_action.value = DESTROY_BLOCK
        block_action.player_id = conn.player_id
        self.protocol.broadcast_contained(block_action, save=True)
        self.protocol.update_entities()
        return True

    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------

    def chat(self, message: str, global_message: bool = True) -> None:
        """
        Send a chat message as this bot.

        ``global_message=True`` sends to all players; ``False`` sends to the
        bot's team only.
        """
        conn = self.connection
        pkt = loaders.ChatMessage()
        pkt.chat_type = CHAT_ALL if global_message else CHAT_TEAM
        pkt.value = message
        pkt.player_id = conn.player_id
        self.protocol.broadcast_contained(pkt)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def can_see(self, target) -> bool:
        """
        ``True`` if this bot has line-of-sight to ``target``.

        Uses the Cython/C++ ``Character.can_see()`` voxel raycast — fast
        enough to call each tick for a small number of targets.
        ``target`` must have a ``world_object`` attribute.
        """
        conn = self.connection
        if conn.world_object is None:
            return False
        if not hasattr(target, 'world_object') or target.world_object is None:
            return False
        p2 = target.world_object.position
        return bool(conn.world_object.can_see(p2.x, p2.y, p2.z))

    def distance_to(
        self, target: Union[object, Tuple[float, float, float]]
    ) -> float:
        """
        Euclidean distance from the bot to ``target``.

        ``target`` may be a player/connection (with ``world_object``) or a
        plain ``(x, y, z)`` tuple.  Returns ``inf`` if the bot has no position.
        """
        p1 = self.position
        if p1 is None:
            return float('inf')
        if hasattr(target, 'world_object') and target.world_object is not None:
            p2 = target.world_object.position.get()
        else:
            p2 = target
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def get_enemies(self) -> list:
        """
        Return all living, non-bot players on the opposing team.

        Excludes: spectators, dead players, players with no ``world_object``,
        and other bots.
        """
        conn = self.connection
        if conn.team is None or conn.team.spectator:
            return []
        return [
            p for p in self.protocol.players.values()
            if not getattr(p, 'is_bot', False)
            and p.team is not conn.team
            and not p.team.spectator
            and p.hp
            and p.world_object is not None
        ]

    def closest(self, players: list):
        """
        Return the player from ``players`` nearest to this bot.

        Raises ``ValueError`` if ``players`` is empty.
        """
        return min(players, key=self.distance_to)


# ---------------------------------------------------------------------------
# BotManagerMixin
# ---------------------------------------------------------------------------

class BotManagerMixin:
    """
    Protocol mixin that provides automatic per-tick bot management.

    Mix this in before the protocol class so ``super()`` chains correctly::

        class MyProtocol(BotManagerMixin, protocol):
            def on_map_change(self, map_):
                super().on_map_change(map_)  # removes old bots
                self.add_bot(MyBot.create(self, 'Bot', self.team_1))

    On every game tick ``on_world_update()`` calls ``bot.think(dt)`` for each
    registered bot.  On map change all bots are removed automatically so
    scripts can re-create them cleanly.

    Multiple bots are fully supported — each ``FakePeer`` instance is unique,
    giving every bot a distinct key in ``protocol.connections``::

        for i in range(4):
            self.add_bot(GuardBot.create(self, f'Guard{i}', self.team_1))
    """

    bots: List[Bot]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bots: List[Bot] = []

    def add_bot(self, bot: Bot) -> Bot:
        """
        Register ``bot`` for automatic ``think()`` calls each tick.

        Returns the bot so callers can write
        ``self.guard = self.add_bot(GuardBot.create(...))``.
        """
        self.bots.append(bot)
        return bot

    def remove_bot(self, bot: Bot) -> None:
        """Unregister and cleanly disconnect ``bot``."""
        try:
            self.bots.remove(bot)
        except ValueError:
            pass
        bot.remove()

    def on_world_update(self) -> None:
        """Tick all registered bots, then call the parent hook."""
        super().on_world_update()
        # Iterate over a snapshot so remove_bot() calls inside think() are safe
        for bot in list(self.bots):
            if not bot.connection.disconnected:
                # When the bot is dead, clear the cached walk state so the
                # first set_walk() after respawn always re-broadcasts InputData
                # to clients (physics resets all flags on spawn).
                if not bot.connection.hp:
                    bot._walk_state = None
                bot.think(UPDATE_FREQUENCY)

    def on_map_change(self, map_) -> None:
        """
        Remove all bots before the map changes so scripts can re-create them.

        Bots are disconnected **before** ``super()`` is called so that
        ``set_map()`` does not find them in ``self.connections`` and attempt
        to call ``reset()`` / ``send_map()`` on them (which would destroy
        their state before we have a chance to clean up properly).
        """
        for bot in list(self.bots):
            bot.remove()
        self.bots.clear()
        super().on_map_change(map_)
