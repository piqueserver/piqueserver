#!/usr/bin/python3
"""
This script downloads wheels from appveyor.
Usage:
python download_wheels.py <build_id>
when build_id is not provided it defaults to latest build.

"""
import argparse
from urllib import request
import json
from urllib.parse import quote_plus, unquote_plus
from os import path, getcwd
from sys import argv
from multiprocessing.pool import Pool

PROJECT_ENDPOINT = "https://ci.appveyor.com/api/projects/piqueserver/piqueserver"
BUILDS_ENDPOINT = "https://ci.appveyor.com/api/projects/piqueserver/piqueserver/builds/{buildid}"
ARTIFACT_ENDPOINT = "https://ci.appveyor.com/api/buildjobs/{jobid}/artifacts"


def get_jobs(build_id=None):
    """
    Fetches job objects. Defaults to latest build if no build_id is provided.
    """
    if build_id:
        endpoint = BUILDS_ENDPOINT.format(buildid=build_id)
    else:
        print("Build ID not provided defaulting to lastest build.")
        endpoint = PROJECT_ENDPOINT
    with request.urlopen(endpoint) as response:
        body = response.read()
        data = json.loads(body.decode("utf-8"))
        jobs = data['build']['jobs']
        return list(filter(lambda job: job["status"] == "success", jobs))


def get_artifacts(job):
    """
    Fetches list of artifacts from the job. It discards all files other than *.whl
    """
    endpoint = ARTIFACT_ENDPOINT.format(jobid=job["jobId"])
    with request.urlopen(endpoint) as response:
        body = response.read()
        artifacts = json.loads(body.decode("utf-8"))
        cleaned = []
        for artifact in artifacts:
            # discards non-wheel files
            if ".whl" in artifact["fileName"]:
                # makes a download loadable url like so:
                # https://ci.appveyor.com/api/buildjobs/976y8r0sxscgvae9/artifacts/dist%2Fpiqueserver-0.1.3-cp36-cp36m-win_amd64.whl
                cleaned.append(endpoint + '/' +
                               quote_plus(artifact["fileName"]))
        return cleaned


def download_file(url, dir):
    # unescape '/', split by '/', get last fragment i.e filename
    filename = unquote_plus(url).split("/")[-1]
    file = path.join(dir, filename)
    response = request.urlopen(url)
    CHUNK = 16 * 1024
    print("Downloading {}".format(filename))
    with open(file, 'wb') as f:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            f.write(chunk)
    return filename


def check_dir(dir):
    if not path.exists(dir):
        raise argparse.ArgumentTypeError(
            "Directory \"{}\" does not exist.".format(dir))
    return dir


def main():
    parser = argparse.ArgumentParser(
        description="Downloads wheels from AppVeyor")
    parser.add_argument("--buildid", "-id", type=int,
                        default=None, help='AppVeyor build id')
    parser.add_argument("--pool", "-p", type=int, default=6,
                        help="Multiprocess pool size")
    parser.add_argument("--dir", "-d", type=check_dir, default=getcwd(),
                        help='Directory to download the files into.')
    options = parser.parse_args()

    download_urls = []
    for job in get_jobs(options.buildid):
        download_urls += get_artifacts(job)
    # Download them in parallel
    pool = Pool(options.pool)
    for download_url in download_urls:
        pool.apply_async(download_file, args=(download_url, options.dir))
    pool.close()
    pool.join()
    print("Done")


if __name__ == "__main__":
    main()
