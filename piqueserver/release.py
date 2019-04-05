from datetime import datetime
import aiohttp
from packaging import version
from twisted.internet.task import LoopingCall
from twisted.internet.defer import ensureDeferred
from twisted.logger import Logger
from piqueserver.config import config, cast_duration
from piqueserver.version import __version__
from piqueserver.utils import as_deferred


notify = config.option("release_notifications", default=True)

log = Logger()


async def fetch_latest_release():
    endpoint = "https://api.github.com/repos/piqueserver/piqueserver/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            return await response.json()


def format_release(release) -> str:
    latest_version = release["tag_name"]
    date = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
    formated = date.strftime("%b %-d %Y")
    # git.io url points towards /latest release page
    return "New release available: {} ({}): https://git.io/fjIDk".format(latest_version, formated)


_subscribers = []


def on_new_release(func):
    _subscribers.append(func)
    return func


async def check_for_releases():
    """Checks for new releases and notifies subcribers"""

    log.debug("checking latest version")
    try:
        release = await fetch_latest_release()
    except IOError as e:
        log.warn("could not fetch latest version: {err}", err=e)
        return None

    latest_version = release["tag_name"]
    if version.parse(latest_version) > version.parse(__version__):
        for subscriber in _subscribers:
            subscriber(release)

# register default log based notifier
on_new_release(lambda release: log.info(format_release(release)))


def watch_for_releases():
    """Starts a looping for `check_for_releases` with interval of 24hrs.
     Quick exits if `release_notification` is `False`.
     """
    if not notify.get():
        return

    def f():
        return ensureDeferred(as_deferred(check_for_releases()))
    call = LoopingCall(f)
    call.start(86400)  # every day
