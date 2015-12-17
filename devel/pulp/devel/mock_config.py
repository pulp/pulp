"""
This module contains utilities to aid in mocking the server config.
"""
from ConfigParser import SafeConfigParser

import mock

from pulp.server.config import config


def patch(overrides):
    """
    Perform a mock.patch on the server config that changes only the values passed in the overrides
    argument.

    :param overrides: A dictionary specifying the config overrides to apply. The keys should be
                      config sections, and each section should be a dictionary of setting and value
                      pairs.
    :type  overrides: dict
    """
    new_config = SafeConfigParser()

    # Copy the old config to the new config. deepcopy() complained about being asked to do this,
    # which is why it is done in this manual fashion.
    for section in config.sections():
        new_config.add_section(section)
        for key, value in config.items(section):
            new_config.set(section, key, value)

    # Overlay the overrides onto our new copy of the config
    for section, settings in overrides.items():
        for key, value in settings.items():
            new_config.set(section, key, value)

    # Returning the patch this way allows us to emulate all the normal mock.patch abilities, such as
    # acting as a function or class decorator, as well as acting as a context manager.
    return mock.patch('pulp.server.config.config._lazy_sections', new_config._sections)
