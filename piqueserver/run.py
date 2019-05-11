
import os
import filecmp
import shutil
import sys
import argparse
import tarfile
import json

from piqueserver.config import (config, TOML_FORMAT, JSON_FORMAT,
                                MAXMIND_DOWNLOAD, MAXMIND_DOWNLOAD_MD5,
                                SUPPORTED_PYTHONS)
import urllib.request
import hashlib

PKG_NAME = 'piqueserver'

def get_git_rev():
    if not os.path.exists(".git"):
        return 'snapshot'

    from distutils.spawn import find_executable
    if find_executable("git") is None:
        return 'gitless'

    import subprocess
    pipe = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
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
    os.makedirs(dst, exist_ok=True)
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
          (config.config_dir, config_source))
    try:
        copytree(config_source, config.config_dir)
    except Exception as e:  # pylint: disable=broad-except
        print(e)
        return 1

    print('Complete! Please edit the files in %s to your liking.' %
          config.config_dir)
    return 0


def update_geoip(target_dir):
    db_filename = 'GeoLite2-City.mmdb'
    working_directory = os.path.join(target_dir, 'data/')
    zipped_path = os.path.join(working_directory,
                               os.path.basename(MAXMIND_DOWNLOAD))
    extracted_path = os.path.join(working_directory, db_filename)

    if not os.path.exists(target_dir):
        print('Configuration directory does not exist')
        return 1

    os.makedirs(working_directory, exist_ok=True)

    print('Downloading %s' % MAXMIND_DOWNLOAD)
    file_data = urllib.request.urlopen(MAXMIND_DOWNLOAD).read()

    print('Downloading %s' % MAXMIND_DOWNLOAD_MD5)
    sum_data = urllib.request.urlopen(MAXMIND_DOWNLOAD_MD5).read()
    print('Download Complete')

    # Both files are downloaded, but not stored before integrity check
    print('Checking integrity...')
    downloaded_sum = sum_data.decode()
    calculated_sum = hashlib.md5(file_data).hexdigest()
    if calculated_sum != downloaded_sum:
        print('md5 sums do not match')
        return 1

    print('OK')
    print('Saving file...')
    with open(zipped_path, 'wb') as f:
        f.write(file_data)

    print('Unpacking...')
    with tarfile.open(zipped_path, 'r:gz') as tar:
        comp_path = os.path.join(tar.next().name, db_filename)
        db = tar.extractfile(comp_path)
        with open(extracted_path, 'wb') as ex:
            ex.write(db.read())

    print('Unpacking Complete')

    print('Cleaning up...')
    os.remove(zipped_path)

    return 0


def main():
    if (sys.version_info.major, sys.version_info.minor) not in SUPPORTED_PYTHONS:
        print('Warning: you are running on an unsupported Python version.\n'
              'The server may not run correctly.\n'
              'Please see https://piqueserver.readthedocs.io/en/v1.0.0/supported-python-environments.html for more information.')

    description = '%s is an open-source Python server implementation ' \
                  'for the voxel-based game "Ace of Spades".' % PKG_NAME
    arg_parser = argparse.ArgumentParser(
        prog=PKG_NAME, description=description)

    arg_parser.add_argument(
        '-c',
        '--config-file',
        default=None,
        help='specify the config file - '
        'default is "config.toml" in the config dir')

    arg_parser.add_argument(
        '-j',
        '--json-parameters',
        help='add extra settings in json format '
        '(overrides the config present in the config file)')

    arg_parser.add_argument(
        '-d',
        '--config-dir',
        default=config.config_dir,
        help='specify the directory which contains '
        'maps, scripts, etc (in correctly named '
        'subdirs) - default is %s' % config.config_dir)

    arg_parser.add_argument(
        '--copy-config',
        action='store_true',
        help='copies the default/example config dir to '
        'its default location or as specified by "-d"')

    arg_parser.add_argument(
        '--update-geoip',
        action='store_true',
        help='download the latest geoip database')

    arg_parser.add_argument(
        '--version',
        action='store_true',
        help='show the version and exit')

    args = arg_parser.parse_args()

    # update the config_dir from cli args
    config.config_dir = args.config_dir

    # run the required tasks if args given
    if args.copy_config or args.update_geoip:
        if args.copy_config:
            status = copy_config()
            if status != 0:
                sys.exit(status)

        if args.update_geoip:
            status = update_geoip(config.config_dir)
            if status != 0:
                sys.exit(status)

        return  # if we have done a task, don't run the server

    if args.version:
        import piqueserver
        print("piqueserver", piqueserver.__version__)
        return

    # TODO: set config/map/script/log/etc. dirs from config file, thus removing
    # the need for the --config-dir argument and the config file is then a
    # single source of configuration

    # find and load the config
    # search order:
    # - --config-file (must have toml or json file extension)
    # - --config-dir/config.toml
    # - --config-dir/config.json
    # - ~/.config/piqueserver/config.toml
    # - ~/.config/piqueserver/config.json
    format_ = None
    if args.config_file is None:
        for format__, ext in ((TOML_FORMAT, 'toml'), (JSON_FORMAT, 'json')):
            config_file = os.path.join(config.config_dir,
                                       'config.{}'.format(ext))
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
                'Unsupported config file format! Must have json or toml extension.'
            )

    config.config_file = config_file
    print('Loading config from {!r}'.format(config_file))
    try:
        with open(config_file) as fobj:
            config.load_from_file(fobj, format_=format_)
    except FileNotFoundError as e:
        print("Could not open Config file")
        print(e)
        return e.errno

    # update config with cli overrides
    if args.json_parameters:
        config.update_from_dict(json.loads(args.json_parameters))
    # We need to install the asyncio reactor before 
    # we add any imports like `twisted.internet.*` which install the default reactor.
    # We keep it here and not at package level to avoid installing the reactor more than once.
    # Twisted throws an exception if you install the reactor more than once.
    import asyncio
    from twisted.internet import asyncioreactor
    asyncioreactor.install(asyncio.get_event_loop())

    from piqueserver import server
    server.run()


if __name__ == "__main__":
    main()
