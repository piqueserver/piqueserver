import unittest
from piqueserver.config import config, ConfigException


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

    def test_get(self):
        f = 'tests/example_config/simple.toml'
        test = config.option('testthing')
        config.load_config(f)


        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), None)

        test.set('something')

        self.assertEqual(test.get(), test.value)
        self.assertEqual(test.get(), 'something')
