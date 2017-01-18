"""
Platforms!

Just knowing the names of the four commands should be enough ingame,
as the parameter lists are provided when you try them.

/p /platform [command]
    Starts a new platform or enables you to edit them by specifying a command.
    To build a platform, put down blocks delimiting the size of the floor--
    two blocks in opposite corners is sufficient.

    Press the SNEAK key (V) while in any platform mode to get information
    about the platform you're looking at.  Must be holding spade tool.

    command:
        new <label>
            Starts a new platform with a label already attached.
        name <label>
            Labels a platform.  It's recommended you name things to avoid mistakes.
        height <height>
            Forces the platform to grow or shrink to the specified height.
        freeze
            Freezes or unfreezes a platform.  A frozen platform won't move.
        destroy
            Destroys a platform, removing all its blocks.
        last
            When you get asked to select a platform, you can use this command
            to automatically choose the last platform you selected or created.

/b /button [command]
    Starts button creation. Just build a block with the desired color.

    A default button only has a Press trigger and no actions, so you'll need
    to make it do something with /action.

    Press the SNEAK key (V) while in any button mode to get information
    about the button you're looking at.  Must be holding spade tool.

    command:
        new <label>
            Starts button creation with a label already attached.
        name <label>
            Labels a button.  It's recommended you name things to avoid mistakes.
        toggle
            Disables or enables a button.  A disabled button does nothing.
        cooldown <seconds>
            The button will be able to be activated only once in the specified
            interval. Default is 0.5 seconds.
        destroy
            Destroys a button, removing the block.
        last
            When you get asked to select a button, you can use this command
            to automatically choose the last button you selected or created.

/ac /action <command>
    Makes a button do something.

    command:
        add <action>
        set <action>
            Adds an action to the button. Set deletes all previous actions first,
            making the new action the only one.

            See /trigger for more information on who the "activating players" are.

            action:
                height   <height> [speed=0.25] [delay]
                raise    <amount> [speed=0.25] [delay]
                lower    <amount> [speed=0.25] [delay]
                elevator <height> [speed=0.75] [delay] [wait=3.0]
                    Speed determines how fast the platform moves, in seconds.
                    Delay is the amount of time spent waiting before the platform
                    actually starts to move.
                    Elevators can wait an amount of time at the end of the journey,
                    before heading back.
                output
                teleport <x y z|where>
                    Moves the activating players to the specified coordinates.
                    Using 'where' instead takes the last location where you stood
                    and executed the /where command.
                chat <text>
                    Sends text to the activating players.
                    You can put text between quotation marks to allow right
                    justifying with spaces, for example: "           Hello!"
                damage <amount>
                    Hits the activating players for that many hitpoints.
                    Use negative numbers to heal.
        list
            Lists the actions present in the button you select.

            Example:
            "Actions in 'mybutton': #0 platform 'myplat' height(5) --
                #1 player teleport(16, 16, 32)"

            #0 and #1 are the action indexes to be used with /action del.
            'myplat' is the name of the platform the height action is affecting,
            in this case making it 5 blocks tall.
        del <#|all>
            Delete a single action in a button by specifying its index. Action
            indexes can be looked up by using /action list.

            Negative indexes can be used too: -1 is the last added action, -2 the
            one before that, and so on.

            Specifying 'all' instead of a number erases all the actions.

/t /trigger <command>
    Triggers are what makes a button know when to act and when not to.

    command:
        add [not] <action>
        set [not] <action>
            Adds a trigger to the button. Set deletes all previous triggers first,
            making the new trigger the only one.

            Putting 'not' before the action makes it NEGATE the output.
            If you want to make a button that activates when a player *leaves*
            a zone, you could use "/trigger set not distance 5"

            action:
                press
                    Fires when a player normally hits the button with the spade.
                distance [radius=3]
                    True when a player gets within <radius> blocks of the
                    button (note: box distance, not sphere).
                track [radius=3]
                    Same as distance, but tracks one player and only one player.

                    Useful for creating a button that requires a specific number
                    of nearby players.
                height <height>
                    True when the platform is exactly the specified height.
        list
            Lists the triggers present in the button you select.

            Example:
            "Triggers in 'mybutton': #0 player press OR #1 player distance=5 [CHECK]"

            #0 and #1 are the trigger indexes to be used with /trigger del.
            [CHECK] means the trigger currently yields true. The player in this
            case is near the button, but hasn't pressed it.

            This button uses OR logic, meaning that EITHER of these triggers
            firing is enough to activate the button.
        del <#|all>
            Delete a single trigger in a button by specifying its index. Trigger
            indexes can be looked up by using /trigger list.

            Negative indexes can be used too: -1 is the last added trigger, -2 the
            one before that, and so on.

            Specifying 'all' instead of a number erases all the triggers.
        logic <and|or>
            "AND" will make the button activate when ALL its triggers yield true.
            "OR" will make the button activate when ANY of its triggers fire.
        quiet
            Makes a button either become silent or resume playing animation and
            sound when it activates.

/save
    Saves all platform and button data to mapname_platform.txt
    Use SAVE_ON_MAP_CHANGE and AUTOSAVE_EVERY to avoid having to manually save.

Maintainer: hompy
"""

# TODO
# Platforms 'freeze' when people spam the button
# Shoot trigger or destroy trigger (both?)
# Grenade launching action
# Prevent platforms from being hidden forever
# Negative heights
# Nicer way of having invisible buttons?
# 'invisibility' mode to get in range of annoying distance buttons
# Platforms crushing players
# Stop platform action?

import __builtin__
import json
import os
import operator
from collections import defaultdict
from itertools import product, imap, chain
from twisted.internet.reactor import callLater, seconds
from twisted.internet.task import LoopingCall
from pyspades.world import cube_line
from pyspades.server import block_action, block_line, set_color, position_data
from pyspades.collision import collision_3d
from pyspades.common import make_color
from pyspades.types import MultikeyDict
from pyspades.constants import *
from commands import add, admin, name, alias, join_arguments
from map import DEFAULT_LOAD_DIR

SAVE_ON_MAP_CHANGE = True
AUTOSAVE_EVERY = 0.0 # minutes, 0 = disabled
MAX_DISTANCE = 64.0
MIN_COOLDOWN = 0.1 # seconds

S_SAVED = 'Platforms saved'
S_EXIT_BLOCKING_STATE = "You must first leave {state} mode!"
S_NOT_WORKING = 'This button is disabled'
S_COMMAND_CANCEL = "Aborting {command} command"
S_PLATFORM_USAGE = 'Usage: /platform [{commands}]'
S_PLATFORM_NEW_USAGE = 'Usage: /platform new <label>'
S_PLATFORM_NAME_USAGE = 'Usage: /platform name <label>'
S_PLATFORM_HEIGHT_USAGE = 'Usage: /platform height <height>'
S_PLATFORM_STARTED = 'Platform construction started. Build then type ' \
    '/platform when done'
S_PLATFORM_NOT_FLAT = 'Bad platform. Floor can be incomplete but must be flat'
S_PLATFORM_CREATED = "Platform '{label}' created"
S_PLATFORM_CANCEL = 'Platform construction cancelled'
S_PLATFORM_RENAMED = "Platform '{old_label}' renamed to '{label}'"
S_PLATFORM_DESTROYED = "Platform '{label}' destroyed"
S_SELECT_PLATFORM = 'Select a platform by hitting it with the spade'
S_PLATFORM_SELECTED = "Platform '{label}' selected"
S_PLATFORM_INFO = "Platform '{label}', height {height}"
S_NOT_A_PLATFORM = 'This is not a platform!'
S_FROZEN = "Platform '{label}' frozen"
S_UNFROZEN = "Platform '{label}' unfrozen"
S_BUTTON_USAGE = 'Usage: /button [{commands}]'
S_BUTTON_NEW_USAGE = 'Usage: /button new <label>'
S_BUTTON_NAME_USAGE = 'Usage: /button name <label>'
S_BUTTON_COOLDOWN_USAGE = 'Usage: /button cooldown <seconds>'
S_BUTTON_PLACEMENT = 'Put down a block where you want the new button to be'
S_BUTTON_CREATED = "Button '{label}' created"
S_BUTTON_CANCEL = 'Aborting button placement'
S_BUTTON_OVERLAPS = 'There is already another button here!'
S_BUTTON_RENAMED = "Button '{old_label}' renamed to '{label}'"
S_BUTTON_DESTROYED = "Button '{label}' removed"
S_BUTTON_COOLDOWN = "Cooldown for button '{label}' set to {cooldown:.2f} seconds"
S_SELECT_BUTTON = 'Select a button by hitting it with the spade'
S_BUTTON_SELECTED = "Button '{label}' selected"
S_BUTTON_INFO = "Button '{label}', cooldown {cooldown:.2f}s"
S_DISABLED = "Button '{label}' disabled"
S_ENABLED = "Button '{label}' enabled"
S_SILENT = "Button '{label}' will activate quietly"
S_NOISY = "Button '{label}' will animate when activated"
S_ACTION_USAGE = 'Usage: /action <{commands}>'
S_ACTION_ADD_USAGE = 'Usage: /action add <{actions}>'
S_ACTION_DELETE_USAGE = 'Usage: /action del <#|all>'
S_ACTION_HEIGHT_USAGE = 'Usage: /action add height <height> [speed=0.25] [delay]'
S_ACTION_RAISE_USAGE = 'Usage: /action add raise <amount> [speed=0.25] [delay]'
S_ACTION_LOWER_USAGE = 'Usage: /action add lower <amount> [speed=0.25] [delay]'
S_ACTION_ELEVATOR_USAGE = 'Usage: /action add elevator <height> [speed=0.75] ' \
    '[delay] [wait=3.0]'
S_ACTION_OUTPUT_USAGE = 'Usage: /action add output [delay]'
S_ACTION_TELEPORT_USAGE = 'Usage: /action add teleport <x y z|where>'
S_ACTION_CHAT_USAGE = 'Usage: /action add chat <text>'
S_ACTION_DAMAGE_USAGE = 'Usage: /action add damage <amount>'
S_ACTION_ADDED = "Added {action} action to button '{label}'"
S_ACTION_LIST_EMPTY = "Button '{label}' has no actions"
S_ACTION_LIST_HEADER = "Actions in '{label}': "
S_ACTION_DELETED = "{action} action {number} deleted from button '{label}'"
S_ACTION_DELETED_ALL = "Deleted all actions in button '{label}'"
S_ACTION_INVALID_NUMBER = "Invalid action number! Use '/action list' to check"
S_TRIGGER_USAGE = 'Usage: /trigger <{commands}>'
S_TRIGGER_ADD_USAGE = 'Usage: /trigger add [not] <{triggers}>'
S_TRIGGER_DELETE_USAGE = 'Usage: /trigger del <#|all>'
S_TRIGGER_LOGIC_USAGE = 'Usage: /trigger logic <and|or>'
S_TRIGGER_DISTANCE_USAGE = 'Usage: /trigger add [not] distance [radius=3]'
S_TRIGGER_TRACK_USAGE = 'Usage: /trigger add [not] track [radius=3]'
S_TRIGGER_HEIGHT_USAGE = 'Usage: /trigger add [not] height <height>'
S_TRIGGER_ADDED = "Added {trigger} trigger to button '{label}'"
S_TRIGGER_LIST_EMPTY = "Button '{label}' has no triggers"
S_TRIGGER_LIST_HEADER = "Triggers in '{label}': "
S_TRIGGER_LIST_ITEM_IS_TRUE = ' [CHECK]'
S_TRIGGER_LIST_AND = ' AND '
S_TRIGGER_LIST_OR = ' OR '
S_TRIGGER_LIST_NOT = 'NOT '
S_TRIGGER_DELETED = "{trigger} trigger {number} deleted from button '{label}'"
S_TRIGGER_DELETED_ALL = "Deleted all triggers in button '{label}'"
S_TRIGGER_INVALID_NUMBER = "Invalid trigger number! Use '/trigger list' to check"
S_LOGIC_AND = "Button '{label}' will activate when ALL its triggers yield true"
S_LOGIC_OR = "Button '{label}' will activate when ANY of its triggers fire"
S_TOO_MANY_PARAMETERS = 'ERROR: too many parameters'
S_NOT_ENOUGH_PARAMETERS = 'ERROR: not enough parameters'
S_WRONG_PARAMETER_TYPE = 'ERROR: wrong parameter type'
S_NOT_POSITIVE = 'ERROR: {parameter} must be a positive number'
S_OUT_OF_BOUNDS = 'ERROR: {parameter} must be in the range [0..512)'
S_OUT_OF_BOUNDS_Z = 'ERROR: {parameter} must be in the range [0..62]'
S_WHERE_FIRST = 'ERROR: use /where first to remember your position'
S_MINIMUM = 'ERROR: Minimum {parameter} is {value}'
S_MAXIMUM = 'ERROR: Maximum {parameter} is {value}'
S_NICE_LOCATION = '{:.4g}, {:.4g}, {:.4g}'
PLATFORM_COMMANDS = ('new', 'name', 'height', 'freeze', 'destroy',  'last')
PLATFORM_COMMAND_USAGES = {
    'new' : S_PLATFORM_NEW_USAGE,
    'name' : S_PLATFORM_NAME_USAGE,
    'height' : S_PLATFORM_HEIGHT_USAGE
}
BUTTON_COMMANDS = ('new', 'name', 'destroy', 'toggle', 'cooldown', 'last')
BUTTON_COMMAND_USAGES = {
    'new' : S_BUTTON_NEW_USAGE,
    'name' : S_BUTTON_NAME_USAGE,
    'cooldown' : S_BUTTON_COOLDOWN_USAGE
}
ACTION_COMMANDS = ('add', 'set', 'list', 'del')
ACTION_COMMAND_USAGES = {
    'add' : S_ACTION_ADD_USAGE,
    'del' : S_ACTION_DELETE_USAGE
}
ACTION_ADD_ACTIONS = ('height', 'raise', 'lower', 'elevator', 'output',
    'teleport', 'chat', 'damage')
ACTION_ADD_USAGES = {
    'height' : S_ACTION_HEIGHT_USAGE,
    'raise' : S_ACTION_RAISE_USAGE,
    'lower' : S_ACTION_LOWER_USAGE,
    'elevator' : S_ACTION_ELEVATOR_USAGE,
    'output' : S_ACTION_OUTPUT_USAGE,
    'teleport' : S_ACTION_TELEPORT_USAGE,
    'chat' : S_ACTION_CHAT_USAGE,
    'damage' : S_ACTION_DAMAGE_USAGE,
}
TRIGGER_COMMANDS = ('add', 'set', 'list', 'del', 'logic', 'quiet')
TRIGGER_COMMAND_USAGES = {
    'add' : S_TRIGGER_ADD_USAGE,
    'del' : S_TRIGGER_DELETE_USAGE,
    'logic' : S_TRIGGER_LOGIC_USAGE
}
TRIGGER_ADD_TRIGGERS = ('press', 'distance', 'track', 'height')
TRIGGER_ADD_USAGES = {
    'distance' : S_TRIGGER_DISTANCE_USAGE,
    'track' : S_TRIGGER_TRACK_USAGE,
    'height' : S_TRIGGER_HEIGHT_USAGE,
}

ACTION_RAY_LENGTH = 8.0
ACTION_COOLDOWN = 0.25

def parseargs(signature, args):
    signature = signature.split()
    if len(args) > len(signature):
        raise ValueError(S_TOO_MANY_PARAMETERS)
    result = []
    optional = False
    for i, s in enumerate(signature):
        func_name = s.strip('[]')
        optional = optional or func_name != s
        try:
            typecast = getattr(__builtin__, func_name)
            result.append(typecast(args[i]))
        except ValueError:
            raise ValueError(S_WRONG_PARAMETER_TYPE)
        except IndexError:
            if not optional:
                raise ValueError(S_NOT_ENOUGH_PARAMETERS)
            result.append(None)
    return result

def flatten(iterables):
    return chain.from_iterable(iterables)

@admin
def save(connection):
    connection.protocol.dump_platform_json()
    return S_SAVED

@alias('p')
@name('platform')
@admin
def platform_command(connection, *args):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    state = player.states.top()

    if state:
        state_name = state.get_parent().name
        if state_name in ('new platform', 'platform command') and not args:
            # finish platform construction
            player.states.exit()
            return
        elif state.blocking:
            # can't switch from a blocking mode
            return S_EXIT_BLOCKING_STATE.format(state = state.name)
    if args:
        # enter new mode
        available = '|'.join(PLATFORM_COMMANDS)
        usage = S_PLATFORM_USAGE.format(commands = available)
        try:
            command = args[0]
            if command not in PLATFORM_COMMANDS:
                return usage

            usage = PLATFORM_COMMAND_USAGES.get(command, usage)
            new_state = PlatformCommandState(command)
            if command == 'height':
                new_state.height, = parseargs('int', args[1:])
                if new_state.height < 0:
                    message = S_NOT_POSITIVE.format(parameter = 'height')
                    raise ValueError(message)
            elif command in ('new', 'name'):
                new_state.label = join_arguments(args[1:], '').strip()
                if not new_state.label:
                    return usage
            elif command == 'last' and state:
                if state.name == 'select platform' and player.previous_platform:
                    state.platform = player.previous_platform
                    player.states.pop()
                    return
        except ValueError as err:
            player.send_chat(usage)
            return str(err)
        except IndexError:
            return usage

        player.states.exit()
        if command == 'new':
            # start construction with label
            player.states.enter(NewPlatformState(new_state.label))
        else:
            player.states.push(new_state)
            player.states.enter(SelectPlatformState(new_state))
    else:
        # start construction
        player.states.exit()
        player.states.enter(NewPlatformState())

@alias('b')
@name('button')
@admin
def button_command(connection, *args):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    state = player.states.top()

    if state:
        state_name = state.get_parent().name
        if state_name in ('new button', 'button command') and not args:
            # cancel button creation
            player.states.exit()
            return
        elif state.blocking:
            # can't switch from a blocking mode
            return S_EXIT_BLOCKING_STATE.format(state = state.name)
    if args:
        # enter new mode
        available = '|'.join(BUTTON_COMMANDS)
        usage = S_BUTTON_USAGE.format(commands = available)
        try:
            command = args[0]
            if command not in BUTTON_COMMANDS:
                return usage

            usage = BUTTON_COMMAND_USAGES.get(command, usage)
            new_state = ButtonCommandState(command)
            if command in ('new', 'name'):
                new_state.label = join_arguments(args[1:], '').strip()
                if not new_state.label:
                    return usage
            elif command == 'cooldown':
                new_state.cooldown, = parseargs('float', args[1:])
                if new_state.cooldown < 0.0:
                    message = S_NOT_POSITIVE.format(parameter = 'cooldown')
                    raise ValueError(message)
                if new_state.cooldown < MIN_COOLDOWN:
                    message = S_MINIMUM.format(parameter = 'cooldown',
                        value = MIN_COOLDOWN)
                    raise ValueError(message)
            elif command == 'last' and state:
                if state.name == 'select button' and player.previous_button:
                    state.button = player.previous_button
                    player.states.pop()
                    return
        except ValueError as err:
            player.send_chat(usage)
            return str(err)
        except IndexError:
            return usage

        player.states.exit()
        if command == 'new':
            # start button creation with label
            player.states.enter(NewButtonState(new_state.label))
        else:
            player.states.push(new_state)
            player.states.enter(SelectButtonState(new_state))
    else:
        # start button creation
        player.states.exit()
        player.states.enter(NewButtonState())

@alias('ac')
@name('action')
@admin
def action_command(connection, *args):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    state = player.states.top()

    if state:
        if state.get_parent().name == 'action' and not args:
            # cancel action command
            player.states.exit()
            return
        elif state.blocking:
            # can't switch from a blocking mode
            return S_EXIT_BLOCKING_STATE.format(state = state.name)

    available = '|'.join(ACTION_COMMANDS)
    usage = S_ACTION_USAGE.format(commands = available)
    try:
        command = args[0].lower()
        if command not in ACTION_COMMANDS:
            return usage

        if command in ('add', 'set'):
            add = command == 'add'
            available = '|'.join(ACTION_ADD_ACTIONS)
            usage = S_ACTION_ADD_USAGE.format(actions = available)
            if not add:
                usage = usage.replace('add', 'set')

            action = args[1].lower()
            if action not in ACTION_ADD_ACTIONS:
                return usage

            usage = ACTION_ADD_USAGES.get(action, usage)
            if not add:
                usage = usage.replace('add', 'set')

            new_state = ActionAddState(action, add)
            new_states = [new_state, SelectButtonState(new_state)]
            if action in ('height', 'raise', 'lower', 'elevator'):
                kwargs = {}
                if action == 'elevator':
                    signature = 'int [float float float]'
                    value, speed, delay, wait = parseargs(signature, args[2:])
                    speed = 0.75 if speed is None else speed
                    kwargs['wait'] = 3.0 if wait is None else wait
                else:
                    signature = 'int [float float]'
                    value, speed, delay = parseargs(signature, args[2:])
                    speed = 0.25 if speed is None else speed
                kwargs['mode'] = action
                kwargs['height'] = value
                kwargs['speed'] = speed
                kwargs['delay'] = delay or 0.0
                # validate parameters
                for parameter, value in kwargs.iteritems():
                    if type(value) in (int, float) and value < 0:
                        message = S_NOT_POSITIVE.format(parameter = parameter)
                        raise ValueError(message)
                new_state.kwargs = kwargs
                new_states.append(SelectPlatformState(new_state))
            elif action == 'output':
                delay, = parseargs('[float]', args[2:])
                new_state.kwargs = {
                    'mode' : 'height',
                    'speed' : 0.0,
                    'delay' : delay or 0.0,
                    'force' : True
                }
                new_states.append(SelectPlatformState(new_state))
            elif action == 'teleport':
                if join_arguments(args[2:]) == 'where':
                    if not player.where_location:
                        return S_WHERE_FIRST
                    x, y, z = player.where_location
                    x = round(x * 2.0) / 2.0 - 0.5
                    y = round(y * 2.0) / 2.0 - 0.5
                    z = round(z) + 0.5
                else:
                    x, y, z = parseargs('float float float', args[2:])
                if x <= 0.0 or x > 511.0:
                    raise ValueError(S_OUT_OF_BOUNDS.format(parameter = 'x'))
                if y <= 0.0 or y > 511.0:
                    raise ValueError(S_OUT_OF_BOUNDS.format(parameter = 'y'))
                if z <= 0.0 or z > 62.0:
                    raise ValueError(S_OUT_OF_BOUNDS_Z.format(parameter = 'z'))
                z = max(0.5, z)
                new_state.kwargs = {'location' : (x, y, z)}
            elif action == 'chat':
                text = join_arguments(args[2:])
                if not text:
                    return usage
                new_state.kwargs = {'value' : text}
            elif action == 'damage':
                amount, = parseargs('int', args[2:])
                damage_type = WEAPON_KILL if amount > 0 else FALL_KILL
                new_state.kwargs = {'value' : amount, 'type' : damage_type}
        else:
            usage = ACTION_COMMAND_USAGES.get(command, usage)
            new_state = ActionCommandState(command)
            new_states = [new_state, SelectButtonState(new_state)]
            if command == 'del':
                new_state.number, = parseargs('str', args[1:])
                if new_state.number != 'all':
                    new_state.number, = parseargs('int', args[1:])

        player.states.exit()
        for state in new_states[:-1]:
            player.states.push(state)
        player.states.enter(new_states[-1])
    except ValueError as err:
        player.send_chat(usage)
        return str(err)
    except IndexError:
        return usage

@alias('t')
@name('trigger')
@admin
def trigger_command(connection, *args):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    state = player.states.top()

    if state:
        if state.get_parent().name == 'trigger' and not args:
            # cancel trigger command
            player.states.exit()
            return
        elif state.blocking:
            # can't switch from a blocking mode
            return S_EXIT_BLOCKING_STATE.format(state = state.name)

    available = '|'.join(TRIGGER_COMMANDS)
    usage = S_TRIGGER_USAGE.format(commands = available)
    try:
        command = args[0].lower()
        if command not in TRIGGER_COMMANDS:
            return usage

        if command in ('add', 'set'):
            add = command == 'add'
            available = '|'.join(TRIGGER_ADD_TRIGGERS)
            usage = S_TRIGGER_ADD_USAGE.format(triggers = available)
            if not add:
                usage = usage.replace('add', 'set')

            negate = args[1].lower() == 'not'
            if negate:
                args = args[:1] + args[2:]

            trigger = args[1].lower()
            if trigger not in TRIGGER_ADD_TRIGGERS:
                return usage

            usage = TRIGGER_ADD_USAGES.get(trigger, usage)
            if not add:
                usage = usage.replace('add', 'set')

            new_state = TriggerAddState(trigger, negate, add)
            new_states = [new_state, SelectButtonState(new_state)]
            if trigger in ('distance', 'track'):
                new_state.radius, = parseargs('[float]', args[2:])
                if new_state.radius is None:
                    new_state.radius = 3.0
                if new_state.radius < 0.0:
                    message = S_NOT_POSITIVE.format(parameter = 'radius')
                    raise ValueError(message)
                if new_state.radius > MAX_DISTANCE:
                    message = S_MAXIMUM.format(parameter = 'radius',
                        value = MAX_DISTANCE)
                    raise ValueError(message)
            elif trigger == 'height':
                new_state.height, = parseargs('int', args[2:])
                if new_state.height < 0:
                    message = S_NOT_POSITIVE.format(parameter = 'height')
                    raise ValueError(message)
                new_states.append(SelectPlatformState(new_state))
        else:
            usage = TRIGGER_COMMAND_USAGES.get(command, usage)
            new_state = TriggerCommandState(command)
            new_states = [new_state, SelectButtonState(new_state)]
            if command == 'del':
                new_state.number, = parseargs('str', args[1:])
                if new_state.number != 'all':
                    new_state.number, = parseargs('int', args[1:])
            elif command == 'logic':
                new_state.logic, = parseargs('str', args[1:])
                if new_state.logic not in ('and', 'or'):
                    return usage

        player.states.exit()
        for state in new_states[:-1]:
            player.states.push(state)
        player.states.enter(new_states[-1])
    except ValueError as err:
        player.send_chat(usage)
        return str(err)
    except IndexError:
        return usage

for func in (platform_command, button_command, action_command,
    trigger_command, save):
    add(func)

def aabb(x, y, z, x1, y1, z1, x2, y2, z2):
    return x >= x1 and y >= y1 and z >= z1 and x < x2 and y < y2 and z < z2

def prism(x1, y1, z1, x2, y2, z2):
    return product(xrange(x1, x2), xrange(y1, y2), xrange(z1, z2))

def plane_least_rows(x1, y1, x2, y2, z):
    if y2 - y1 < x2 - x1:
        for y in xrange(y1, y2):
            yield x1, y, z, x2 - 1, y, z
    else:
        for x in xrange(x1, x2):
            yield x, y1, z, x, y2 - 1, z

def send_color(protocol, color):
    set_color.value = make_color(*color)
    set_color.player_id = 32
    protocol.send_contained(set_color, save = True)

def send_block(protocol, x, y, z, value = BUILD_BLOCK):
    block_action.value = value
    block_action.player_id = 32
    block_action.x = x
    block_action.y = y
    block_action.z = z
    protocol.send_contained(block_action, save = True)

class Trigger:
    type = None
    parent = None
    status = False
    unique = False
    negate = False

    def __init__(self, protocol, negate = False):
        self.protocol = protocol
        self.negate = negate

    def unbind(self):
        self.parent.triggers.remove(self)

    def get_status(self):
        return self.status ^ self.negate

    def serialize(self):
        return {'type' : self.type, 'negate' : self.negate}

class PressTrigger(Trigger):
    type = 'press'
    unique = True

    def callback(self, player):
        shared = self.parent.shared_trigger_objects[self.type]
        shared.add(player)
        self.status = True
        self.parent.trigger_check()
        self.status = False
        shared.discard(player)

    def __str__(self):
        s = 'player press'
        return S_TRIGGER_LIST_NOT + s if self.negate else s

class DistanceTrigger(Trigger):
    type = 'distance'

    def __init__(self, protocol, radius, negate = False):
        Trigger.__init__(self, protocol, negate)
        self.radius = radius
        protocol.position_triggers.append(self)

    def unbind(self):
        Trigger.unbind(self)
        shared = self.parent.shared_trigger_objects[self.type]
        shared.clear()
        self.protocol.position_triggers.remove(self)

    def callback(self, player):
        parent = self.parent
        if not parent:
            return
        shared = parent.shared_trigger_objects[self.type]
        status = False
        if not player.disconnected and player.world_object:
            x1, y1, z1 = parent.x + 0.5, parent.y + 0.5, parent.z + 0.5
            x2, y2, z2 = player.world_object.position.get()
            status = collision_3d(x1, y1, z1, x2, y2, z2, self.radius)
        if status:
            shared.add(player)
        else:
            shared.discard(player)
        status = bool(shared)
        if self.status != status:
            self.status = status
            if self.parent:
                parent.trigger_check()

    def serialize(self):
        return {
            'type' : self.type,
            'negate' : self.negate,
            'radius' : self.radius
        }

    def __str__(self):
        s = 'player distance=%s' % self.radius
        return S_TRIGGER_LIST_NOT + s if self.negate else s

class TrackTrigger(Trigger):
    type = 'track'
    tracked_player = None

    def __init__(self, protocol, radius, negate = False):
        Trigger.__init__(self, protocol, negate)
        self.radius = radius
        protocol.position_triggers.append(self)

    def unbind(self):
        Trigger.unbind(self)
        shared = self.parent.shared_trigger_objects[self.type]
        shared.discard(self.tracked_player)
        self.protocol.position_triggers.remove(self)

    def callback(self, player):
        parent = self.parent
        if not parent:
            return
        shared = parent.shared_trigger_objects[self.type]
        if self.status:
            if self.tracked_player is not player:
                # we're already locked on a different player
                return
        elif player in shared:
            # another trigger has already claimed this player
            return
        status = False
        if not player.disconnected and player.world_object:
            x1, y1, z1 = parent.x + 0.5, parent.y + 0.5, parent.z + 0.5
            x2, y2, z2 = player.world_object.position.get()
            status = collision_3d(x1, y1, z1, x2, y2, z2, self.radius)
        if self.status != status:
            # keep track of the player to avoid tripping other distance triggers
            # in the same button
            if status:
                shared.add(player)
                self.tracked_player = player
            else:
                shared.discard(player)
                self.tracked_player = None

            self.status = status
            if self.parent:
                parent.trigger_check()

    def serialize(self):
        return {
            'type' : self.type,
            'negate' : self.negate,
            'radius' : self.radius
        }

    def __str__(self):
        s = 'track distance=%s' % self.radius
        return S_TRIGGER_LIST_NOT + s if self.negate else s

class HeightTrigger(Trigger):
    type = 'height'

    def __init__(self, protocol, platform_id, height, negate = False):
        Trigger.__init__(self, protocol, negate)
        platform = protocol.platforms[platform_id]
        self.platform = platform
        self.target_height = height
        if platform.bound_triggers is None:
            platform.bound_triggers = []
        platform.bound_triggers.append(self)
        self.callback(platform)

    def unbind(self):
        Trigger.unbind(self)
        self.platform.bound_triggers.remove(self)

    def callback(self, platform):
        met = platform.height == self.target_height
        if self.status != met:
            self.status = met
            if self.parent:
                self.parent.trigger_check()

    def serialize(self):
        return {
            'type' : self.type,
            'negate' : self.negate,
            'platform_id' : self.platform.id,
            'height' : self.target_height
        }

    def __str__(self):
        s = "platform '%s' height=%s" % (self.platform.label,
            self.target_height)
        return S_TRIGGER_LIST_NOT + s if self.negate else s

TRIGGER_CLASSES = {}
for cls in (PressTrigger, TrackTrigger, DistanceTrigger, HeightTrigger):
    TRIGGER_CLASSES[cls.type] = cls

PLATFORM_ACTION_FUNCTIONS = {
    'start' : 'start',
    'height' : 'start',
    'raise' : 'start',
    'lower' : 'start',
    'elevator' : 'start',
    'output' : 'start'
}

class PlatformAction:
    type = 'platform'

    def __init__(self, protocol, platform_id, action, kwargs):
        self.platform = protocol.platforms[platform_id]
        self.action = action
        func_name = PLATFORM_ACTION_FUNCTIONS[action]
        self.callback = getattr(self.platform, func_name)
        self.kwargs = kwargs

    def run(self, value, objects):
        if self.action == 'output':
            self.callback(height = int(value), **self.kwargs)
        elif value:
            self.callback(**self.kwargs)

    def serialize(self):
        return {
            'type' : self.type,
            'platform_id' : self.platform.id,
            'action' : self.action,
            'kwargs' : self.kwargs
        }

    def __str__(self):
        return "platform '%s' %s(%s)" % (self.platform.label,
            self.kwargs['mode'], self.kwargs['height'])

PLAYER_ACTION_FUNCTIONS = {
    'teleport' : 'set_location',
    'chat' : 'send_chat',
    'damage' : 'hit'
}

class PlayerAction:
    type = 'player'

    def __init__(self, protocol, action, kwargs):
        self.action = action
        func_name = PLAYER_ACTION_FUNCTIONS[action]
        self.callback = getattr(protocol.connection_class, func_name)
        self.kwargs = kwargs

    def run(self, value, objects):
        if not value:
            return
        for player in objects:
            self.callback(player, **self.kwargs)

    def serialize(self):
        return {
            'type' : self.type,
            'action' : self.action,
            'kwargs' : self.kwargs
        }

    def __str__(self):
        if self.action == 'teleport':
            info = S_NICE_LOCATION.format(*self.kwargs['location'])
        elif self.action == 'chat':
            info = '"%s"' % self.kwargs['value'].strip()
        elif self.action == 'damage':
            info = self.kwargs['value']
        return "player %s(%s)" % (self.action, info)

ACTION_CLASSES = {}
for cls in (PlatformAction, PlayerAction):
    ACTION_CLASSES[cls.type] = cls

class BaseObject:
    protocol = None
    id = None

    def __init__(self, protocol, id):
        self.protocol = protocol
        self.id = id

    def release(self):
        pass

class Button(BaseObject):
    label = None
    action_pending = False
    disabled = False
    silent = False
    cooldown_call = None

    def __init__(self, protocol, id, x, y, z, color):
        BaseObject.__init__(self, protocol, id)
        self.label = str(self.id)
        self.x, self.y, self.z = x, y, z
        self.color = color
        self.color_triggered = tuple(int(c * 0.2) for c in color)
        self.actions = []
        self.triggers = []
        self.shared_trigger_objects = defaultdict(set)
        self.logic = 'and'
        self.cooldown = 0.5
        protocol.map.set_point(x, y, z, self.color)

    def release(self):
        BaseObject.release(self)
        self.clear_triggers()
        if self.cooldown_call and self.cooldown_call.active():
            self.cooldown_call.cancel()
        self.cooldown_call = None

    def destroy(self):
        self.release()
        if self.protocol.map.destroy_point(self.x, self.y, self.z):
            send_block(self.protocol, self.x, self.y, self.z, DESTROY_BLOCK)

    def add_trigger(self, new_trigger):
        new_trigger.parent = self
        if new_trigger.unique:
            # ensure there is only one trigger of this type
            remove_triggers = [trigger for trigger in self.triggers if
                trigger.type == new_trigger.type]
            for trigger in remove_triggers:
                trigger.unbind()
        self.triggers.append(new_trigger)
        self.trigger_check()

    def clear_triggers(self):
        for trigger in self.triggers[:]:
            trigger.unbind()

    def trigger_check(self):
        self.action_pending = False
        check = all if self.logic == 'and' else any
        if check(trigger.get_status() for trigger in self.triggers):
            if self.cooldown_call:
                # schedule action for after the button resets
                self.action_pending = True
            else:
                self.action()
        else:
            for action in self.actions:
                action.run(False, None)

    def action(self):
        self.cooldown_call = callLater(self.cooldown, self.reset)
        objects = set(flatten(self.shared_trigger_objects.itervalues()))
        if self.disabled:
            if not self.silent:
                for player in objects:
                    player.send_chat(S_NOT_WORKING)
            return
        for action in self.actions:
            action.run(True, objects)
        if not self.silent:
            self.build_block(self.color_triggered)

    def reset(self):
        self.cooldown_call = None
        if not self.silent and not self.disabled:
            self.build_block(self.color)
        if self.action_pending:
            # ensure conditions are still met
            self.trigger_check()

    def build_block(self, color):
        send_block(self.protocol, self.x, self.y, self.z, DESTROY_BLOCK)
        send_color(self.protocol, color)
        send_block(self.protocol, self.x, self.y, self.z, BUILD_BLOCK)

    def serialize(self):
        return {
            'id' : self.id,
            'location' : (self.x, self.y, self.z),
            'label' : self.label,
            'color' : self.color,
            'actions' : [action.serialize() for action in self.actions],
            'triggers' : [trigger.serialize() for trigger in self.triggers],
            'logic' : self.logic,
            'cooldown' : self.cooldown,
            'disabled' : self.disabled,
            'silent' : self.silent
        }

class Platform(BaseObject):
    label = None
    last_z = None
    target_z = None
    frozen = False
    mode = None
    busy = False
    delay_call = None
    bound_triggers = None

    def __init__(self, protocol, id, x1, y1, z1, x2, y2, z2, color):
        BaseObject.__init__(self, protocol, id)
        self.label = str(self.id)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.z, self.start_z = z1, z2
        self.height = self.start_z - self.z
        self.color = color
        self.cycle_loop = LoopingCall(self.cycle)
        for x, y, z in prism(x1, y1, z1, x2, y2, z2):
            protocol.map.set_point(x, y, z, color)

    def contains(self, x, y, z):
        return aabb(x, y, z, self.x1, self.y1, self.z, self.x2, self.y2,
            self.start_z)

    def overlaps(self, p):
        return (self.x1 <= p.x2 and self.y1 <= p.y2 and self.z <= p.start_z and
            self.x2 >= p.x1 and self.y2 >= p.y1 and self.start_z >= p.z)

    def destroy(self):
        self.destroy_z(self.z, self.start_z + 1)
        self.release()

    def release(self):
        BaseObject.release(self)
        if self.bound_triggers:
            bound_buttons = set()
            for trigger in self.bound_triggers[:]:
                bound_buttons.add(trigger.parent)
                trigger.unbind()
            for button in bound_buttons:
                button.trigger_check()
        if self.delay_call and self.delay_call.active():
            self.delay_call.cancel()
        self.delay_call = None
        if self.cycle_loop and self.cycle_loop.running:
            self.cycle_loop.stop()
        self.cycle_loop = None

    def start(self, height, mode, speed, delay, wait = None, force = False):
        if self.busy and not force:
            return
        if mode == 'raise':
            height = (self.start_z - self.z) + height
        elif mode == 'lower':
            height = (self.start_z - self.z) - height
        self.mode = mode
        self.last_z = self.z
        self.target_z = max(0, min(self.start_z, self.start_z - height))
        self.speed = speed
        self.wait = wait
        if self.z == self.target_z:
            return
        self.busy = True
        self.start_cycle_later(delay)

    def start_cycle_later(self, delay):
        if self.delay_call and self.delay_call.active():
            self.delay_call.cancel()
        self.delay_call = None
        if self.cycle_loop and self.cycle_loop.running:
            self.cycle_loop.stop()
        self.cycle_loop = LoopingCall(self.cycle)
        if delay > 0.0:
            self.delay_call = callLater(delay, self.cycle_loop.start, self.speed)
        else:
            self.cycle_loop.start(self.speed)

    def cycle(self):
        if self.frozen:
            return
        if self.z > self.target_z:
            self.z -= 1
            self.build_plane(self.z)
            self.protocol.update_entities()
            # unstuck players
            for player in self.protocol.players.itervalues():
                obj = player.world_object
                looking_up = obj.orientation.get()[2] < 0.4 # 0.5 (allow lag)
                x, y, z = obj.position.get()
                if aabb(x, y, z, self.x1, self.y1, self.z - 2,
                    self.x2, self.y2, self.start_z):
                    if looking_up and not obj.crouch and not z > self.z:
                        # player is looking up, no need to readjust
                        continue
                    z = self.z - 2.4
                    if player.world_object.crouch:
                        z += 1.0
                    position_data.x = x
                    position_data.y = y
                    position_data.z = z
                    player.send_contained(position_data)
                    player.world_object.position.z = z
        elif self.z < self.target_z:
            self.destroy_z(self.z)
            self.protocol.update_entities()
            self.z += 1
        self.height = self.start_z - self.z
        if self.z == self.target_z:
            self.cycle_loop.stop()
            self.cycle_loop = None
            if self.mode == 'elevator':
                self.mode = 'return'
                self.target_z = self.last_z
                self.start_cycle_later(self.wait)
            else:
                self.busy = False
        if self.bound_triggers:
            for trigger in self.bound_triggers:
                trigger.callback(self)

    def build_line(self, x1, y1, z1, x2, y2, z2):
        line = cube_line(x1, y1, z1, x2, y2, z2)
        for x, y, z in line:
            self.protocol.map.set_point(x, y, z, self.color)
        block_line.player_id = 32
        block_line.x1 = x1
        block_line.y1 = y1
        block_line.z1 = z1
        block_line.x2 = x2
        block_line.y2 = y2
        block_line.z2 = z2
        self.protocol.send_contained(block_line, save = True)

    def build_plane(self, z):
        send_color(self.protocol, self.color)
        for line in plane_least_rows(self.x1, self.y1, self.x2, self.y2, z):
            self.build_line(*line)

    def destroy_z(self, z1, z2 = None):
        if z2 is None:
            z2 = z1 + 1
        protocol = self.protocol
        overlaps = [platform for platform in protocol.platforms.itervalues() if
            platform is not self and platform.overlaps(self)]
        for x, y, z in prism(self.x1, self.y1, z1, self.x2, self.y2, z2):
            if any(platform.contains(x, y, z) for platform in overlaps):
                continue
            if (x, y, z) in protocol.buttons:
                continue
            if protocol.map.destroy_point(x, y, z):
                send_block(protocol, x, y, z, DESTROY_BLOCK)

    def serialize(self):
        z = self.last_z if self.mode == 'elevator' else self.target_z
        return {
            'id' : self.id,
            'start' : (self.x1, self.y1, z or self.z),
            'end' : (self.x2, self.y2, self.start_z),
            'label' : self.label,
            'color' : self.color,
            'frozen' : self.frozen
        }

def player_action(player, select, inspect):
    if not select and not inspect:
        return
    protocol = player.protocol
    if not protocol.platforms and not protocol.buttons:
        return
    state = player.states.top()
    if inspect and not state and not select:
        return
    last_action = player.last_action
    if last_action is not None and seconds() - last_action <= ACTION_COOLDOWN:
        return
    player.last_action = seconds()
    location = player.world_object.cast_ray(ACTION_RAY_LENGTH)
    if location is None:
        return
    x, y, z = location

    button = protocol.buttons.get(location)
    if button:
        if state:
            if select and state.name == 'select button':
                state.button = button
                player.states.pop()
                return
            elif inspect and 'button' in state.name:
                info = S_BUTTON_INFO.format(label = button.label,
                    cooldown = button.cooldown)
                player.send_chat(info)
                return
        if not inspect:
            for trigger in button.triggers:
                if trigger.type == 'press':
                    trigger.callback(player)
    elif state and 'platform' in state.name:
        platform = protocol.get_platform(x, y, z)
        if select and state.name == 'select platform':
            if platform:
                state.platform = platform
                player.states.pop()
                return
            else:
                player.send_chat(S_NOT_A_PLATFORM)
        elif inspect:
            info = S_PLATFORM_INFO.format(label = platform.label,
                height = platform.height)
            player.send_chat(info)

class State(object):
    name = None
    blocking = False
    parent_state = None

    def on_enter(self, protocol, player):
        pass

    def on_exit(self, protocol, player):
        pass

    def get_parent(self):
        return self.parent_state if self.parent_state else self

class NewPlatformState(State):
    name = 'new platform'
    blocking = True
    label = None

    def __init__(self, label = None):
        self.label = label

    def on_enter(self, protocol, player):
        self.blocks = set()
        return S_PLATFORM_STARTED

    def on_exit(self, protocol, player):
        if not self.blocks:
            return S_PLATFORM_CANCEL

        zipped = zip(*self.blocks)
        x1, y1 = min(zipped[0]), min(zipped[1])
        x2, y2 = max(zipped[0]) + 1, max(zipped[1]) + 1
        z1, z2 = min(zipped[2]), max(zipped[2])
        if z1 != z2:
            # undo placed blocks if the design is invalid
            block_action.value = DESTROY_BLOCK
            block_action.player_id = player.player_id
            for x, y, z in self.blocks:
                if protocol.map.destroy_point(x, y, z):
                    block_action.x = x
                    block_action.y = y
                    block_action.z = z
                    protocol.send_contained(block_action, save = True)
            return S_PLATFORM_NOT_FLAT
        z2 += 1

        # get averaged color
        color_sum = (0, 0, 0)
        for x, y, z in self.blocks:
            color = protocol.map.get_color(x, y, z)
            color_sum = tuple(imap(operator.add, color_sum, color))
        color_avg = tuple(n / len(self.blocks) for n in color_sum)

        protocol.highest_id += 1
        id = protocol.highest_id
        platform = Platform(protocol, id, x1, y1, z1, x2, y2, z2, color_avg)
        platform.label = self.label or platform.label
        platform.build_plane(z1)
        protocol.platforms[id] = platform
        player.previous_platform = platform
        return S_PLATFORM_CREATED.format(label = platform.label)

class NewButtonState(State):
    name = 'new button'
    location = None
    label = None

    def __init__(self, label = None):
        self.label = label

    def on_enter(self, protocol, player):
        return S_BUTTON_PLACEMENT

    def on_exit(self, protocol, player):
        if not self.location:
            return S_BUTTON_CANCEL
        if self.location in protocol.buttons:
            return S_BUTTON_OVERLAPS

        protocol.highest_id += 1
        id = protocol.highest_id
        x, y, z = self.location
        button = Button(protocol, id, x, y, z, self.color)
        button.label = self.label or button.label
        button.add_trigger(PressTrigger(protocol))
        protocol.buttons[(id, (x, y, z))] = button
        player.previous_button = button
        return S_BUTTON_CREATED.format(label = button.label)

class PlatformCommandState(State):
    name = 'platform command'
    platform = None

    def __init__(self, command):
        self.command = command

    def on_exit(self, protocol, player):
        platform = self.platform
        if not platform:
            return S_COMMAND_CANCEL.format(command = 'platform ' + self.command)

        command = self.command
        if command == 'name':
            old, platform.label = platform.label, self.label
            return S_PLATFORM_RENAMED.format(old_label = old, label = self.label)
        elif command == 'height':
            platform.start(self.height, 'once', 0.1, 0.0, None, force = True)
        elif command == 'freeze':
            platform.frozen = not platform.frozen
            result = S_FROZEN if platform.frozen else S_UNFROZEN
            return result.format(label = platform.label)
        elif command == 'destroy':
            platform.destroy()
            del protocol.platforms[platform.id]
            # remove actions affecting this platform
            for button in protocol.buttons.itervalues():
                button.actions = [action for action in button.actions
                    if getattr(action, 'platform', None) is not platform]
            # cancel any ongoing commands targeting this platform
            for player in protocol.players.itervalues():
                state = player.states.top()
                if not state:
                    continue
                if getattr(state.get_parent(), 'platform', None) is platform:
                    player.states.exit()
            # clear last platform memory from players
            for player in protocol.players.itervalues():
                if player.previous_platform is platform:
                    player.previous_platform = None
            return S_PLATFORM_DESTROYED.format(label = platform.label)

class ButtonCommandState(State):
    name = 'button command'
    button = None

    def __init__(self, command):
        self.command = command

    def on_exit(self, protocol, player):
        button = self.button
        if not button:
            return S_COMMAND_CANCEL.format(command = 'button ' + self.command)

        command = self.command
        if command == 'name':
            old, button.label = button.label, self.label
            return S_BUTTON_RENAMED.format(old_label = old, label = self.label)
        elif command == 'destroy':
            button.destroy()
            del protocol.buttons[button]
            # clear last button memory from players
            for player in protocol.players.itervalues():
                if player.previous_button is button:
                    player.previous_button = None
            return S_BUTTON_DESTROYED.format(label = button.label)
        elif command == 'toggle':
            button.disabled = not button.disabled
            result = S_DISABLED if button.disabled else S_ENABLED
            return result.format(label = button.label)
        elif command == 'cooldown':
            button.cooldown = self.cooldown
            return S_BUTTON_COOLDOWN.format(label = button.label,
                cooldown = self.cooldown)

class ActionAddState(State):
    name = 'action'
    platform = None
    button = None

    def __init__(self, action, add = True):
        self.action = action
        self.add = add

    def on_exit(self, protocol, player):
        button = self.button
        if not button:
            return S_COMMAND_CANCEL.format(command = self.name)

        if self.action in PLATFORM_ACTION_FUNCTIONS:
            if not self.platform:
                return S_COMMAND_CANCEL.format(command = self.name)
            new_action = PlatformAction(protocol, self.platform.id,
                self.action, self.kwargs)
        elif self.action in PLAYER_ACTION_FUNCTIONS:
            new_action = PlayerAction(protocol, self.action, self.kwargs)

        if not self.add:
            button.actions = []
        button.actions.append(new_action)
        return S_ACTION_ADDED.format(action = self.action, label = button.label)

class ActionCommandState(State):
    name = 'action'
    button = None

    def __init__(self, command):
        self.command = command

    def on_exit(self, protocol, player):
        button = self.button
        if not button:
            return S_COMMAND_CANCEL.format(command = 'action ' + self.command)

        if self.command == 'list':
            if not button.actions:
                return S_ACTION_LIST_EMPTY.format(label = button.label)

            items = ' -- '.join('#%s %s' % (i, action) for i, action in
                enumerate(button.actions))
            return S_ACTION_LIST_HEADER.format(label = button.label) + items
        elif self.command == 'del':
            if self.number == 'all':
                button.actions = []
                return S_ACTION_DELETED_ALL.format(label = button.label)
            else:
                try:
                    index = self.number % len(button.actions)
                    action = button.actions.pop(self.number)
                except IndexError:
                    return S_ACTION_INVALID_NUMBER

                action_type = action.type.capitalize()
                return S_ACTION_DELETED.format(action = action_type,
                    number = index, label = button.label)

class TriggerAddState(State):
    name = 'trigger'
    platform = None
    button = None

    def __init__(self, trigger, negate, add = True):
        self.trigger = trigger
        self.negate = negate
        self.add = add

    def on_exit(self, protocol, player):
        button = self.button
        if not button:
            return S_COMMAND_CANCEL.format(command = self.name)

        if self.trigger == 'press':
            new_trigger = PressTrigger(protocol)
        elif self.trigger == 'distance':
            new_trigger = DistanceTrigger(protocol, self.radius)
        elif self.trigger == 'track':
            new_trigger = TrackTrigger(protocol, self.radius)
        elif self.trigger == 'height':
            if not self.platform:
                return S_COMMAND_CANCEL.format(command = self.name)
            new_trigger = HeightTrigger(protocol, self.platform.id, self.height)
        new_trigger.negate = self.negate

        if not self.add:
            button.clear_triggers()
        button.add_trigger(new_trigger)
        return S_TRIGGER_ADDED.format(trigger = self.trigger,
            label = button.label)

class TriggerCommandState(State):
    name = 'trigger'
    button = None

    def __init__(self, command):
        self.command = command

    def on_exit(self, protocol, player):
        button = self.button
        if not button:
            return S_COMMAND_CANCEL.format(command = 'trigger ' + self.command)

        if self.command == 'list':
            if not button.triggers:
                return S_TRIGGER_LIST_EMPTY.format(label = button.label)

            items = []
            for i, trigger in enumerate(button.triggers):
                item = '#%s %s' % (i, trigger)
                if trigger.status:
                    item += S_TRIGGER_LIST_ITEM_IS_TRUE
                items.append(item)
            separator = (S_TRIGGER_LIST_AND if button.logic == 'and' else
                S_TRIGGER_LIST_OR)
            items = separator.join(items)
            return S_TRIGGER_LIST_HEADER.format(label = button.label) + items
        elif self.command == 'del':
            if self.number == 'all':
                button.clear_triggers()
                return S_TRIGGER_DELETED_ALL.format(label = button.label)
            else:
                try:
                    trigger = button.triggers[self.number]
                    index = button.triggers.index(trigger)
                except IndexError:
                    return S_TRIGGER_INVALID_NUMBER

                trigger.unbind()
                button.trigger_check()
                trigger_type = trigger.type.capitalize()
                return S_TRIGGER_DELETED.format(trigger = trigger_type,
                    number = index, label = button.label)
        elif self.command == 'logic':
            button.logic = self.logic
            button.trigger_check()
            result = S_LOGIC_AND if self.logic == 'and' else S_LOGIC_OR
            return result.format(label = button.label)
        elif self.command == 'quiet':
            button.silent = not button.silent
            result = S_SILENT if button.silent else S_NOISY
            return result.format(label = button.label)

class SelectPlatformState(State):
    name = 'select platform'
    platform = None
    parent_state = None

    def __init__(self, parent_state):
        self.parent_state = parent_state

    def on_enter(self, protocol, player):
        return S_SELECT_PLATFORM

    def on_exit(self, protocol, player):
        self.parent_state.platform = self.platform
        player.previous_platform = self.platform or player.previous_platform
        if player.states.top() is self.parent_state:
            player.states.pop()
        elif self.platform:
            return S_PLATFORM_SELECTED.format(label = self.platform.label)

class SelectButtonState(State):
    name = 'select button'
    button = None
    parent_state = None

    def __init__(self, parent_state):
        self.parent_state = parent_state

    def on_enter(self, protocol, player):
        return S_SELECT_BUTTON

    def on_exit(self, protocol, player):
        self.parent_state.button = self.button
        player.previous_button = self.button or player.previous_button
        if player.states.top() is self.parent_state:
            player.states.pop()
        elif self.button:
            return S_BUTTON_SELECTED.format(label = self.button.label)

class StateStack:
    stack = None
    protocol = None
    connection = None

    def __init__(self, connection):
        self.stack = []
        self.connection = connection
        self.protocol = connection.protocol

    def top(self):
        return self.stack[-1] if self.stack else None

    def enter(self, state):
        self.stack.append(state)
        result = state.on_enter(self.protocol, self.connection)
        if result:
            self.connection.send_chat(result)

    def push(self, state):
        self.stack.append(state)

    def pop(self):
        state = self.stack.pop()
        result = state.on_exit(self.protocol, self.connection)
        if result:
            self.connection.send_chat(result)
        state = self.top()
        if state:
            result = state.on_enter(self.protocol, self.connection)
            if result:
                self.connection.send_chat(result)

    def exit(self):
        while self.stack:
            self.pop()

def apply_script(protocol, connection, config):
    class PlatformConnection(connection):
        states = None
        where_location = None
        where_orientation = None
        last_action = None
        previous_button = None
        previous_platform = None

        def on_reset(self):
            if self.states:
                self.states.stack = []
            self.where_location = None
            self.where_orientation = None
            self.last_action = None
            self.previous_button = None
            self.previous_platform = None
            connection.on_reset(self)

        def on_login(self, name):
            self.states = StateStack(self)
            connection.on_login(self, name)

        def on_disconnect(self):
            self.states = None
            for trigger in self.protocol.position_triggers:
                trigger.callback(self)
            connection.on_disconnect(self)

        def on_block_build(self, x, y, z):
            state = self.states.top()
            if state:
                if state.name == 'new platform':
                    state.blocks.add((x, y, z))
                elif state.name == 'new button':
                    state.location = (x, y, z)
                    state.color = self.color
                    self.states.pop()
            connection.on_block_build(self, x, y, z)

        def on_line_build(self, points):
            state = self.states.top()
            if state and state.name == 'new platform':
                state.blocks.update(points)
            connection.on_line_build(self, points)

        def on_block_destroy(self, x, y, z, mode):
            is_platform = self.protocol.is_platform
            if mode == DESTROY_BLOCK:
                if is_platform(x, y, z):
                    return False
            elif mode == SPADE_DESTROY:
                if (is_platform(x, y, z) or
                    is_platform(x, y, z + 1) or
                    is_platform(x, y, z - 1)):
                    return False
            elif mode == GRENADE_DESTROY:
                for i, j, k in prism(x - 1, y - 1, z - 1, x + 2, y + 2, z + 2):
                    if is_platform(i, j, k):
                        return False
            return connection.on_block_destroy(self, x, y, z, mode)

        def on_block_removed(self, x, y, z):
            state = self.states.top()
            if state and state.name == 'new platform':
                state.blocks.discard((x, y, z))
            connection.on_block_removed(self, x, y, z)

        def on_shoot_set(self, fire):
            if self.tool == SPADE_TOOL and fire:
                player_action(self, True, False)
            connection.on_shoot_set(self, fire)

        def on_position_update(self):
            if self.tool == SPADE_TOOL:
                player_action(self, self.world_object.primary_fire, False)
            connection.on_position_update(self)

        def on_orientation_update(self, x, y, z):
            if self.tool == SPADE_TOOL:
                player_action(self, self.world_object.primary_fire, False)
            return connection.on_orientation_update(self, x, y, z)

        def on_animation_update(self, jump, crouch, sneak, sprint):
            if self.tool == SPADE_TOOL:
                inspect = not self.world_object.sneak and sneak
                player_action(self, self.world_object.primary_fire, inspect)
            return connection.on_animation_update(self, jump, crouch, sneak,
                sprint)

        def on_command(self, command, parameters):
            if command == 'where' and not parameters:
                self.where_location = self.world_object.position.get()
                self.where_orientation = self.world_object.orientation.get()
            connection.on_command(self, command, parameters)

    class PlatformProtocol(protocol):
        highest_id = None
        platforms = None
        platform_json_dirty = False
        buttons = None
        position_triggers = None
        autosave_loop = None

        def on_map_change(self, map):
            self.highest_id = -1
            self.platforms = {}
            self.buttons = MultikeyDict()
            self.position_triggers = []
            self.platform_json_dirty = False
            self.load_platform_json()
            if AUTOSAVE_EVERY:
                self.autosave_loop = LoopingCall(self.dump_platform_json)
                self.autosave_loop.start(AUTOSAVE_EVERY * 60.0, now = False)
            protocol.on_map_change(self, map)

        def on_map_leave(self):
            if SAVE_ON_MAP_CHANGE:
                self.dump_platform_json()
            if self.autosave_loop and self.autosave_loop.running:
                self.autosave_loop.stop()
            self.autosave_loop = None
            for platform in self.platforms.itervalues():
                platform.release()
            for button in self.buttons.itervalues():
                button.release()
            self.platforms = None
            self.buttons = None
            self.position_triggers = None
            protocol.on_map_leave(self)

        def on_world_update(self):
            for player in self.players.itervalues():
                for trigger in self.position_triggers:
                    trigger.callback(player)
            protocol.on_world_update(self)

        def get_platform_json_path(self):
            filename = self.map_info.rot_info.full_name + '_platform.txt'
            return os.path.join(DEFAULT_LOAD_DIR, filename)

        def load_platform_json(self):
            path = self.get_platform_json_path()
            if not os.path.isfile(path):
                return
            with open(path, 'r') as file:
                data = json.load(file)
            ids = []
            for platform_data in data['platforms']:
                x1, y1, z1 = platform_data['start']
                x2, y2, z2 = platform_data['end']
                color = tuple(platform_data['color'])
                id = platform_data['id']
                ids.append(id)
                platform = Platform(self, id, x1, y1, z1, x2, y2, z2, color)
                platform.label = platform_data['label']
                platform.frozen = platform_data['frozen']
                self.platforms[id] = platform
            stored_actions = {}
            for button_data in data['buttons']:
                x, y, z = button_data['location']
                color = tuple(button_data['color'])
                id = button_data['id']
                ids.append(id)
                button = Button(self, id, x, y, z, color)
                button.label = button_data['label']
                button.logic = button_data['logic']
                button.cooldown = button_data['cooldown']
                button.disabled = button_data['disabled']
                button.silent = button_data['silent']
                for trigger_data in button_data['triggers']:
                    cls = trigger_data.pop('type')
                    new_trigger = TRIGGER_CLASSES[cls](self, **trigger_data)
                    new_trigger.parent = button
                    button.triggers.append(new_trigger)
                for action_data in button_data['actions']:
                    cls = action_data.pop('type')
                    new_action = ACTION_CLASSES[cls](self, **action_data)
                    button.actions.append(new_action)
                self.buttons[(id, (x, y, z))] = button
            ids.sort()
            self.highest_id = ids[-1] if ids else -1
            self.platform_json_dirty = True
            for button in self.buttons.itervalues():
                button.trigger_check()

        def dump_platform_json(self):
            if (not self.platforms and not self.buttons and
                not self.platform_json_dirty):
                return
            data = {
                'platforms' : [platform.serialize() for platform in
                    self.platforms.values()],
                'buttons' : [button.serialize() for button in
                    self.buttons.values()]
            }
            path = self.get_platform_json_path()
            with open(path, 'w') as file:
                json.dump(data, file, indent = 4)
            self.platform_json_dirty = True

        def get_platform(self, x, y, z):
            for platform in self.platforms.itervalues():
                if platform.contains(x, y, z):
                    return platform
            return None

        def is_platform(self, x, y, z):
            return self.get_platform(x, y, z) or (x, y, z) in self.buttons

    return PlatformProtocol, PlatformConnection
