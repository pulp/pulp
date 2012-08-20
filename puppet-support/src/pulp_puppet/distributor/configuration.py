# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp_puppet.common import constants

# This should be added to the PluginCallConfiguration at the outset of each
# call in the distributor where one is specified. This will prevent the need
# for the rest of the codebase to explicitly apply default concepts.
DEFAULT_CONFIG = {
    constants.CONFIG_SERVE_HTTP : constants.DEFAULT_SERVE_HTTP,
    constants.CONFIG_SERVE_HTTPS : constants.DEFAULT_SERVE_HTTPS,

    constants.CONFIG_HTTP_DIR : constants.DEFAULT_HTTP_DIR,
    constants.CONFIG_HTTPS_DIR : constants.DEFAULT_HTTPS_DIR,
}


def validate(config):
    """
    Validates the configuration for the puppet module distributor.

    :param config: configuration passed in by Pulp
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :return: the expected return from the plugin's validate_config method
    :rtype:  tuple
    """

    validations = (
        _validate_http,
        _validate_https,
    )

    for v in validations:
        result, msg = v(config)
        if not result:
            return result, msg

    return True, None


def _validate_http(config):
    """
    Validates the serve HTTP flag.
    """
    parsed = config.get_boolean(constants.CONFIG_SERVE_HTTP)
    if parsed is None:
        return False, _('The value for <%(k)s> must be either "true" or "false"') % {'k' : constants.CONFIG_SERVE_HTTP}

    return True, None


def _validate_https(config):
    """
    Validates the serve HTTPS flag.
    """
    parsed = config.get_boolean(constants.CONFIG_SERVE_HTTPS)
    if parsed is None:
        return False, _('The value for <%(k)s> must be either "true" or "false"') % {'k' : constants.CONFIG_SERVE_HTTPS}

    return True, None