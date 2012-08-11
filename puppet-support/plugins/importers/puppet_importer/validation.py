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
import os

import constants

def validate(config):
    """
    Validates the configuration for the puppet module importer.

    :return: the expected return from the plugin's validate_config method
    :rtype:  tuple
    """

    result, msg = _validate_dir(config)
    if not result:
        return result, msg

    return True, None

def _validate_dir(config):
    """
    Validates the location of the puppet modules.
    """

    dir = config.get(constants.CONFIG_DIR)
    data = {'d' : dir}

    if dir is None:
        return False, _('Puppet module directory must be specified under the key <%(d)s>') % data

    if not os.path.exists(dir):
        return False, _('Directory <%(d)s> does not exist') % data

    if not os.access(dir, os.R_OK):
        return False, _('Directory <%(d)s> cannot be read by the Pulp server') % data

    return True, None