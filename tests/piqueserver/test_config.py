import tempfile
from pprint import pprint

import unittest
from piqueserver.config import ConfigStore, JSON_FORMAT, TOML_FORMAT, cast_duration
from io import StringIO

SIMPLE_TOML_CONFIG = u"""
title = "something"
testnumber = 42

[server]
name = "piqueserver instance"
game_mode = "ctf"
port = 4567

[passwords]
admin = ["adminpass1", "adminpass2", "adminpass3"]
moderator = ["modpass"]

[squad]
respawn_time = 32
size = 5

[server.things]
thing1 = "something"
"""


class TestExampleConfig(unittest.TestCase):

    def test_simple(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        gravity = config.option('gravity', cast=bool, default=True)
        self.assertEqual(gravity.get(), True)

        gravity.set(False)
        self.assertEqual(gravity.get(), False)

        title = config.option('title', default=None)
        self.assertEqual(title.get(), 'something')

        n = config.option('testnumber', cast=int, default=None)
        self.assertEqual(n.get(), 42)

        s = config.option('testnumber', cast=str, default=None)
        self.assertEqual(s.get(), '42')

    def test_validation(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        bounded = config.option('testboundednumber', cast=int,
                                validate=lambda n: 0 < n < 11, default=5)

        with self.assertRaises(ValueError):
            bounded.set(30)

        self.assertEqual(bounded.get(), 5)

        bounded.set(6)
        self.assertEqual(bounded.get(), 6)

    def test_get(self):
        config = ConfigStore()
        test = config.option('testthing')
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        self.assertEqual(test.get(), None)

        test.set('something')

        self.assertEqual(test.get(), 'something')

    def test_nested(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        server_config = config.section('server')
        port = server_config.option('port')
        self.assertEqual(port.get(), 4567)

        lol = config.section('lol')
        test = lol.option('nonexistant', default='hi')
        self.assertEqual(test.get(), 'hi')

        raw = config.get_dict()

        self.assertEqual(raw['server']['port'], 4567)
        self.assertEqual(raw['lol']['nonexistant'], 'hi')

        raw = server_config.get_dict()
        self.assertEqual(raw['port'], 4567)
        self.assertEqual(raw['name'], 'piqueserver instance')

        server_config.update_from_dict({'port': 1})
        raw = server_config.get_dict()
        self.assertEqual(raw['port'], 1)
        self.assertEqual(raw['name'], 'piqueserver instance')

        server_config.load_from_dict({'port': 1})
        self.assertEqual(server_config.get_dict(), {'port': 1})
        self.assertEqual(test.get(), 'hi')

    def test_reload(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        server_config = config.section('server')
        port = server_config.option('port', default=32887)
        self.assertEqual(port.get(), 4567)

        config.load_from_dict({})
        self.assertEqual(port.get(), 32887)
        port.set(456)
        self.assertEqual(port.get(), 456)

        config.load_from_dict({})
        port.set(5555)
        self.assertEqual(port.get(), 5555)

    def test_raw_loading(self):
        config = ConfigStore()
        config.load_from_dict({})
        name = config.option('name')
        port = config.section('server').option('port')

        obj = {'server': {'port': 4567}, 'name': 'thing'}
        config.load_from_dict(obj)
        self.assertEqual(name.get(), 'thing')

        obj = {'server': {'port': 42}}
        config.update_from_dict(obj)
        self.assertEqual(port.get(), 42)
        self.assertEqual(name.get(), 'thing')

        obj = {'server': {'port': 4567}, 'name': 'thing'}
        config.load_from_dict(obj)
        self.assertEqual(port.get(), 4567)
        self.assertEqual(name.get(), 'thing')

    def test_fail_load(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)

        with self.assertRaises(ValueError):
            config.load_from_file(f, format_='aoeuaoeu')

        with self.assertRaises(ValueError):
            config.load_from_file(f, format_=JSON_FORMAT)

    def test_json(self):
        config = ConfigStore()
        f = StringIO(u'''
        {
            "name": "piqueserver instance"
        }
        ''')
        config.load_from_file(f, format_=JSON_FORMAT)

    def test_more_nested(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        server_config = config.section('server')
        port = server_config.option('port')
        self.assertEqual(port.get(), 4567)

        thing_config = server_config.section('things')
        self.assertEqual(thing_config.option('thing1').get(), 'something')

        thing2 = thing_config.option('thing2')
        thing2.set('something else')

        self.assertEqual(thing_config.get_dict(), {'thing1': 'something', 'thing2': 'something else'})

    def test_nested_update(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        updates = {
                'server': {
                    'things': {
                        'thing2': 'added'
                        }
                    }
                }

        config.update_from_dict(updates)

        raw = config.get_dict()

        self.assertEqual(raw['server']['things']['thing1'], 'something')
        self.assertEqual(raw['server']['things']['thing2'], 'added')
        self.assertEqual(raw['server']['name'], 'piqueserver instance')

    def test_dump_to_file(self):
        config = ConfigStore()
        f = StringIO(SIMPLE_TOML_CONFIG)
        config.load_from_file(f)

        with self.assertRaises(ValueError):
            config.dump_to_file(None, format_='garbage123')

        with tempfile.TemporaryFile(mode='w+') as f:
            config.dump_to_file(f, JSON_FORMAT)
            f.seek(0)
            out = f.read().strip()
            # at least make sure it wrote something that could be json
            self.assertEqual(out[0], '{')
            self.assertEqual(out[-1], '}')

        with tempfile.TemporaryFile(mode='w+') as f:
            config.dump_to_file(f, TOML_FORMAT)
            f.seek(0)
            out = f.read().strip()
            # at least make sure it wrote something that could be toml
            self.assertIn('[server]', out)

    def test_check_unused(self):
        config = ConfigStore()
        d = {
                'server': {
                    'name': 'wat',
                    'unreg1': 'nothing',
                    },
                'unreg2': {
                    'unreg3': 'should not be warned about'
                    }
                }
        config.load_from_dict(d)

        server_config = config.section('server')
        name = server_config.option('name')

        one = config.check_unused()
        two = {
                'server': {
                    'unreg1': 'nothing',
                    },
                'unreg2': {
                    'unreg3': 'should not be warned about'
                    }
                }
        self.assertEqual(one, two)


class TestCasts(unittest.TestCase):
    def test_duration_cast(self):
        test_cases = [
            {
                "name": "Direct seconds",
                "input": 10,
                "expect": 10
            },
            {
                "name": "Duration",
                "input": "10sec",
                "expect": 10
            },
            {
                "name": "Invalid type",
                "input": [],
                "ex": ValueError
            },
            {
                "name": "Invalid Duration",
                "input": "1dia",
                "ex": ValueError
            }
        ]
        for case in test_cases:
            if "ex" in case:
                with self.assertRaises(case["ex"]):
                    cast_duration(case["input"])
                continue
            got = cast_duration(case["input"])
            self.assertEqual(got, case["expect"])