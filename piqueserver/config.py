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


class ConfigStore():
    '''
    configuration store that manages global configuration
    '''

    def __init__(self):
        self._raw_config = {}
        self.options = {}

    def _validate_all(self):
        for option in self.options.values():
            option.validate(option.get())

    def get_dict(self):
        return self._raw_config

    def load_from_file(self, fobj, style=DEFAULT_STYLE):
        '''
        clear the current configuration and load new configuration from a file like object
        in a supported format
        '''
        self._raw_config = {}
        self.update_from_file(fobj, style)

    def update_from_file(self, fobj, style=DEFAULT_STYLE):
        d = {}
        if style == TOML_STYLE:
            d = toml.load(fobj)
        elif style == JSON_STYLE:
            d = json.load(fobj)
        else:
            raise ValueError('Unsupported config file format: {}'.format(style))
        self.update_from_dict(d)

    def load_from_dict(self, config):
        self._raw_config = {}
        self.update_from_dict(config)

    def update_from_dict(self, config):
        self._raw_config.update(config)
        self._validate_all()

    def dump(self, out_file, style=DEFAULT_STYLE):
        if style == TOML_STYLE:
            toml.dump(self._raw_config, open(out_file, 'w'))
        elif style == JSON_STYLE:
            json.dump(self._raw_config, open(out_file, 'w'))
        else:
            raise ValueError('Unsupported config file format: {}'.format(style))

    def get(self, name, default=None, section=None):
        if section:
            if section not in self._raw_config:
                self._raw_config[section] = {}
                self._raw_config[section][name] = default
            return self._raw_config[section][name]
        else:
            if name not in self._raw_config:
                self._raw_config[name] = default
            return self._raw_config[name]


    def set(self, name, value, section=None):
        if section:
            if section not in self._raw_config:
                self._raw_config[section] = {}
            self._raw_config[section][name] = value
        else:
            self._raw_config[name] = value

    def option(self, name, section=None, cast=None, default=None, validate=None):
        option = Option(self, name, section, default, cast, validate)
        self.options[(section, name)] = option

        return option



class Option():
    '''
    configuration option object, backed by a configuration store
    '''
    def __init__(self, store, name, section, default, cast, validate):
        self.store = store # ConfigStore object
        self.name = name
        self.section = section
        self.default = default
        self.cast = cast
        self.validate_func = validate

        self.validate(self.get())


    def validate(self, value):
        if self.validate_func is not None:
            if not self.validate_func(value):
                raise ValueError('Failed to validate {!r} config option'.format(self.name))
        return value

    def get(self):
        value = self.store.get(self.name, self.default, self.section)
        if self.cast is not None:
            return self.cast(value)
        return value

    def set(self, value):
        if self.cast is not None:
            value = self.cast(value)
        self.validate(value)
        self.store.set(self.name, value, self.section)

    @property
    def value(self):
        return self.get()


config = ConfigStore()
