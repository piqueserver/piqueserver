
import os

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


def load_scripts(config):
    '''
    Loads all scripts from script/ folder
    Returns a list of script modules
    '''


def apply_scripts(scripts, config):
    '''
    Applies scripts to the server
    Returns protocol and connection class
    '''

