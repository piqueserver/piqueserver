
from __future__ import print_function
import os
import shutil
import sys
import argparse
import urllib
import gzip

import cfg


def copy_config():
    config_source = os.path.dirname(os.path.abspath(__file__)) + '/config'
    print('Attempting to copy example config to %s (origin: %s).' % (cfg.config_dir, config_source))
    try:
        shutil.copytree(config_source, cfg.config_dir)
    except Exception as e:
        print(e)
        sys.exit(1)

    print('Complete! Please edit the files in %s to your liking.' % cfg.config_dir)


def update_geoip(target_dir):
    MAXMIND_DOWNLOAD = 'http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz'
    WORKING_DIRECTORY = os.path.join(target_dir, 'data/')
    ZIPPED_PATH = os.path.join(
        WORKING_DIRECTORY, os.path.basename(MAXMIND_DOWNLOAD))
    EXTRACTED_PATH = os.path.join(WORKING_DIRECTORY, 'GeoLiteCity.dat')


    if not os.path.exists(target_dir):
        print('Configuration directory does not exist')
        sys.exit(1)

    if not os.path.exists(WORKING_DIRECTORY):
        os.makedirs(WORKING_DIRECTORY)

    print('Downloading %s' % MAXMIND_DOWNLOAD)

    urllib.urlretrieve(MAXMIND_DOWNLOAD, ZIPPED_PATH)

    print('Download Complete')
    print('Unpacking...')

    with gzip.open(ZIPPED_PATH, 'rb') as gz:
        d = gz.read()
        with open(EXTRACTED_PATH, 'wb') as ex:
            ex.write(d)

    print('Unpacking Complete')
    print('Cleaning up...')

    os.remove(ZIPPED_PATH)


def run_server():
    import server
    server.run()


def main():
    arg_parser = argparse.ArgumentParser(prog=cfg.pkg_name,
                                         description='%s is an open-source Python server implementation for the voxel-based game "Ace of Spades".' % cfg.pkg_name)

    arg_parser.add_argument('-c', '--config-file', default='config.json',
            help='specify the config file (relative to config dir if relative path) - default is "config.json"')
    arg_parser.add_argument('-j', '--json-parameters',
            help='add extra json parameters (overrides the ones present in the config file)')
    arg_parser.add_argument('-d', '--config-dir', default=cfg.config_dir,
            help='specify the directory which contains maps, scripts, etc (in correctly named subdirs) - default is %s' % cfg.config_path)
    arg_parser.add_argument('--copy-config', action='store_true', help='copies the default/example config dir to its default location or as specified by "-d"')
    arg_parser.add_argument('--update-geoip', action='store_true', help='download the latest geoip database')

    args = arg_parser.parse_args()

    # populate the global config with values from args
    cfg.config_dir = args.config_dir
    cfg.config_file = args.config_file
    cfg.json_parameters = args.json_parameters

    run = True

    # copy config and update geoip can happen at the same time
    # note that sys.exit is called from either of these functions on failure
    if args.copy_config:
        copy_config()
        run = False
    if args.update_geoip:
        update_geoip(cfg.config_dir)
        run = False

    # only run the server if other tasks weren't performed
    if run:
        run_server()
