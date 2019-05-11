from datetime import datetime
from typing import Optional, Dict, Any
from twisted.logger import Logger
import aiohttp
from packaging import version
from piqueserver.version import __version__


log = Logger()


async def fetch_latest_release() -> Dict[str, Any]:
    endpoint = "https://api.github.com/repos/piqueserver/piqueserver/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            return await response.json()


def format_release(release: Dict[str, Any]) -> str:
    latest_version = release["tag_name"]
    date = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
    formated = date.strftime("%b %d %Y")
    # git.io url points towards /latest release page
    return "New release available: {} ({}): https://git.io/fjIDk".format(latest_version, formated)


async def check_for_releases() -> Optional[Dict[str, Any]]:
    """Checks for new release and returns it if new release is found."""

    log.debug("checking latest version")
    try:
        release = await fetch_latest_release()
    except IOError as e:
        log.warn("could not fetch latest version: {err}", err=e)
        return None

    latest_version = release["tag_name"]
    if version.parse(latest_version) > version.parse(__version__):
        return release
    return None
