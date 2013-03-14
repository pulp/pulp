# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

"""
Provides classes representing representing the database objects contained
in either a parent or child pulp server.  Parent objects are read-only and
are used for querying, comparison and merging to child objects.  Child objects
are used for querying, comparison and merging from remote objects. Unlike remote
objects, child objects are also used to apply changes to the child database and
to trigger repository synchronization. These objects cover repositories and their
associated plugins.  Content units are not represented here.  That is the
responsibility of the nodes importers.
"""

import os
import socket
import httplib

from logging import getLogger

from pulp.common.bundle import Bundle
from pulp.common.config import Config
from pulp.bindings.bindings import Bindings as PulpBindings
from pulp.bindings.exceptions import NotFoundException
from pulp.bindings.server import PulpConnection

from pulp_node.poller import TaskPoller
from pulp_node import constants
from pulp_node import link


log = getLogger(__name__)


CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'


# --- utils -----------------------------------------------------------------------------


def subdict(adict, *keylist):
    """
    Get a subset dictionary.
    @param adict: A dictionary to subset.
    :type adict: dict
    :param keylist: A list of keys to be included in the subset.
    :type keylist: list
    :return: The subset dictionary.
    :rtype: dict.
    """
    return dict([t for t in adict.items() if t[0] in keylist])


# --- exceptions ------------------------------------------------------------------------

class ModelError(Exception):
    pass


# --- pulp bindings ---------------------------------------------------------------------


class ChildPulpBindings(PulpBindings):
    """
    Child Pulp (REST) API.
    """

    def __init__(self):
        host = socket.gethostname()
        port = 443
        cert = '/etc/pki/pulp/nodes/local.crt'
        connection = PulpConnection(host, port, cert_filename=cert)
        PulpBindings.__init__(self, connection)


class ParentPulpBindings(PulpBindings):
    """
    Parent Pulp (REST) API.
    """

    def __init__(self):
        cfg = Config(CONFIG_PATH)
        server = cfg['server']
        host = server['host']
        port = int(server['port'])
        files = cfg['filesystem']
        cert = os.path.join(files['id_cert_dir'], files['id_cert_filename'])
        connection = PulpConnection(host, port, cert_filename=cert)
        PulpBindings.__init__(self, connection)


# --- certificate bundles ---------------------------------------------------------------


class ConsumerSSLCredentialsBundle(Bundle):
    """
    A bundled consumer certificate and private key.
    """

    def __init__(self):
        """
        Read from file-system on construction.
        """
        cfg = Config(CONFIG_PATH)
        files = cfg['filesystem']
        path = os.path.join(files['id_cert_dir'], files['id_cert_filename'])
        Bundle.__init__(self, path)


# --- model objects ---------------------------------------------------------------------


class Child(object):
    """
    A Child (local) entity.
    :cvar binding: A REST API binding.
    :type binding: PulpBindings
    """
    binding = ChildPulpBindings()


class Parent(object):
    """
    A Parent (remote) entity.
    :cvar binding: A REST API binding.
    :type binding: PulpBindings
    """
    binding = ParentPulpBindings()


class Repository(object):
    """
    Represents a repository database object.
    :ivar repo_id: Repository ID.
    :type repo_id: str
    :ivar details: Repository details as modeled by bind payload.
    :type details: dict
    """

    def __init__(self, repo_id, details=None):
        """
        :param repo_id: The repository ID.
        :type repo_id: str
        :param details: The repository details defined in the bind payload.
        :type details: dict
        :return:
        """
        self.repo_id = repo_id
        self.details = details or {}

    @property
    def basic_properties(self):
        """
        Get basic mutable properties within the bind payload I{details}.
        :return: A dict of basic properties.
        :rtype: dict
        """
        return subdict(self.details['repository'], 'display_name', 'description', 'notes')

    @property
    def distributors(self):
        """
        Get the list of distributors defined in the bind payload I{details}.
        :return: A list of distributors.
        :rtype: list
        """
        return self.details['distributors']

    @property
    def importers(self):
        """
        Get the list of importers defined in the bind payload I{details}.
        :return: A list of importers.
        :rtype: list
        """
        return self.details['importers']

    def __str__(self):
        return 'repository: %s' % self.repo_id


class ChildRepository(Child, Repository):
    """
    Represents a repository associated with the child inventory.
    :ivar poller: A task poller used to poll for tasks status and progress.
    :type poller: TaskPoller
    """

    @classmethod
    def fetch_all(cls):
        """
        Fetch all repositories from the child inventory.
        :return: A list of: ChildRepository
        :rtype: list
        """
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
        Fetch a specific repository from the child inventory.
        :param repo_id: Repository ID.
        :type repo_id: str
        :return: The fetched repository.
        :rtype: ChildRepository
        """
        details = {}
        try:
            http = cls.binding.repo.repository(repo_id)
            details['repository'] = http.response_body
            http = cls.binding.repo_distributor.distributors(repo_id)
            details['distributors'] = http.response_body
            http = cls.binding.repo_importer.importers(repo_id)
            details['importers'] = http.response_body
            return cls(repo_id, details)
        except NotFoundException:
            return None

    @classmethod
    def purge_orphans(cls):
        """
        Purge orphaned units within the child inventory.
        """
        http = cls.binding.content_orphan.remove_all()
        if http.response_code != httplib.ACCEPTED:
            raise ModelError('purge_orphans() failed:%d', http.response_code)

    def __init__(self, repo_id, details=None):
        """
        :param repo_id: The repository ID.
        :type repo_id: str
        :param details: The repositories details.
        :type details: dict
        """
        Repository.__init__(self, repo_id, details)
        self.poller = TaskPoller(self.binding)

    def add(self):
        """
        Add the child repository and associated plugins..
        """
        # repository
        self.binding.repo.create(
            self.repo_id,
            self.basic_properties['display_name'],
            self.basic_properties['description'],
            self.basic_properties['notes'])
        # distributors
        for details in self.distributors:
            dist_id = details['id']
            dist = ChildDistributor(self.repo_id, dist_id, details)
            dist.add()
        # importers
        for details in self.importers:
            imp_id = details['id']
            importer = ChildImporter(self.repo_id, imp_id, details)
            importer.add()
        log.info('Repository: %s, added', self.repo_id)

    def update(self, delta):
        """
        Update this child repository.
        :param delta: The properties that need to be updated.
        :type delta: dict
        """
        self.binding.repo.update(self.repo_id, delta)
        log.info('Repository: %s, updated', self.repo_id)

    def delete(self):
        """
        Delete the child repository.
        """
        self.binding.repo.delete(self.repo_id)
        log.info('Repository: %s, deleted', self.repo_id)

    def merge(self, parent):
        """
        Merge parent repositories.
          1. Determine the delta and update the repository properties.
          2. Merge importers
          3. Merge distributors
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        delta = {}
        for k,v in parent.basic_properties.items():
            if self.basic_properties.get(k) != v:
                self.basic_properties[k] = v
                delta[k] = v
        if delta:
            self.update(delta)
        self.merge_importers(parent)
        self.merge_distributors(parent)

    def merge_importers(self, parent):
        """
        Merge importers.
          - Delete importers associated to this child repository but not
            associated with the parent repository.
          - Merge importers associated with this child repository AND associated
            with parent repository.
          - Add importers associated with the parent repository but NOT associated
            with this child repository.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        self.delete_importers(parent)
        for details in parent.importers:
            imp_id = details['id']
            imp = Importer(self.repo_id, imp_id, details)
            myimp = ChildImporter.fetch(self.repo_id, imp_id)
            if myimp:
                myimp.merge(imp)
            else:
                myimp = ChildImporter(self.repo_id, imp_id, details)
                myimp.add()

    def delete_importers(self, parent):
        """
        Delete importers associated with this child repository but not
        associated with the parent repository.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        parent_ids = [d['id'] for d in parent.importers]
        for details in self.importers:
            imp_id = details['id']
            if imp_id not in parent_ids:
                imp = ChildImporter(self.repo_id, imp_id, {})
                imp.delete()

    def merge_distributors(self, parent):
        """
        Merge distributors.
          - Delete distributors associated to this child repository but not
            associated with the parent repository.
          - Merge distributors associated with this child repository AND
            associated with parent repository.
          - Add distributors associated with the parent repository but NOT
            associated with this child repository.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        self.delete_distributors(parent)
        for details in parent.distributors:
            dist_id = details['id']
            dist = Distributor(self.repo_id, dist_id, details)
            mydist = ChildDistributor.fetch(self.repo_id, dist_id)
            if mydist:
                mydist.merge(dist)
            else:
                mydist = ChildDistributor(self.repo_id, dist_id, details)
                mydist.add()

    def delete_distributors(self, parent):
        """
        Delete distributors associated with this child repository but not
        associated with the parent repository.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        parent_ids = [d['id'] for d in parent.distributors]
        for details in self.distributors:
            dist_id = details['id']
            if dist_id not in parent_ids:
                dist = ChildDistributor(self.repo_id, dist_id, {})
                dist.delete()

    def run_synchronization(self, progress):
        """
        Run a repo_sync() on this child repository.
        :param progress: A progress report.
        :type progress: pulp_node.progress.RepositoryProgress
        :return: The task result.
        """
        http = self.binding.repo_actions.sync(self.repo_id, {})
        if http.response_code == httplib.ACCEPTED:
            task = http.response_body[0]
            return self.poller.join(task.task_id, progress)
        else:
            raise ModelError('synchronization failed: http=%d', http.response_code)

    def cancel_synchronization(self):
        """
        Cancel running synchronization.
        """
        self.poller.abort()


class Distributor(object):
    """
    Represents a repository-distributor association.
    :ivar repo_id: Repository ID.
    :type repo_id: str
    :param dist_id: Distributor ID.
    :type dist_id: str
    :ivar details: Distributor details as modeled in the bind payload.
    :type details: dict
    """

    def __init__(self, repo_id, dist_id, details):
        """
        :param repo_id: Repository ID.
        :type repo_id: str
        :param dist_id: Distributor ID.
        :type dist_id: str
        :param details: Distributor details as modeled in the bind payload.
        :type details: dict
        """
        self.repo_id = repo_id
        self.dist_id = dist_id
        self.details = subdict(details, 'config', 'auto_publish', 'distributor_type_id')

    def __str__(self):
        return 'distributor: %s.%s' % (self.repo_id, self.dist_id)


class ChildDistributor(Child, Distributor):
    """
    Represents a repository-distributor associated with the child inventory.
    """

    @classmethod
    def fetch(cls, repo_id, dist_id):
        """
        Fetch the repository-distributor from the child inventory.
        :param repo_id: The repository ID.
        :type repo_id: str
        :param dist_id: A distributor ID.
        :type dist_id: str
        :return: The fetched distributor.
        :rtype: ChildDistributor
        """
        try:
            binding = cls.binding.repo_distributor
            http = binding.distributor(repo_id, dist_id)
            details = http.response_body
            return cls(repo_id, dist_id, details)
        except NotFoundException:
            return None

    def add(self):
        """
        Add this repository-distributor to the child inventory.
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
        Update this repository-distributor in the child inventory.
        :param delta: The properties that need to be updated.
        :type delta: dict
        """
        binding = self.binding.repo_distributor
        binding.update(self.repo_id, self.dist_id, delta)
        log.info('Distributor: %s/%s, updated', self.repo_id, self.dist_id)

    def delete(self):
        """
        Delete this repository-distributor from the child inventory.
        """
        binding = self.binding.repo_distributor
        binding.delete(self.repo_id, self.dist_id)
        log.info('Distributor: %s/%s, deleted', self.repo_id, self.dist_id)

    def merge(self, parent):
        """
        Merge the distributor configuration from the parent.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        delta = {}
        for k,v in parent.details['config'].items():
            if self.details['config'].get(k) != v:
                self.details['config'][k] = v
                delta[k] = v
        if delta:
            self.update(delta)


class Importer(object):
    """
    Represents a repository-importer association.
    :ivar repo_id: Repository ID.
    :type repo_id: str
    :param imp_id: Importer ID.
    :type imp_id: str
    :ivar details: Importer details as modeled in the bind payload.
    :type details: dict
    """

    def __init__(self, repo_id, imp_id, details):
        """
        :param repo_id: Repository ID.
        :type repo_id: str
        :param imp_id: Importer ID.
        :type imp_id: str
        :param details: Importer details as modeled in the bind payload.
        :type details: dict
        """
        self.repo_id = repo_id
        self.imp_id = imp_id
        self.details = details

    def __str__(self):
        return 'importer: %s.%s' % (self.repo_id, self.imp_id)


class ChildImporter(Child, Importer):
    """
    Represents a repository-importer associated with the child inventory.
    """

    @classmethod
    def fetch(cls, repo_id, imp_id):
        """
        Fetch the repository-importer from the child inventory.
        :return: The fetched importer.
        :rtype: ChildImporter
        """
        try:
            binding = cls.binding.repo_importer
            http = binding.importer(repo_id, imp_id)
            details = http.response_body
            return cls(repo_id, imp_id, details)
        except NotFoundException:
            return None

    def add(self):
        """
        Add this importer to the child inventory.
        """
        binding = self.binding.repo_importer
        conf = self.details['config']
        conf = link.unpack_all(conf)
        binding.create(self.repo_id, self.imp_id, conf)
        log.info('Importer %s/%s, added', self.repo_id, self.imp_id)

    def update(self, delta):
        """
        Update this repository-importer in the child inventory.
        :param delta: The properties that need to be updated.
        :type delta: dict
        """
        binding = self.binding.repo_importer
        binding.update(self.repo_id, self.imp_id, delta)
        log.info('Importer: %s/%s, updated', self.repo_id, self.imp_id)

    def delete(self):
        """
        Delete this repository-importer from the child inventory.
        """
        binding = self.binding.repo_importer
        binding.delete(self.repo_id, self.imp_id)
        log.info('Importer: %s/%s, deleted', self.repo_id, self.imp_id)

    def merge(self, parent):
        """
        Merge this importer configuration from the parent importer.
        :param parent: The parent repository.
        :type parent: ParentRepository
        """
        delta = {}
        for k,v in parent.details['config'].items():
            if self.details['config'].get(k) != v:
                self.details['config'][k] = v
                delta[k] = v
        if delta:
            delta = link.unpack_all(delta)
            self.update(delta)


class Binding(object):
    """
    Represents a consumer binding to a repository.
    """
    pass


class ParentBinding(Parent, Binding):
    """
    Represents a parent consumer binding to a repository.
    """

    @classmethod
    def fetch_all(cls):
        """
        Fetch a list of ALL bind payloads for this consumer.
        :return: List of bind payloads.
        :rtype: list
        """
        bundle = ConsumerSSLCredentialsBundle()
        myid = bundle.cn()
        http = Parent.binding.bind.find_by_id(myid)
        if http.response_code == httplib.OK:
            return cls.filtered(http.response_body)
        else:
            raise ModelError('fetch failed, http:%d', http.response_code)

    @classmethod
    def fetch(cls, repo_ids):
        """
        Fetch a list of bind payloads for the specified list of repository ID.
        :param repo_ids: A list of repository IDs.
        :type repo_ids:  list
        :return: List of bind payloads.
        :rtype: list
        """
        binds = []
        bundle = ConsumerSSLCredentialsBundle()
        myid = bundle.cn()
        for repo_id in repo_ids:
            http = Parent.binding.bind.find_by_id(myid, repo_id)
            if http.response_code == httplib.OK:
                binds.extend(cls.filtered(http.response_body))
            else:
                raise ModelError('fetch failed, http:%d', http.response_code)
        return binds

    @classmethod
    def filtered(cls, binds):
        """
        Get a filtered list of binds.
          - Includes only the nodes_ distributors.
        :param binds: A list of bind payloads.
        :type binds: list
        :return: The filtered list of bind payloads.
        :rtype: list
        """
        return [b for b in binds if b['type_id'] in constants.ALL_DISTRIBUTORS]


class Node(object):
    """
    Represents a pulp node.
    """
    pass


class ParentNode(Parent, Node):
    """
    Represents a child node in the parent.
    """

    @classmethod
    def fetch(cls):
        """
        Fetch this node from the parent.
        :return: This node.
        :rtype: dict
        """
        bundle = ConsumerSSLCredentialsBundle()
        myid = bundle.cn()
        http = Parent.binding.consumer.consumer(myid)
        if http.response_code == httplib.OK:
            return http.response_body
        else:
            raise Exception('Node not found in parent.')

    @classmethod
    def get_strategy(cls):
        """
        Get this node's update strategy.
        :return: The node level strategy for this node.
        :rtype: str
        """
        node = cls.fetch()
        notes = node.get('notes', {})
        return notes.get(constants.STRATEGY_NOTE_KEY, constants.DEFAULT_STRATEGY)