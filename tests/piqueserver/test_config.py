import unittest
from piqueserver.config import config, JSON_STYLE, TOML_STYLE


class TestExampleConfig(unittest.TestCase):

    def test_simple(self):
        f = 'tests/example_config/simple.toml'
        config.load_from_file(open(f))

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
        f = 'tests/example_config/simple.toml'
        config.load_from_file(open(f))

        bounded = config.option('testboundednumber', cast=int,
                                validate=lambda n: 0 < n < 11, default=5)

        with self.assertRaises(ValueError):
            bounded.set(30)

        self.assertEqual(bounded.get(), 5)

        bounded.set(6)
        self.assertEqual(bounded.get(), 6)

    def test_get(self):
        f = 'tests/example_config/simple.toml'
        test = config.option('testthing')
        config.load_from_file(open(f))

        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), None)

        test.set('something')

        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), 'something')

    def test_nested(self):
        f = 'tests/example_config/simple.toml'
        config.load_from_file(open(f))

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
        f = 'tests/example_config/simple.toml'
        config.load_from_file(open(f))

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
        f = 'tests/example_config/simple.toml'

        with self.assertRaises(ValueError):
            config.load_from_file(open(f), style='aoeuaoeu')

        with self.assertRaises(ValueError):
            config.load_from_file(open(f), style=JSON_STYLE)

    def test_json(self):
        f = 'piqueserver/config/config.json'
        config.load_from_file(open(f), style=JSON_STYLE)

        # "name" : "piqueserver instance",
        name = config.option('name')
        self.assertEqual(name.get(), 'piqueserver instance')

    def test_more_nested(self):
        f = 'tests/example_config/simple.toml'
        config.load_from_file(open(f))

        server_config = config.section('server')
        port = server_config.option('port')
        self.assertEqual(port.get(), 4567)

        thing_config = server_config.section('things')
        self.assertEqual(thing_config.option('thing1').get(), 'something')

        thing2 = thing_config.option('thing2')
        thing2.set('something else')

        self.assertEqual(thing_config.get_dict(), {'thing1': 'something', 'thing2': 'something else'})
