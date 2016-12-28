#!/usr/bin/env python2

import os
import urllib
import gzip

MAXMIND_DOWNLOAD = "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz"

WORKING_DIRECTORY = "data"

ZIPPED_PATH = os.path.join(
    WORKING_DIRECTORY, os.path.basename(MAXMIND_DOWNLOAD))
EXTRACTED_PATH = os.path.join(WORKING_DIRECTORY, "GeoLiteCity.dat")


def download_geoip_db():
    urllib.urlretrieve(MAXMIND_DOWNLOAD, ZIPPED_PATH)


def extract_geoip_db():
    with gzip.open(ZIPPED_PATH, "rb") as gz:
        d = gz.read()
        with open(EXTRACTED_PATH, "wb") as ex:
            ex.write(d)

if __name__ == '__main__':

    if not os.path.exists(WORKING_DIRECTORY):
        os.makedirs(WORKING_DIRECTORY)

    print "Downloading %s" % MAXMIND_DOWNLOAD

    download_geoip_db()

    print "Download Complete"
    print "Unpacking..."

    extract_geoip_db()

    print "Unpacking Complete"
    print "Cleaning up..."

    os.remove(ZIPPED_PATH)
