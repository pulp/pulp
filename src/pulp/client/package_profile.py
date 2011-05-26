#!/usr/bin/python
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
#
from pulp.client.logutil import getLogger
import utils
import rpm
log = getLogger(__name__)

class InvalidProfileType(Exception):
    pass

class BaseProfile(object):
    """
    Base Class for probing profile info. type of package content to run lookups on eg: 'rpm','jar','zip' etc.
    """
    def collect(self):
        # implement in the subclass
        pass

class RPMProfile(BaseProfile):

    def collect(self):
        """ Accumulates list of installed rpm info """
        ts = rpm.TransactionSet()
        ts.setVSFlags(-1)
        installed = ts.dbMatch()
        return utils.generatePakageProfile(installed)

class JarProfile(BaseProfile):
    pass

def get_profile(type):
    '''
    Returns an instance of a Profile object
    @param type: profile type
    @type type: string
    Returns an instance of a Profile object
    '''
    if type not in PROFILE_MAP:
        raise InvalidProfileType('Could not find profile for type [%s]', type)
    profile = PROFILE_MAP[type]()
    return profile

PROFILE_MAP = {
    "rpm" : RPMProfile,
}

if __name__ == '__main__':
    p = get_profile("rpm")
    import pprint
    pprint.pprint(p.collect())
