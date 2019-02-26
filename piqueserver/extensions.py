
import os
import importlib
import imp

from twisted.logger import Logger

log = Logger()

def check_scripts(scripts):
    '''
    Ensures that there are no duplicate scripts in scripts
    :param scripts: list of scripts
    :return: True if there is no duplicate scripts, False otherwise
    '''
    seen = set()
    dups = []
    for script in scripts:
        if script in seen:
            dups.append(script)
        else:
            seen.add(script)
    if dups:
        log.warn("Scripts included multiple times: {}".format(dups))
        return False
    return True

def load_scripts(script_names, script_dir):
    '''
    Loads all scripts from the script_dir folder
    :param script_names: A list of script names
    :param script_dir: Path to scripts directory
    :return: A list of script modules
    '''
    script_objects = []

    for script in script_names[:]:
        try:
            # this finds and loads scripts directly from the script dir
            # no need for messing with sys.path
            f, filename, desc = imp.find_module(script, [script_dir])
            module = imp.load_module(
                'piqueserver_script_namespace_' + script, f, filename, desc)
            script_objects.append(module)
        except ImportError as e:
            # warning: this also catches import errors from inside the script
            # module it tried to load
            try:
                module = importlib.import_module(script)
                script_objects.append(module)
            except ImportError as e:
                log.error("(script '{}' not found: {!r})".format(script, e))
                script_names.remove(script)

    return script_objects

def apply_scripts(scripts, config, protocol_class, connection_class):
    '''
    Applies scripts to the specified protocol and connection class instances
    :param scripts: List of scripts modules to apply
    :param config: Config object which holds a dict
    :param protocol_class: The protocol class instance to update
    :param connection_class: The connection class instance to update
    :return: The updated protocol and connection class instances
    '''

    for script in scripts:
        protocol_class, connection_class = script.apply_script(
            protocol_class, connection_class, config.get_dict())

    return (protocol_class, connection_class)

def apply_gamemode_script(current_game_mode, config, protocol_class, connection_class):
    '''
    :param current_game_mode: The current game mode of the server
    :param config: A configuration object containing the directory where the game mode scripts are located
    :param protocol_class: The protocol class instance to update
    :param connection_class: The connection class instance to update
    :return: The updated progocol and connection class instances
    '''
    if current_game_mode not in ('ctf', 'tc'):
        # must be a script with this game mode
        module = None
        try:
            game_mode_dir = os.path.join(config.config_dir, 'game_modes/')
            f, filename, desc = imp.find_module(
                current_game_mode, [game_mode_dir])
            module = imp.load_module(
                'piqueserver_gamemode_namespace_' + current_game_mode, f, filename, desc)
        except ImportError as e:
            try:
                module = importlib.import_module(current_game_mode)
            except ImportError as e:
                log.error("(game_mode '%s' not found: %r)" %
                              (current_game_mode, e))

        if module:
            protocol_class, connection_class = module.apply_script(
                protocol_class, connection_class, config.get_dict())

    return (protocol_class, connection_class)
