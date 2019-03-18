#!/usr/bin/python3
"""
usage: smoke_test.py [-h] [--timeout TIMEOUT] [--config-dir CONFIG_DIR]

Basic smoke test for pique

optional arguments:
  -h, --help            show this help message and exit
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for killing the proc
  --config-dir CONFIG_DIR, -d CONFIG_DIR
                        Pique config dir

"""


import asyncio
import sys
import argparse


def printer(buffer, prefix):
    def p(data):
        buffer.write(prefix + data)
        buffer.flush()
    return p


stdoutprinter = printer(sys.stdout.buffer, b"[STDOUT]: ")
stderrprinter = printer(sys.stderr.buffer, b"[STDERR]: ")


async def _read_stream(stream, cb):
    while True:
        line = await stream.readline()
        if line:
            cb(line)
        else:
            break


async def smoketest(config_dir: str, timeout: int):
    cmd = "piqueserver -d {}".format(config_dir)
    proc = await asyncio.create_subprocess_exec(
        "piqueserver",
        "-d",
        config_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    print("Running \"{}\" (pid: {}) with timeout {} seconds.".format(
        cmd, proc.pid, timeout))
    print("-" * 10, "Output start", "-" * 10)
    asyncio.ensure_future(_read_stream(proc.stdout, stdoutprinter))
    asyncio.ensure_future(_read_stream(proc.stderr, stderrprinter))
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    print("-" * 10, "Output end", "-" * 10)
    return proc


def main():
    parser = argparse.ArgumentParser(description="Basic smoke test for pique")
    parser.add_argument("--timeout", "-t", type=int,
                        default=45, help='Timeout for killing the proc')
    parser.add_argument(
        "--config-dir",
        "-d",
        type=str,
        default="./piqueserver/config",
        help='Pique config dir')
    options = parser.parse_args()
    loop = asyncio.get_event_loop()
    proc = loop.run_until_complete(
        smoketest(options.config_dir, options.timeout))
    loop.close()
    if proc.returncode is None:
        print("Smoke test passed.")
        proc.kill()
    else:
        print("Smoke test failed. Exit code: ", proc.returncode)
    sys.exit(proc.returncode or 0)


if __name__ == "__main__":
    main()
