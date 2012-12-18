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
from pulp.agent.lib.report import ContentReport
from pulp.bindings.bindings import Bindings
from pulp.bindings.exceptions import NotFoundException
from pulp.bindings.server import PulpConnection
from logging import getLogger

log = getLogger(__name__)


CITRUS_DISTRIBUTOR = 'citrus_distributor'
CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'


def subdict(adict, *keylist):
    """
    Get a subset dictionary.
    @param adict: A dictionary to subset.
    @type adict: dict
    @param keylist: A list of keys to include in the subset.
    @type keylist: list
    @return: The subset dictionary.
    @rtype: dict.
    """
    return dict([t for t in adict.items() if t[0] in keylist])


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

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
          - apply : apply the transaction
          - importkeys : import GPG keys
          - reboot : Reboot after installed
        @type options: dict
        @return: An update report.
        @rtype: L{ContentReport}
        """
        report = ContentReport()
        all = options.get('all', False)
        repoids = [key['repo_id'] for key in units if key]
        if all:
            binds = self.all_binds()
        else:
            binds = self.binds(repoids)
        details = self.synchronize(binds)
        report.set_succeeded(details, len(details))
        return report

    def all_binds(self):
        """
        Get a list of ALL bind payloads for this consumer.
        @return: List of bind payloads.
        @rtype: list
        """
        bundle = Bundle()
        myid = bundle.cn()
        http = Remote.binding.bind.find_by_id(myid)
        if http.response_code == httplib.OK:
            return self.filtered(http.response_body)
        else:
            raise Exception('sync failed, http:%d', http.response_code)

    def binds(self, repoids):
        """
        Get a list of bind payloads for the specified list of repository ID.
        @param repoids: A list of repository IDs.
        @type repoids:  list
        @return: List of bind payloads.
        @rtype: list
        """
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
        """
        Get a filtered list of binds.
          - Includes only the (pulp) distributor.
        @param binds: A list of bind payloads.
        @type binds: list
        @return: The filtered list of bind payloads.
        @rtype: list
        """
        return [b for b in binds if b['type_id'] == CITRUS_DISTRIBUTOR]

    def synchronize(self, binds):
        """
        Synchronize repositories.
        @param binds: A list of bind payloads.
        @type binds: list
        @return: A sync report.
        @rtype: TBD
        """
        report = {}
        self.merge(binds)
        for repo_id in [b['repo_id'] for b in binds]:
            http = Local.binding.repo_actions.sync(repo_id, {})
        return report

    def merge(self, binds):
        """
        Merge repositories.
          - Delete repositories found locally but not upstream.
          - Merge repositories found BOTH upstream and locally.
          - Add repositories found upstream but NOT locally.
        @param binds: List of bind payloads.
        @type binds: list
        """
        self.purge(binds)
        for bind in binds:
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                upstream = Repository(repo_id, details)
                myrepo = LocalRepository.fetch(repo_id)
                if myrepo:
                    myrepo.merge(upstream)
                else:
                    myrepo = LocalRepository(repo_id, upstream.details)
                    myrepo.add()
            except Exception:
                log.exception(str(bind))

    def purge(self, binds):
        """
        Purge repositories found locally but NOT upstream.
        @param binds: List of bind payloads.
        @type binds: list
        """
        try:
            upstream = [b['repo_id'] for b in binds]
            downstream = [r.repo_id for r in LocalRepository.fetch_all()]
            for repo_id in downstream:
                if repo_id not in upstream:
                    repo = LocalRepository(repo_id)
                    repo.delete()
        except Exception, e:
            return e


class Local:
    """
    Local (downstream) entity.
    @cvar binding: A REST API binding.
    @type binding: L{Binding}
    """

    binding = LocalBindings()


class Remote:
    """
    Remote (upstream) entity.
    @cvar binding: A REST API binding.
    @type binding: L{Binding}
    """

    binding = RemoteBindings()


class Repository:
    """
    Represents a repository object.
    @ivar repo_id: Repository ID.
    @type repo_id: str
    @ivar details: Repository details as modeled by bind payload.
    @type details: dict
    """

    def __init__(self, repo_id, details=None):
        self.repo_id = repo_id
        self.details = details or {}

    @property
    def basic(self):
        """
        Get basic mutable properties for I{details}.
        @return: A dict of basic properties.
        @rtype: dict
        """
        return subdict(
            self.details['repository'],
            'display_name', 'description', 'notes')

    @property
    def distributors(self):
        """
        Get the list of distributors defined in I{details}.
        @return: A list of distributors.
        @rtype: list
        """
        return self.details['distributors']

    @property
    def importers(self):
        """
        Get the list of distributors defined in I{details}.
        @return: A list of distributors.
        @rtype: list
        """
        return self.details['importers']


class LocalRepository(Local, Repository):
    """
    Represents a local repository.
    """

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
        """
        Fetch the local repository.
        @param repo_id: Repository ID.
        @type repo_id: str
        @return: The fetched repository.
        @rtype: L{Repository}
        """
        details = {}
        try:
            http = cls.binding.repo.repository(repo_id)
            details['repository'] = http.response_body
            http = cls.binding.repo_distributor.distributors(repo_id)
            details['distributors'] = http.response_body
            return cls(repo_id, details)
        except NotFoundException:
            return None

    def add(self):
        """
        Add the local repository and associated distributors.
        """
        # repository
        self.binding.repo.create(
            self.repo_id,
            self.basic['display_name'],
            self.basic['description'],
            self.basic['notes'])
        # distributors
        for details in self.distributors:
            dist_id = details['id']
            dist = LocalDistributor(self.repo_id, dist_id, details)
            dist.add()
        # importer
        for details in self.importers:
            imp_id = details['id']
            importer = LocalImporter(self.repo_id, imp_id, details)
            importer.add()
        log.info('Repository: %s, added', self.repo_id)

    def update(self, delta):
        """
        Update the local repository.
        """
        self.binding.repo.update(self.repo_id, delta)
        log.info('Repository: %s, updated', self.repo_id)

    def delete(self):
        """
        Delete the local repository.
        """
        self.binding.repo.delete(self.repo_id)
        log.info('Repository: %s, deleted', self.repo_id)

    def merge(self, upstream):
        """
        Merge upstream repositories.
          1. Update the repository properties.
          2. Merge importers
          3. Merge distributors
        @param upstream: The upstream repository.
        @type upstream: L{Repository}
        """
        delta = {}
        for k,v in upstream.basic.items():
            if self.basic[k] != v:
                self.basic[k] = v
                delta[k] = v
        if delta:
            self.update(delta)
        self.merge_importers(upstream)
        self.merge_distributors(upstream)

    def merge_importers(self, upstream):
        """
        Merge importers.
          - Delete importers associated locally but not associated w/ upstream.
          - Merge importers associated locally AND associated w/ upstream.
          - Add importers associated w/ upstream but NOT associated locally.
        @param upstream: The upstream repository.
        @type upstream: L{Repository}
        """
        self.purge_importers(upstream)
        for details in upstream.importers:
            imp_id = details['id']
            imp = Importer(self.repo_id, imp_id, details)
            myimp = LocalImporter.fetch(self.repo_id, imp_id)
            if myimp:
                myimp.merge(imp)
            else:
                myimp = LocalImporter(self.repo_id, imp_id, details)
                myimp.add()

    def purge_importers(self, upstream):
        """
        Purge importers not associated with the upstream repository.
        @param upstream: The upstream repository.
        @type upstream: L{Repository}
        """
        upstream_impids = [d['id'] for d in upstream.importers]
        for details in self.importers:
            imp_id = details['id']
            if imp_id not in upstream_impids:
                imp = LocalImporter(self.repo_id, imp_id)
                imp.delete()

    def merge_distributors(self, upstream):
        """
        Merge distributors.
          - Delete distributors associated locally but not associated w/ upstream.
          - Merge distributors associated locally AND associated w/ upstream.
          - Add distributors associated w/ upstream but NOT associated locally.
        @param upstream: The upstream repository.
        @type upstream: L{Repository}
        """
        self.purge_distributors(upstream)
        for details in upstream.distributors:
            dist_id = details['id']
            dist = Distributor(self.repo_id, dist_id, details)
            mydist = LocalDistributor.fetch(self.repo_id, dist_id)
            if mydist:
                mydist.merge(dist)
            else:
                mydist = LocalDistributor(self.repo_id, dist_id, details)
                mydist.add()

    def purge_distributors(self, upstream):
        """
        Purge distributors not associated with the upstream repository.
        @param upstream: The upstream repository.
        @type upstream: L{Repository}
        """
        upstream_distids = [d['id'] for d in upstream.distributors]
        for details in self.distributors:
            dist_id = details['id']
            if dist_id not in upstream_distids:
                dist = LocalDistributor(self.repo_id, dist_id)
                dist.delete()


class Distributor:
    """
    Represents a repository-distributor association.
    @ivar repo_id: Repository ID.
    @type repo_id: str
    @param dist_id: Distributor ID.
    @type dist_id: str
    @ivar details: Distributor details as modeled by bind payload.
    @type details: dict
    """

    def __init__(self, repo_id, dist_id, details={}):
        """
        @param repo_id: Repository ID.
        @type repo_id: str
        @param dist_id: Distributor ID.
        @type dist_id: str
        @param details: Distributor details as modeled by bind payload.
        @type details: dict
        """
        self.repo_id = repo_id
        self.dist_id = dist_id
        self.details = subdict(details, 'config', 'auto_publish', 'distributor_type_id')


class LocalDistributor(Local, Distributor):
    """
    Represents a local repository-distributor association.
    """

    @classmethod
    def fetch(cls, repo_id, dist_id):
        """
        Fetch the local repository-distributor.
        @return: The fetched distributor.
        @rtype: L{LocalDistributor}
        """
        try:
            http = cls.binding.repo_distributor.distributor(repo_id, dist_id)
            details = http.response_body
            return cls(repo_id, dist_id, details)
        except NotFoundException:
            return None

    def add(self):
        """
        Add the local repository-distributor.
        """
        self.binding.repo_distributor.create(
            self.repo_id,
            self.details['distributor_type_id'],
            self.details['config'],
            self.details['auto_publish'],
            self.dist_id)
        log.info('Distributor: %s/%s, added', self.repo_id, self.dist_id)

    def update(self, delta):
        """
        Update the local repository-distributor.
        @param delta: The configuration delta.
        @type delta: dict
        """
        binding = self.binding.repo_distributor
        binding.update(self.repo_id, self.dist_id, delta)
        log.info('Distributor: %s/%s, updated', self.repo_id, self.dist_id)

    def delete(self):
        """
        Delete the local repository-distributor.
        """
        binding = self.binding.repo_distributor
        binding.delete(self.repo_id, self.dist_id)
        log.info('Distributor: %s/%s, deleted', self.repo_id, self.dist_id)

    def merge(self, upstream):
        """
        Merge the distributor configuration
        @param upstream: The upstream distributor
        @type upstream: L{Distributor}
        """
        delta = {}
        for k,v in upstream.details['config'].items():
            if self.details['config'][k] != v:
                self.details['config'][k] = v
                delta[k] = v
        if delta:
            self.update(delta)


class Importer:
    """
    Represents a repository-importer association.
    @ivar repo_id: Repository ID.
    @type repo_id: str
    @param imp_id: Importer ID.
    @type imp_id: str
    @ivar details: Importer details as modeled by bind payload.
    @type details: dict
    """

    def __init__(self, repo_id, imp_id, details={}):
        """
        @param repo_id: Repository ID.
        @type repo_id: str
        @param imp_id: Importer ID.
        @type imp_id: str
        @param details: Importer details as modeled by bind payload.
        @type details: dict
        """
        self.repo_id = repo_id
        self.imp_id = imp_id
        self.details = details


class LocalImporter(Local, Importer):
    """
    Represents a repository-importer association.
    """

    def add(self):
        """
        Add the importer.
        """
        binding = self.binding.repo_importer
        binding.create(self.repo_id, self.imp_id, self.details['config'])
        log.info('Importer %s/%s, added', self.repo_id, self.imp_id)

    def update(self, delta):
        """
        Update the local repository-importer.
        @param delta: The configuration delta.
        @type delta: dict
        """
        binding = self.binding.repo_importer
        binding.update(self.repo_id, self.imp_id, delta)
        log.info('Importer: %s/%s, updated', self.repo_id, self.imp_id)

    def delete(self):
        """
        Delete the local repository-importer.
        """
        binding = self.binding.repo_importer
        binding.delete(self.repo_id, self.imp_id)
        log.info('Importer: %s/%s, deleted', self.repo_id, self.imp_id)

    def merge(self, upstream):
        """
        Merge the importer configuration
        @param upstream: The upstream importer
        @type upstream: L{Importer}
        """
        delta = {}
        for k,v in upstream.details['config'].items():
            if self.details['config'][k] != v:
                self.details['config'][k] = v
                delta[k] = v
        if delta:
            self.update(delta)