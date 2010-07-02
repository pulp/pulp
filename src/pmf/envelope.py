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

import simplejson as json


class Envelope(dict):

    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

    def load(self, s):
        d = json.loads(s)
        self.update(d)

    def dump(self):
        d = self
        return json.dumps(d, indent=2)

    def __getattr__(self, attr):
        return self.get(attr, None)

    def __str__(self):
        return self.dump()
