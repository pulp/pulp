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

from uuid import uuid4
import simplejson as json

version = '0.1'


def getuuid():
    return str(uuid4())


class Envelope(dict):
    """
    Basic envelope is a json encoded/decoded dictionary
    that provides dot (.) style access.
    """

    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

    def load(self, s):
        """
        Load using a json string.
        @param s: A json encoded string.
        @type s: str
        """
        d = json.loads(s)
        self.update(d)
        return self

    def dump(self):
        """
        Dump to a json string.
        @return: A json encoded string.
        @rtype: str
        """
        d = self
        return json.dumps(d, indent=2)

    def __getattr__(self, attr):
        return self.get(attr, None)

    def __str__(self):
        return self.dump()
