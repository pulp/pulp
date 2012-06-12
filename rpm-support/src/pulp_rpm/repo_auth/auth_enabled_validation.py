#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

'''
Logic for checking if the Pulp server is configured to apply *any* repo
authentication. This is meant to be used as a short-circuit validation
to prevent the more costly tests from being run in the case the Pulp server
doesn't care at all about repo authentication.
'''

from ConfigParser import SafeConfigParser

# This needs to be accessible on both Pulp and the CDS instances, so a
# separate config file for repo auth purposes is used.
CONFIG_FILENAME = '/etc/pulp/repo_auth.conf'


# -- framework------------------------------------------------------------------

def authenticate(environ):
    '''
    Framework hook method.
    '''
    config = _config()
    is_enabled = config.getboolean('main', 'enabled')

    # If auth is disabled, return true so the framework assumes a valid user has
    # been found and will short-circuit any other validation checks.
    return not is_enabled

def _config():
    config = SafeConfigParser()
    config.read(CONFIG_FILENAME)
    return config
