#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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
Pulp Tools.
"""

class ConsumerId:
    """
    Client identity
    @ivar id: The client id.
    @type id: str
    """

    PATH = '/etc/pulp/consumer'

    def __init__(self, id=None):
        """
        @ivar id: The client id.
        @type id: str
        """
        if id:
            self.id = id
        else:
            self.read()

    def read(self):
        """
        Read identity from file.
        """
        f = open(self.PATH)
        try:
            self.id = f.read().strip()
        finally:
            f.close()

    def write(self, id):
        """
        Write identity to file.
        """
        f = open(self.PATH, 'w')
        try:
            f.write(self.id)
        finally:
            f.close()

    def __str__(self):
        return self.id
