# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
import httplib
import socket
from pulp.common.bundle import Bundle as BundleImpl
from pulp.common.config import Config
from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import HandlerReport
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from logging import getLogger

log = getLogger(__name__)


PULP_DISTRIBUTOR = 'pulp_distributor'
CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'


def subdict(adict, *keylist):
    d = {}
    for k,v in adict.items():
        if k in keylist:
            d[k] = v
    return d


class LocalBindings(Bindings):
    """
    Local Pulp (REST) API.
    """
    
    def __init__(self):
        host = socket.gethostname()
        port = 443
        cert = os.path.expanduser('~/.pulp/user-cert.pem')
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)


class RemoteBindings(Bindings):
    """
    Remote Pulp (REST) API.
    """
    
    def __init__(self):
        cfg = Config(CONFIG_PATH)
        server = cfg['server']
        host = server['host']
        port = int(server['port'])
        files = cfg['filesystem']
        cert = os.path.join(files['id_cert_dir'], files['id_cert_filename'])
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)


class Bundle(BundleImpl):
    """
    Consumer certificate (bundle)
    """

    def __init__(self):
        cfg = Config(CONFIG_PATH)
        files = cfg['filesystem']
        path = os.path.join(files['id_cert_dir'], files['id_cert_filename'])
        BundleImpl.__init__(self, path)


class RepositoryHandler(ContentHandler):

    def update(self, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.  See: L{Package.update}
        @rtype: L{HandlerReport}
        """
        report = HandlerReport()
        all = options.get('all', False)
        repoids = [key['repo_id'] for key in units if key]
        if all:
            binds = self.all_binds()
        else:
            binds = self.binds(repoids)
        details = self.synchronize(binds)
        report.succeeded(details, len(details))
        return report
    
    def all_binds(self):
        bundle = Bundle()
        myid = bundle.cn()
        http = Remote.binding.bind.find_by_id(myid)
        if http.response_code == httplib.OK:
            return self.filtered(http.response_body)
        else:
            raise Exception('sync failed, http:%d', http.response_code)
        
    def binds(self, repoids):
        binds = []
        bundle = Bundle()
        myid = bundle.cn()
        for repo_id in repoids:
            http = Remote.binding.bind.find_by_id(myid, repo_id)
            if http.response_code == httplib.OK:
                binds.extend(self.filtered(http.response_body))
            else:
                raise Exception('sync failed, http:%d', http.response_code)
        return binds
    
    def filtered(self, binds):
        type_id = PULP_DISTRIBUTOR
        return [b for b in binds if b['type_id'] == type_id]

    def synchronize(self, binds):
        report = {}
        self.merge(binds)
        return report

    def merge(self, binds):
        self.purge(binds)
        for b in binds:
            try:
                repo_id = b['repo_id']
                details = b['details']
                upstream = Repository(repo_id, details)
                myrepo = LocalRepository.fetch(repo_id)
                if myrepo:
                    myrepo.merge(upstream)
                else:
                    myrepo = LocalRepository(upstream.repo_id, upstream.details)
                    myrepo.add()
            except Exception, e:
                return e

    def purge(self, binds):
        try:
            upstream = [b['repo_id'] for b in binds]
            downstream = [r.repo_id for r in Repository.fetch_all()]
            for repo_id in downstream:
                if repo_id not in upstream:
                    repo = LocalRepository(repo_id)
                    repo.delete()
        except Exception, e:
            return e


class Local:
    
    binding = LocalBindings()
    

class Remote:
    
    binding = RemoteBindings()  


class Repository:
    
    def __init__(self, repo_id, details=None):
        self.repo_id = repo_id
        self.details = details or {}
        
    @property
    def basic(self):
        return subdict(
            self.details['repository'],
            'display_name', 'description', 'notes')
    
    @property
    def distributors(self):
        return self.details['distributors']
        

class Distributor:

    def __init__(self, repo_id, dist_id, details={}):
        self.repo_id = repo_id
        self.dist_id = dist_id
        self.details = subdict(details, 'config', 'auto_publish')

    
class LocalRepository(Local):
    
    @classmethod
    def fetch_all(cls):
        all = []
        for repo in cls.binding.repo_search.search():
            repo_id = repo['id']
            details = {
                'repository':repo,
                'distributors':[]
            }
            r = cls(repo_id, details)
            all.append(r)
        return all

    @classmethod
    def fetch(cls, repo_id):
        details = {}
        http = cls.binding.repo.repository(repo_id)
        if http.response_code == httplib.NOT_FOUND:
            return None
        if http.response_code == httplib.OK:
            details['repository'] = http.response_body
        else:
            raise Exception('query failed, http:%d', http.response_code)
        http = cls.binding.repo_distributor.distributors(repo_id)
        if http.response_code == httplib.OK:
            details['distributors'] = http.response_body
        else:
            raise Exception('query failed, http:%d', http.response_code)
        return cls(repo_id, details)
    
    def add(self):
        log.info('Repository: %s, added', self.repo_id)
        
    def update(self, delta):
        log.info('Repository: %s, updated', self.repo_id)
    
    def delete(self):
        log.info('Repository: %s, deleted', self.repo_id)
    
    def merge(self, upstream):
        delta = {}
        for k,v in upstream.basic.items():
            if self.basic[k] != v:
                self.basic[k] = v
                delta[k] = v
        if delta:
            self.update(delta)
        self.merge_distributors(upstream)
    
    def merge_distributors(self, upstream):
        self.purge_distributors(upstream)
        for details in upstream.distributors:
            dist_id = details['id']
            dist = Distributor(self.repo_id, dist_id, details)
            mydist = LocalDistributor.fetch(binding, self.repo_id, dist_id)
            if mydist:
                mydist.merge(dist)
            else:
                dist.add()
                
    def purge_distributors(self, upstream):
        upstream_distids = [d['id'] for d in upstream.distributors]
        for details in self.distributors:
            dist_id = details['id']
            if dist_id not in upstream_distids:
                dist = LocalDistributor(self.repo_id, dist_id)
                dist.delete()


class LocalDistributor(Local):
    
    @classmethod
    def fetch(cls, repo_id, dist_id):
        dist = None
        http = cls.binding.repo_distributor.distributor(repo_id, dist_id)
        if http.response_code == httplib.NOT_FOUND:
            return None
        if http.response_code == httplib.OK:
            return cls(repo_id, dist_id, http.response_body)
        else:
            raise Exception('query failed, http:%d', http.response_code)
        
    def add(self):
        log.info('Distributor: %s/%s, added', self.repo_id, self.dist_id)
        
    def update(self, delta):
        log.info('Distributor: %s/%s, updated', self.repo_id, self.dist_id)
    
    def delete(self):
        log.info('Distributor: %s/%s, deleted', self.repo_id, self.dist_id)
        
    def merge(self, upstream):
        delta = {}
        for k,v in upstream.details.items():
            if self.details[k] != v:
                self.details[k] = v
                delta[k] = v
        if delta:
            self.update(delta)
        return mrgcnt
