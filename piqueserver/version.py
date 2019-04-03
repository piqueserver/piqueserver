from datetime import datetime
from packaging import version
import aiohttp
from piqueserver.config import config
from twisted.logger import Logger

__version__ = '0.1.3'
__version_info__ = (0, 1, 3)


async def fetch_latest_release():
    endpoint = "https://api.github.com/repos/piqueserver/piqueserver/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            return await response.json()


async def notify_updates():
    log = Logger()

    log.debug("checking latest version")
    try:
        release = await fetch_latest_release()
    except IOError as e:
        log.warn("could not fetch latest version: {err}", err=e)
        return None

    latest_version = release["tag_name"]
    date = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
    formated = date.strftime("%b %-d %Y")
    if version.parse(latest_version) > version.parse(__version__):
        # git.io url points towards /latest release page
        log.info("New release available: {version} ({date}): https://git.io/fjIDk",
                 version=latest_version, date=formated)
