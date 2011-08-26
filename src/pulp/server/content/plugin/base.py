# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import copy
import itertools
from ConfigParser import SafeConfigParser

from pulp.server.compat import wraps


class ContentPlugin(object):

    def __init__(self, config):
        self._config = config
        self._method_config = None
        self.__current_config = None

    @property
    def config(self):
        def _merge_configs(orig, override):
            config = SafeConfigParser()
            for section in set(itertools.chain(orig.sections(), override.sections())):
                config.add_section(section)
                for option in set(itertools.chain(orig.options(section), override.options(section))):
                    value = None
                    if override.has_option(section, option):
                        value = override.get(section, option)
                    else:
                        value = orig.get(section, option)
                    config.set(section, option, value)
            return config

        if self.__current_config is not None:
            return self.__current_config
        if self._method_config is None:
            self.__current_config = self._config
        else:
            self.__current_config = _merge_configs(self._config, self._method_config)
        return self.__current_config

    @classmethod
    def metadata(cls):
        return {}


def config_override(method):
    @wraps(method)
    def _config_override_decorator(self, *args, **kwargs):
        return method(self, *args, **kwargs)
    return _config_override_decorator
