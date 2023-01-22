#!/usr/bin/python3
"""
usage: download_wheels.py [-h] [--ghtoken GITHUBTOKEN] [--artifactid ARTIFACTID] [--dir DIR]

Downloads wheels from Github Actions

optional arguments:
  -h, --help            show this help message and exit
  --ghtoken GITHUBTOKEN, -token GITHUBTOKEN
                        Your github token for downloading
  --artifactid ARTIFACTID, -id ARTIFACTID
                        Github artifact id
  --dir DIR, -d DIR     Directory to download the files into.
"""
from urllib.request import Request, urlopen
from urllib.parse import unquote_plus
from os import path, getcwd, remove
import argparse
import zipfile
import json

ARTIFACT_ENDPOINT = "https://api.github.com/repos/piqueserver/piqueserver/actions/artifacts"


def get_artifact(artifact_id):
    """
    Get the artifact download link. Default to the latest if no artifact_id is provided
    """
    _id = "" if not artifact_id else "/%s" % artifact_id
    endpoint = ARTIFACT_ENDPOINT+_id

    with urlopen(endpoint) as response:
        body = response.read()
        data = json.loads(body.decode("utf-8"))

        if artifact_id:
            return data["archive_download_url"]
        else:
            return data["artifacts"][0]["archive_download_url"]


def download_file(url, dir, token):
    filename = unquote_plus(url).split("/")[-2]
    file = path.join(dir, filename)

    req = Request(url)
    req.add_header("Authorization", "Bearer %s" % token)
    response = urlopen(req)

    CHUNK = 16 * 1024
    print("Downloading %s" % filename)

    with open(file, 'wb') as f:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            f.write(chunk)
    return filename


def unzip_wheels(dir, filename):
    print("Extracting %s" % filename)
    file = zipfile.ZipFile(path.join(dir, filename), 'r')
    file.extractall(dir)

    print("Deleting %s" % filename)
    remove(path.join(dir, filename))


def check_dir(dir):
    if not path.exists(dir):
        raise argparse.ArgumentTypeError(
            "Directory \"{}\" does not exist.".format(dir))
    return dir


def main():
    parser = argparse.ArgumentParser(
        description="Downloads wheels from Github Actions")
    parser.add_argument("--ghtoken", "-token",
                        default=None, help='Your github token')
    parser.add_argument("--artifactid", "-id", type=int,
                        default=None, help='Artifact id')
    parser.add_argument("--dir", "-d", type=check_dir, default=getcwd(),
                        help='Directory to download the files into.')
    options = parser.parse_args()

    download_url = get_artifact(options.artifactid)
    filename = download_file(download_url, options.dir, options.ghtoken)

    unzip_wheels(options.dir, filename)

    print("Done")


if __name__ == "__main__":
    main()
