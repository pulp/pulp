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

from pulp.server.compat import wraps

# content plugin base class ----------------------------------------------------

class ContentPlugin(object):
    """
    Base plugin class for the generic content system
    """

    def __init__(self, config):
        assert isinstance(config, dict)
        self.__config = config
        self.__current_config = None

    @property
    def config(self):
        if self.__current_config is None:
            return self.__config
        return self.__current_config

    def set_current_config(self, config):
        assert isinstance(config, dict)
        current_config = copy.copy(self.__config)
        current_config.update(config)
        self.__current_config = current_config

    def unset_current_config(self):
        self.__current_config = None

    @classmethod
    def metadata(cls):
        return {}

# config override decorator ----------------------------------------------------

def allow_config_override(method):
    @wraps(method)
    def _config_override_decorator(self, *args, **kwargs):
        override_config = kwargs.get('config', {})
        self.set_current_config(override_config)
        return_value = method(self, *args, **kwargs)
        self.unset_current_config()
        return return_value
    return _config_override_decorator
