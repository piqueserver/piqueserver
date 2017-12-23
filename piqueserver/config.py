# Copyright (c) 2017 Piqueserver development team

# This file is part of piqueserver.

# piqueserver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# piqueserver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with piqueserver.  If not, see <http://www.gnu.org/licenses/>.

import json
import toml


DEFAULT_STYLE = 'TOML'
TOML_STYLE = 'TOML'
JSON_STYLE = 'JSON'


class ConfigException(Exception):
    pass


class ConfigStore():
    '''
    configuration store that manages global configuration
    '''

    def __init__(self):
        self.raw_config = {}

    def clear_config(self):
        self.raw_config = {}

    def load_config(self, config_file, style=DEFAULT_STYLE):
        self.clear_config()
        self.update_config(config_file, style)

    def update_config(self, config_file, style=DEFAULT_STYLE):
        if style == TOML_STYLE:
            self.raw_config.update(toml.load(open(config_file)))
        elif style == JSON_STYLE:
            self.raw_config.update(json.load(open(config_file)))
        else:
            raise ConfigException('Unsupported config file format: {}'.format(style))

    def load_config_object(self, config):
        self.raw_config = config

    def update_config_object(self, config):
        self.raw_config.update(config)

    def dump_config(self, out_file, style=DEFAULT_STYLE):
        if style == TOML_STYLE:
            toml.dump(self.raw_config, open(out_file, 'w'))
        elif style == JSON_STYLE:
            json.dump(self.raw_config, open(out_file, 'w'))
        else:
            raise ConfigException('Unsupported config file format: {}'.format(style))

    def get(self, name, default):
        if name not in self.raw_config:
            self.raw_config[name] = default
        return self.raw_config.get(name)

    def set(self, name, value):
        self.raw_config[name] = value

    def option(self, name, cast=None, default=None, validate=None):
        option = Option(self, name, default, cast, validate)

        return option



class Option():
    '''
    configuration option object, backed by a configuration store
    '''
    def __init__(self, store, name, default, cast, validate):
        self.store = store # ConfigStore object
        self.name = name
        self.default = default
        self.cast = cast
        self.validate = validate

    def _validate(self, value):
        if self.validate is not None:
            if not self.validate(value):
                raise ConfigException('Failed to validate {!r} config option'.format(self.name))
        return value

    def get(self):
        value = self.store.get(self.name, self.default)
        if self.cast is not None:
            return self.cast(value)
        return value

    def set(self, value):
        value = self.cast(value)
        self._validate(value)
        self.store.set(self.name, value)


config = ConfigStore()
