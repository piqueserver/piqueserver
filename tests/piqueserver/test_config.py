import unittest
from piqueserver.config import config, ConfigException, JSON_STYLE, TOML_STYLE
from json import JSONDecodeError


class TestExampleConfig(unittest.TestCase):

    def test_simple(self):
        f = 'tests/example_config/simple.toml'
        config.load_config(f)

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
        config.load_config(f)

        bounded = config.option('testboundednumber', cast=int, validate=lambda n:0<n<11, default=5)

        with self.assertRaises(ConfigException):
            bounded.set(30)

        self.assertEqual(bounded.get(), 5)

        bounded.set(6)
        self.assertEqual(bounded.get(), 6)



    def test_get(self):
        f = 'tests/example_config/simple.toml'
        test = config.option('testthing')
        config.load_config(f)


        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), None)

        test.set('something')

        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), 'something')

    def test_nested(self):
        f = 'tests/example_config/simple.toml'
        config.load_config(f)

        port = config.option('port', section='server')
        self.assertEqual(port.get(), 4567)

        test = config.option('nonexistant', section='lol', default='hi')
        self.assertEqual(test.get(), 'hi')

        raw = config.get_raw_config()

        self.assertEqual(raw['server']['port'], 4567)
        self.assertEqual(raw['lol']['nonexistant'], 'hi')

    def test_reload(self):
        f = 'tests/example_config/simple.toml'
        config.load_config(f)

        port = config.option('port', section='server', default=32887)
        self.assertEqual(port.get(), 4567)

        config.clear_config()
        self.assertEqual(port.get(), 32887)
        port.set(456)
        self.assertEqual(port.get(), 456)


        config.clear_config()
        port.set(5555)
        self.assertEqual(port.get(), 5555)

    def test_raw_loading(self):
        config.clear_config()
        name = config.option('name')
        port = config.option('port', section='server')

        obj = {'server':{'port': 4567}, 'name': 'thing'}
        config.load_config_object(obj)
        self.assertEqual(name.get(), 'thing')

        obj = {'server':{'port': 42}}
        config.update_config_object(obj)
        self.assertEqual(port.get(), 42)
        self.assertEqual(name.get(), 'thing')

        obj = {'server':{'port': 4567}, 'name': 'thing'}
        config.load_config_object(obj)
        self.assertEqual(port.get(), 4567)
        self.assertEqual(name.get(), 'thing')

    def test_fail_load(self):
        f = 'tests/example_config/simple.toml'

        with self.assertRaises(ConfigException):
            config.load_config(f, style='aoeuaoeu')

        with self.assertRaises(JSONDecodeError):
            config.load_config(f, style=JSON_STYLE)

    def test_json(self):
        f = 'piqueserver/config/config.json'
        config.load_config(f, style=JSON_STYLE)

        # "name" : "piqueserver instance",
        name = config.option('name')
        self.assertEqual(name.get(), 'piqueserver instance')
