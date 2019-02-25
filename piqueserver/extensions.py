
import os
import importlib
import imp

def check_scripts(scripts):
    '''
    Checks if scripts were included multiple times.
    '''
    seen = set()
    dups = []
    for script in scripts:
        if script in seen:
            dups.append(script)
        else:
            seen.add(script)
    if dups:
        #log.warn("Scripts included multiple times: {}".format(dups)) TODO: Pass logger object to this function
        return False
    return True


def load_scripts(config, scripts_option, log=None):
    '''
    Loads all scripts from script/ folder
    Returns a list of script modules
    '''
    script_objects = []
    script_names = scripts_option.get()
    script_dir = os.path.join(config.config_dir, 'scripts/')

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
                if (log != None):
                    log.error("(script '{}' not found: {!r})".format(script, e))
                script_names.remove(script)

    return script_objects


def apply_scripts(scripts, config, protocol_class, connection_class):
    '''
    Applies scripts to the server
    Returns protocol and connection class
    '''

    for script in scripts:
        protocol_class, connection_class = script.apply_script(
            protocol_class, connection_class, config.get_dict())

    return (protocol_class, connection_class)
