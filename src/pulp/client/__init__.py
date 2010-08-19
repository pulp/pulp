#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Pulp Client
"""

import os

class ConsumerId:
    """
    Client identity
    @ivar uuid: The client id.
    @type uuid: str
    """

    PATH = '/etc/pulp/consumer'

    def __init__(self, uuid=None):
        """
        @ivar value: The client id.
        @type value: str
        """
        self.uuid = None
        if uuid:
            self.uuid = uuid
        else:
            self.read()

    def read(self):
        """
        Read identity from file.
        """
        if not self.exists():
            return
        f = open(self.PATH)
        try:
            self.uuid = f.read().strip()
            return self
        finally:
            f.close()

    def write(self, id):
        """
        Write identity to file.
        """
        f = open(self.PATH, 'w')
        try:
            f.write(self.uuid)
            return self
        finally:
            f.close()
            
    def exists(self):
        return os.path.exists(self.PATH)

    def __str__(self):
        return self.uuid
