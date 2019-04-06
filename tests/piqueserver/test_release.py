import unittest
from piqueserver.release import format_release, check_for_releases
import asyncio
from unittest.mock import patch


class TestVersionCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def test_format_release(self):
        release = {"tag_name": "v1.0.0",
                   "published_at": "2019-04-06T13:04:26Z"}
        expected = "New release available: v1.0.0 (Apr 6 2019): https://git.io/fjIDk"
        formatted = format_release(release)
        self.assertEqual(formatted, expected)

    def test_check_for_releases(self):
        release = {"tag_name": "v100.0.0",
                   "published_at": "2040-04-06T13:04:26Z"}
        f = asyncio.Future()
        f.set_result(release)

        async def fn():
            with patch('piqueserver.release.fetch_latest_release', return_value=f):
                got = await check_for_releases()
                self.assertEqual(got, release)
        self.loop.run_until_complete(fn())

    def test_check_for_releases_none(self):
        release = {"tag_name": "v0.0.0",
                   "published_at": "2013-04-06T13:04:26Z"}
        f = asyncio.Future()
        f.set_result(release)

        async def fn():
            with patch('piqueserver.release.fetch_latest_release', return_value=f):
                got = await check_for_releases()
                self.assertEqual(got, None)
        self.loop.run_until_complete(fn())
