from twisted.trial import unittest
from unittest.mock import Mock

from piqueserver import statusserver

class StatusSeverTest(unittest.TestCase):
    def test_json(self):
        statusserver.JSONPage(Mock())
        # TODO: actually simulate HTTP request
