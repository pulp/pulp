# -*- coding: utf-8 -*-

from ConfigParser import SafeConfigParser


DEFAULT_CONFIG_FILES = ['/etc/pulp/streamer.conf']
DEFAULT_VALUES = {
    'streamer': {
        'port': '8751',
        'interfaces': 'localhost',
        'cache_timeout': '86400',
    },
}


def load_configuration(config_filenames):
    """
    Load a configuration object from the default values and the provided files.
    The default values are applied first and are overridden by a value in any
    of the files provided.

    :param config_filenames: A list of files containing config values for the streamer.
                             These should be readable by the user running the streamer.
    :type  config_filenames: list of str

    :return: A configuration for the Pulp streamer which is guaranteed to have a value
             for every configuration option.
    :rtype:  SafeConfigParser
    """
    config = SafeConfigParser()
    for section, settings in DEFAULT_VALUES.items():
        config.add_section(section)
        for option, value in settings.items():
            config.set(section, option, value)
    config.read(config_filenames)

    return config
