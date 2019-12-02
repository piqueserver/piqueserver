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

import collections
import json
import os
import sys

import piqueserver
import toml
from piqueserver.utils import timeparse

# supported config format constants to avoid typos
DEFAULT_FORMAT = 'TOML'
TOML_FORMAT = 'TOML'
JSON_FORMAT = 'JSON'

# global constants we need to know at the start
_path = os.environ.get('XDG_CONFIG_HOME', '~/.config') + '/piqueserver'
DEFAULT_CONFIG_DIR = os.path.expanduser(_path)
MAXMIND_DOWNLOAD = 'https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz'
MAXMIND_DOWNLOAD_MD5 = MAXMIND_DOWNLOAD + '.md5'

# (major, minor) versions of python we are supporting
# used on startup to emit a warning if not running on a supported version
SUPPORTED_PYTHONS = ((3, 5), (3, 6), (3, 7), (3, 8))


class ConfigStore():
    '''
    Configuration store that manages global configuration.

    Usage example:

    >>> config = ConfigStore()
    >>> config.load_from_dict({'key1': 'value1'})

    >>> option1 = config.option('key1', default='nothing',
    ...                         validate=lambda x: len(x) > 0)
    >>> section1 = config.section('section1')
    >>> nested_option = section1.option('key1', default=0)

    >>> print(nested_option.get())
    >>> option1.set('hello')

    >>> # underlying dictionary structure will look like
    >>> # {
    >>> #   'key1': 'hello',
    >>> #   'section1': {
    >>> #     'key1': 0
    >>> #   }
    >>> # }
    '''

    def __init__(self):
        self._raw_config = {}
        self._options = {}
        self._sections = {}

        # these are for config that isn't ever stored in the config file (yet)
        self.config_dir = DEFAULT_CONFIG_DIR
        self.config_file = os.path.join(DEFAULT_CONFIG_DIR, "config.toml")

    def _validate_all(self):
        for option in self._options.values():
            option._validate(option.get())
        for section in self._sections.values():
            section._validate_all()

    # https://stackoverflow.com/a/3233356/
    def _nested_update(self, config_dict, updates):
        for k, v in updates.items():
            if isinstance(v, collections.Mapping):
                config_dict[k] = self._nested_update(config_dict.get(k, {}), v)
            else:
                config_dict[k] = v
        return config_dict

    def get_dict(self):
        return self._raw_config

    def load_from_file(self, fobj, format_=DEFAULT_FORMAT):
        '''
        Clear the current configuration and load new configuration from a file-like object
        in a supported format.
        '''
        self._raw_config = {}
        self.update_from_file(fobj, format_)

    def update_from_file(self, fobj, format_=DEFAULT_FORMAT):
        '''
        Updates the configuration from a file-like object. Useful for
        overwriting/updating part of the config without touching the rest.
        '''
        d = {}
        if format_ == TOML_FORMAT:
            d = toml.load(fobj)
        elif format_ == JSON_FORMAT:
            d = json.load(fobj)
        else:
            raise ValueError(
                'Unsupported config file format: {}'.format(format_))
        self.update_from_dict(d)

    def load_from_dict(self, config):
        '''
        Load from a dictionary object directly.
        '''
        self._raw_config = {}
        self.update_from_dict(config)

    def update_from_dict(self, config):
        '''
        Load from a dictionary object directly.
        '''
        self._raw_config = self._nested_update(self._raw_config, config)
        self._validate_all()

    def dump_to_file(self, fobj, format_=DEFAULT_FORMAT):
        '''
        Writes the current configuration to a file-like objection,
        with the format specified by `format_`.
        '''
        if format_ == TOML_FORMAT:
            toml.dump(self._raw_config, fobj)
        elif format_ == JSON_FORMAT:
            json.dump(self._raw_config, fobj, indent=2)
        else:
            raise ValueError(
                'Unsupported config file format: {}'.format(format_))

    def _get(self, name, default=None):
        if name not in self._raw_config:
            self._raw_config[name] = default
        return self._raw_config[name]

    def _set(self, name, value):
        self._raw_config[name] = value

    def check_unused(self):
        '''
        Return the subset of the underlying dictionary that doesn't have any
        corresponding registered options.
        '''

        unused = {}
        for k, v in self.get_dict().items():
            if isinstance(v, collections.Mapping):
                if k in self._sections:
                    section_unused = self._sections[k].check_unused()
                    if section_unused:
                        unused[k] = section_unused
                else:
                    if k not in self._options:
                        unused[k] = v
            else:
                if k not in self._options:
                    unused[k] = v

        return unused

    def option(self, name, default=None, cast=None, validate=None):
        '''
        Register and return a new option object.
        '''
        # TODO: how to handle same option defined twice?
        option = _Option(self, name, default, cast, validate)
        self._options[name] = option
        return option

    def section(self, name):
        '''
        Register and return a new section object.
        '''
        if name in self._sections:
            return self._sections[name]

        section = _Section(self, name)
        self._sections[name] = section
        return section


class _Section(ConfigStore):
    '''
    Represents a section of a configstore. Can be nested arbitarily.
    '''

    def __init__(self, store, name):
        self._store = store
        self._name = name
        self._sections = {}
        self._options = {}

    def get_dict(self):
        return self._store.get_dict().get(self._name, {})

    def load_from_file(self, fobj, format_=DEFAULT_FORMAT):
        raise NotImplementedError()

    def update_from_file(self, fobj, format_=DEFAULT_FORMAT):
        raise NotImplementedError()

    def load_from_dict(self, config):
        self._store._set(self._name, config)

    def update_from_dict(self, config):
        d = self._store._get(self._name, {})
        d.update(config)
        self._store._set(self._name, d)

    def dump_to_file(self, fobj, format_=DEFAULT_FORMAT):
        raise NotImplementedError()

    def _get(self, name, default):
        section = self._store._get(self._name, {})
        if name not in section:
            section[name] = default
            self._store._set(self._name, section)
        return section[name]

    def _set(self, name, value):
        section = self._store._get(self._name, {})
        section[name] = value
        self._store._set(self._name, section)


class _Option():
    '''
    configuration option object, backed by a configuration store
    '''

    def __init__(self, store, name, default, cast, validate):
        '''
        store: a ConfigStore or Section object. Must provide `get()` and `set(value)` methods
        name: the option name (corresponding to the dictionary key for the section/store)
        cast: a transformation function that will be called whenever you retrieve the option's value.
        validate: a function that takes the casted value and should return bool indicating whether it is a valid value
        '''
        self._store = store  # ConfigStore object
        self._name = name
        self._default = default
        self._cast = cast
        self._validate_func = validate

        # get and validate on declaration to make sure all is good
        self._validate(self.get())

    def _validate(self, value):
        '''
        Runs the validation function (if provided) against the value.
        The function should not mutate the value.
        Returns the value if validation function returns a truthy value, otherwise raises an exception
        '''
        if self._validate_func is not None:
            if not self._validate_func(value):
                raise ValueError(
                    'Failed to validate {!r} config option'.format(self._name))
        return value

    def get(self):
        '''
        Returns the option's value at this point in time. Do not rely on this
        to be the same each time it is called, since it will update if the
        configuration is updated/reloaded.
        '''
        value = self._store._get(self._name, self._default)
        if self._cast is not None:
            return self._cast(value)
        return value

    def set(self, value):
        '''
        Sets the option's value. Will first cast and validate.
        '''
        if self._cast is not None:
            value = self._cast(value)
        self._validate(value)
        self._store._set(self._name, value)


# the global instance to be used across all the codebase
config = ConfigStore()


def cast_duration(d) -> int:
    """
    casts duration(1min, 1hr) into seconds.
    If input is an int it returns that unmodified.
    """
    if isinstance(d, int):
        return d
    if not isinstance(d, str):
        raise ValueError("Invalid type")
    seconds = timeparse(d)
    if seconds is None:
        raise ValueError("Invalid duration")
    return seconds
