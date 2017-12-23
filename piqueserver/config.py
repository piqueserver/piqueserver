import toml
from pprint import pprint

class ConfigException(Exception):
    pass


class ConfigEngine():
    '''
    configuration engine that handles loading and saving config,
    and all the things
    '''
    def __init__(self):
        self.raw_config = {}
        self.style = 'TOML'

    def load_config(self, config_file, style='TOML'):
        # TODO: could also have this merge into current config if available
        self.style = style

        if style == 'TOML':
            self.raw_config = toml.load(open(config_file))
        else:
            raise Exception()

    def dump_config(self, out_file=None, style='TOML'):
        if out_file is None:
            pprint(self.raw_config)
        # TODO
        pass

    def get(self, name, default):
        # TODO: handle nested config values
        # XXX: should requesting a config value that is a dictionary object
        #       return the whole dictionary, or fail?
        return self.raw_config.get(name, default)

    def set(self, name, value):
        self.raw_config[name] = value

    def __call__(self, name, cast=None, default=None, validate=None):
        return ConfigObject(self, name, cast, default, validate)



class ConfigObject():
    '''
    configuration object stored in the engine
    '''
    def __init__(self, engine, name, cast, default, validate):
        self.name = name
        self.cast = cast
        self.default = default
        self.validate = validate
        self.engine = engine

        value = self.engine.get(name, default)
        self.value = self._cast_and_validate(value)

    def _cast_and_validate(self, value):
        if self.cast is not None:
            try:
                value = self.cast(value)
            except Exception as e:
                print(e)
                print('failed to cast config value')

        if self.validate is not None:
            ok = self.validate(value)
            if not ok:
                raise ConfigException('failed to validate')

        return value


    def get(self):
        # TODO: use getattr magic to get and set this?
        return self.value

    def set(self, value):
        # TODO: investigate possible issues with mutations if setting things like lists
        self.value = self._cast_and_validate(value)
        self.engine.set(self.name, self.value)


config = ConfigEngine()
