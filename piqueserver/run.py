from __future__ import print_function, unicode_literals

import os
import filecmp
import shutil
import sys
import argparse
import gzip
import json

import six.moves.urllib as urllib

from piqueserver import cfg
from piqueserver.config import config, TOML_FORMAT, JSON_FORMAT

MAXMIND_DOWNLOAD = 'http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz'

# (major, minor) versions of python we are supporting
# used on startup to emit a warning if not running on a supported version
SUPPORTED_PYTHONS = ((2, 7), (3, 4), (3, 5), (3, 6))


def get_git_rev():
    if not os.path.exists(".git"):
        return 'snapshot'

    from distutils.spawn import find_executable
    if find_executable("git") is None:
        return 'gitless'

    import subprocess
    pipe = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = pipe.stdout.read()[:40]
    if not ret:
        return 'unknown'
    return ret


def copytree(src, dst):
    """
    A re-implementation of shutil.copytree that doesn't fail if dst already exists.
    Other properties:
    Doesn't over-write if src/dst files don't differ.
    Creates a backup of dst file before over-writing.
    """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d)
        else:
            # create/copy if not exist
            if not os.path.exists(d):
                shutil.copy2(s, d)
            # if src/dst files differ, backup and over-write dst file
            elif not filecmp.cmp(s, d):
                shutil.copy2(d, d + '.bak')
                shutil.copy2(s, d)
            # skip if unchanged
            else:
                pass

def copy_config():
    config_source = os.path.dirname(os.path.abspath(__file__)) + '/config'
    print('Attempting to copy example config to %s (origin: %s).' %
          (cfg.config_dir, config_source))
    try:
        copytree(config_source, cfg.config_dir)
    except Exception as e:  # pylint: disable=broad-except
        print(e)
        return 1

    print('Complete! Please edit the files in %s to your liking.' %
          cfg.config_dir)
    return 0


def update_geoip(target_dir):
    working_directory = os.path.join(target_dir, 'data/')
    zipped_path = os.path.join(
        working_directory, os.path.basename(MAXMIND_DOWNLOAD))
    extracted_path = os.path.join(working_directory, 'GeoLiteCity.dat')

    if not os.path.exists(target_dir):
        print('Configuration directory does not exist')
        return 1

    if not os.path.exists(working_directory):
        os.makedirs(working_directory)

    print('Downloading %s' % MAXMIND_DOWNLOAD)

    urllib.request.urlretrieve(MAXMIND_DOWNLOAD, zipped_path)

    print('Download Complete')
    print('Unpacking...')

    with gzip.open(zipped_path, 'rb') as gz:
        d = gz.read()
        with open(extracted_path, 'wb') as ex:
            ex.write(d)

    print('Unpacking Complete')
    print('Cleaning up...')

    os.remove(zipped_path)
    return 0


def main():
    if (sys.version_info.major, sys.version_info.minor) not in SUPPORTED_PYTHONS:
        print('Warning: you are running on an unsupported Python version.\n'
              'The server may not run correctly.\n'
              'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments for more information.')
    elif sys.version_info.major == 2:
        print('You are running piqueserver on Python 2.\n'
              'This will be deprecated soon and it is recommended to upgrade to Python 3.\n'
              'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments for more information.')

    description = '%s is an open-source Python server implementation ' \
                  'for the voxel-based game "Ace of Spades".' % cfg.pkg_name
    arg_parser = argparse.ArgumentParser(prog=cfg.pkg_name,
                                         description=description)

    arg_parser.add_argument('-c', '--config-file', default=None,
                            help='specify the config file - '
                                 'default is "config.json" in the config dir')

    arg_parser.add_argument('-j', '--json-parameters',
                            help='add extra json parameters '
                                 '(overrides the ones present in the config file)')

    arg_parser.add_argument('-d', '--config-dir', default=cfg.config_dir,
                            help='specify the directory which contains '
                                 'maps, scripts, etc (in correctly named '
                                 'subdirs) - default is %s' % cfg.config_path)

    arg_parser.add_argument('--copy-config', action='store_true',
                            help='copies the default/example config dir to '
                            'its default location or as specified by "-d"')

    arg_parser.add_argument('--update-geoip', action='store_true',
                            help='download the latest geoip database')

    args = arg_parser.parse_args()

    # populate the global config with values from args
    cfg.config_dir = args.config_dir

    # run the required tasks if args given
    if args.copy_config or args.update_geoip:
        if args.copy_config:
            status = copy_config()
            if status != 0:
                sys.exit(status)

        if args.update_geoip:
            status = update_geoip(cfg.config_dir)
            if status != 0:
                sys.exit(status)

        return # if we have done a task, don't run the server


    if args.config_file is None:
        cfg.config_file = os.path.join(cfg.config_dir, 'config.json')
    else:
        cfg.config_file = args.config_file

    cfg.json_parameters = args.json_parameters

    # find and load the config
    format_ = None
    if args.config_file is None:
        for format__, ext in ((TOML_FORMAT, 'toml'), (JSON_FORMAT, 'json')):
            config_file = os.path.join(cfg.config_dir, 'config.{}'.format(ext))
            format_ = format__
            if os.path.exists(config_file):
                break
    else:
        config_file = args.config_file
        ext = os.path.splitext(config_file)[1]
        if ext == '.json':
            format_ = JSON_FORMAT
        elif ext == '.toml':
            format_ = TOML_FORMAT
        else:
            raise ValueError(
                'Unsupported config file format! Must have json or toml extension.')

    print('Loading config from {!r}'.format(config_file))
    with open(config_file) as fobj:
        config.load_from_file(fobj, format_=format_)

    # update config with cli overrides
    if args.json_parameters:
        config.update_from_dict(json.loads(args.json_parameters))


    from piqueserver import server
    server.run()


if __name__ == "__main__":
    main()
