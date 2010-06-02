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

import os
from urllib import basejoin
from certlib import EntitlementDirectory, ActionLock
from iniparse import ConfigParser as Parser
from logutil import getLogger

log = getLogger(__name__)


class RepoLib:

    def __init__(self, lock=ActionLock()):
        self.lock = lock

    def update(self):
        lock = self.lock
        lock.acquire()
        try:
            action = UpdateAction()
            return action.perform()
        finally:
            lock.release()


class ActionLock(Lock):

    PATH = '/var/run/subsys/pulp/repolib.pid'

    def __init__(self):
        Lock.__init__(self, self.PATH)


class Pulp:

    def getProducts(self):
        return []


class Action:

    def __init__(self):
        self.pulp = Pulp()


class UpdateAction(Action):

    def perform(self):
        repod = RepoFile()
        repod.read()
        valid = set()
        updates = 0
        for cont in self.getUniqueContent():
            valid.add(cont.id)
            existing = repod.section(cont.id)
            if existing is None:
                updates += 1
                repod.add(cont)
                continue
            updates += existing.update(cont)
            repod.update(existing)
        for section in repod.sections():
            if section not in valid:
                updates += 1
                repod.delete(section)
        repod.write()
        return updates

    def getUniqueContent(self):
        unique = set()
        products = self.pulp.getProducts()
        products.sort()
        cfg = initConfig()
        baseurl = cfg['baseurl']
        for product in products:
            for r in self.getContent(product, baseurl):
                unique.add(r)
        return unique

    def getContent(self, product, baseurl):
        lst = []
        for ent in product.getContentEntitlements():
            id = ent.getLabel()
            repo = Repo(id)
            repo['name'] = ent.getName()
            repo['enabled'] = ent.getEnabled()
            repo['baseurl'] = self.join(baseurl, ent.getUrl())
            repo['gpgkey'] = self.join(baseurl, ent.getGpg())
            repo['sslclientkey'] = EntitlementDirectory.keypath()
            repo['sslclientcert'] = product.path
            lst.append(repo)
        return lst

    def join(self, base, url):
        if '://' in url:
            return url
        else:
            return basejoin(base, url)


class Repo(dict):

    CA = '/usr/share/rhn/RHNS-CA-CERT'

    # (name, mutable, default)
    PROPERTIES = (
        ('name', 0, None),
        ('baseurl', 0, None),
        ('enabled', 1, '1'),
        ('gpgcheck', 0, '1'),
        ('gpgkey', 0, None),
        ('sslverify', 0, '1'),
        ('sslcacert', 0, CA),
        ('sslclientkey', 0, None),
        ('sslclientcert', 0, None),
    )

    def __init__(self, id):
        self.id = id
        for k,m,d in self.PROPERTIES:
            self[k] = d

    def items(self):
        lst = []
        for k,m,d in self.PROPERTIES:
            v = self[k]
            lst.append((k,v))
        return tuple(lst)

    def update(self, other):
        count = 0
        for k,m,d in self.PROPERTIES:
            v = other.get(k)
            if not m:
                if v is None:
                    continue
                if self[k] == v:
                    continue
                self[k] = v
                count += 1
        return count

    def __str__(self):
        s = []
        s.append('[%s]' % self.id)
        for k in self.PROPERTIES:
            v = self.get(k)
            if v is None:
                continue
            s.append('%s=%s' % (k, v))

        return '\n'.join(s)

    def __eq__(self, other):
        return ( self.id == other.id )

    def __hash__(self):
        return hash(self.id)


class RepoFile(Parser):

    PATH = '/etc/yum.repos.d/'

    def __init__(self, name='redhat.repo'):
        Parser.__init__(self)
        self.path = os.path.join(self.PATH, name)
        self.create()

    def read(self):
        r = Reader(self.path)
        Parser.readfp(self, r)

    def write(self):
        f = open(self.path, 'w')
        Parser.write(self, f)
        f.close()

    def add(self, repo):
        self.add_section(repo.id)
        self.update(repo)

    def delete(self, section):
        return self.remove_section(section)

    def update(self, repo):
        for k,v in repo.items():
            Parser.set(self, repo.id, k, v)

    def section(self, section):
        if self.has_section(section):
            repo = Repo(section)
            for k,v in self.items(section):
                repo[k] = v
            return repo

    def create(self):
        if os.path.exists(self.path):
            return
        f = open(self.path, 'w')
        s = []
        s.append('#')
        s.append('# Red Hat Repositories')
        s.append('# Managed by (rhsm) subscription-manager')
        s.append('#')
        f.write('\n'.join(s))
        f.close()


class Reader:

    def __init__(self, path):
        f = open(path)
        bfr = f.read()
        self.idx = 0
        self.lines = bfr.split('\n')
        f.close()

    def readline(self):
        nl = 0
        i = self.idx
        eof = len(self.lines)
        while 1:
            if i == eof:
                return
            ln = self.lines[i]
            i += 1
            if not ln:
                nl += 1
            else:
                break
        if nl:
            i -= 1
            ln = '\n'
        self.idx = i
        return ln


def main():
    print 'Updating Pulp repository'
    repolib = RepoLib()
    updates = repolib.update()
    print '%d updates required' % updates
    print 'done'

if __name__ == '__main__':
    main()
