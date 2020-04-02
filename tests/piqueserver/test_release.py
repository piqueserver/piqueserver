import pytest
import unittest
from piqueserver.release import format_release, check_for_releases
import asyncio
from unittest.mock import patch, MagicMock


class TestVersionCheck(unittest.TestCase):
    def test_format_release(self):
        release = {"tag_name": "v1.0.0",
                   "published_at": "2019-04-06T13:04:26Z"}
        expected = "New release available: v1.0.0 (Apr 06 2019): https://git.io/fjIDk"
        formatted = format_release(release)
        self.assertEqual(formatted, expected)

    @pytest.mark.asyncio
    async def test_check_for_releases(self):
        release = {"tag_name": "v100.0.0",
                   "published_at": "2040-04-06T13:04:26Z"}
        f = asyncio.Future()
        f.set_result(release)

        # python3.8+ uses AsyncMock for mocking async functions. Force MagicMock
        # until we can rely on that behaviour.
        with patch('piqueserver.release.fetch_latest_release', return_value=f,
                   new_callable=MagicMock):
            got = await check_for_releases()
            assert got == release

    @pytest.mark.asyncio
    async def test_check_for_releases_none(self):
        release = {"tag_name": "v0.0.0",
                   "published_at": "2013-04-06T13:04:26Z"}
        f = asyncio.Future()
        f.set_result(release)

        # python3.8+ uses AsyncMock for mocking async functions. Force MagicMock
        # until we can rely on that behaviour.
        with patch('piqueserver.release.fetch_latest_release', return_value=f,
                   new_callable=MagicMock):
            got = await check_for_releases()
            assert got == None
