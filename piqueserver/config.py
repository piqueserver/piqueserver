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

import six
import toml


DEFAULT_FORMAT = 'TOML'
TOML_FORMAT = 'TOML'
JSON_FORMAT = 'JSON'


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

    def _validate_all(self):
        for option in self._options.values():
            option._validate(option.get())
        for section in self._sections.values():
            section._validate_all()

    # https://stackoverflow.com/a/3233356/
    def _nested_update(self, config_dict, updates):
        for k, v in six.iteritems(updates):
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
            raise ValueError('Unsupported config file format: {}'.format(format_))
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
            raise ValueError('Unsupported config file format: {}'.format(format_))

    def _get(self, name, default=None):
        if name not in self._raw_config:
            self._raw_config[name] = default
        return self._raw_config[name]

    def _set(self, name, value):
        self._raw_config[name] = value

    def option(self, name, cast=None, default=None, validate=None):
        '''
        Register and return a new option object.
        '''
        option = _Option(self, name, default, cast, validate)
        self._options[name] = option
        return option

    def section(self, name):
        '''
        Register and return a new section object.
        '''
        section = _Section(self, name)
        self._sections[name] = section
        return section


class _Section():
    '''
    Represents a section of a configstore. Can be nested arbitarily.
    '''
    def __init__(self, store, name):
        self._store = store
        self._name = name
        self._sections = {}
        self._options = {}

    def _validate_all(self):
        for option in self._options.values():
            option._validate(option.get())
        for section in self._sections.values():
            section._validate_all()

    def get_dict(self):
        return self._store.get_dict().get(self._name, {})

    def load_from_dict(self, config):
        self._store._set(self._name, config)

    def update_from_dict(self, config):
        d = self._store._get(self._name, {})
        d.update(config)
        self._store._set(self._name, d)

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

    def section(self, name):
        '''
        Registers and returns a new Section object which is a subsection of this section.
        '''
        section = _Section(self, name)
        self._sections[name] = section
        return section

    def option(self, name, cast=None, default=None, validate=None):
        '''
        Registers and returns a new Option object which is an option in this section.
        '''
        option = _Option(self, name, default, cast, validate)
        self._options[name] = option
        return option



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
        self._store = store # ConfigStore object
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
                raise ValueError('Failed to validate {!r} config option'.format(self._name))
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


config = ConfigStore()
