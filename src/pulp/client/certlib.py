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
Contains certificate management (backend) classes.
"""

import os
from pulp.client.logutil import getLogger

log = getLogger(__name__)


class Bundle:

    ROOT = '/tmp/etc/pki/content'

    @classmethod
    def installed(cls):
        lst = []
        for fn in os.listdir(cls.ROOT):
            lst.append(Bundle(fn))
        return lst

    def __init__(self, id):
        self.id = id
        self.__downloaded = None
        self.mkdir(self.ROOT)

    def install(self, pulp, files):
        for fn in files:
            path = os.path.join(self.root(), fn)
            if os.path.exists(path):
                continue
            self.mkdir(self.root())
            n,ext = fn.rsplit('.',1)
            pem = self.downloaded(pulp, n)
            self.write(path, pem)

    def write(self, path, pem):
        try:
            f = open(path, 'w')
            f.write(pem)
            f.close()
        except:
            log.error(path, exc_info=True)

    def downloaded(self, pulp, key):
        if not self.__downloaded:
            self.__downloaded = \
                pulp.getCertificates(self.id)
        return self.__downloaded[key]

    def delete(self, excluded=[]):
        dir = self.root()
        for fn in os.listdir(dir):
            if fn in excluded:
                continue
            path = os.path.join(dir, fn)
            os.unlink(path)
        if not excluded:
            os.rmdir(dir)

    def root(self):
        return os.path.join(self.ROOT, self.id)

    def mkdir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def __eq__(self, other):
        return ( self.id == other.id )

    def __hash__(self):
        return hash(self.id)


class CertLib:

    def __init__(self, pulp):
        self.pulp = pulp

    def update(self, repolist):
        installed = Bundle.installed()
        needed = []
        for repo in repolist:
            b = Bundle(repo.id)
            needed.append(b)
        for b in installed:
            if b not in needed:
                b.delete()
        for b in needed:
            pass
