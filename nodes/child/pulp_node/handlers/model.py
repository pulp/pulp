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
Provides classes representing the database objects contained in either
the parent or child pulp server.  Parent objects are read-only and are used for querying,
comparison and merging to child objects.  Child objects are used for querying, comparison
and merging from remote objects. Unlike parent objects, child objects are also used to apply
changes to the child database and to trigger repository synchronization. These objects cover
repositories and their associated plugins.  Content units are not represented here.  That is
the responsibility of the nodes importers.
"""

import httplib

from logging import getLogger

from pulp.common.bundle import Bundle
from pulp.common.plugins import importer_constants
from pulp.bindings.exceptions import NotFoundException

from pulp_node.error import PurgeOrphansError, RepoSyncRestError, GetBindingsError
from pulp_node.poller import TaskPoller
from pulp_node import constants
from pulp_node import resources


log = getLogger(__name__)


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


# --- model objects ---------------------------------------------------------------------


class Entity(object):
    """
    Model entity base.
    """

    @staticmethod
    def purge_orphans():
        """
        Purge orphaned units within the inventory.
        """
        bindings = resources.pulp_bindings()
        http = bindings.content_orphan.remove_all()
        if http.response_code != httplib.ACCEPTED:
            raise PurgeOrphansError(http.response_code)


class Repository(Entity):
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

    @staticmethod
    def fetch_all():
        """
        Fetch all repositories from the inventory.
        :return: A list of: Repository
        :rtype: list
        """
        repositories = []
        bindings = resources.pulp_bindings()
        for repository in bindings.repo_search.search():
            repo_id = repository['id']
            details = {
                'repository': repository,
                'distributors': []
            }
            r = Repository(repo_id, details)
            repositories.append(r)
        return repositories

    @staticmethod
    def fetch(repo_id):
        """
        Fetch a specific repository from the inventory.
        :param repo_id: Repository ID.
        :type repo_id: str
        :return: The fetched repository.
        :rtype: Repository
        """
        details = {}
        bindings = resources.pulp_bindings()
        try:
            http = bindings.repo.repository(repo_id)
            details['repository'] = http.response_body
            http = bindings.repo_distributor.distributors(repo_id)
            details['distributors'] = http.response_body
            http = bindings.repo_importer.importers(repo_id)
            details['importers'] = http.response_body
            return Repository(repo_id, details)
        except NotFoundException:
            return None

    @property
    def basic_properties(self):
        """
        Get basic mutable properties within the bind payload details.
        :return: A dict of basic properties.
        :rtype: dict
        """
        return subdict(self.details['repository'], 'display_name', 'description', 'notes', 'scratchpad')

    @property
    def distributors(self):
        """
        Get the list of distributors defined in the bind payload details.
        :return: A list of distributors.
        :rtype: list
        """
        return self.details['distributors']

    @property
    def importers(self):
        """
        Get the list of importers defined in the bind payload details.
        :return: A list of importers.
        :rtype: list
        """
        return self.details['importers']

    def add(self):
        """
        Add the repository and associated plugins.
        """
        # repository
        bindings = resources.pulp_bindings()
        bindings.repo.create(
            self.repo_id,
            self.basic_properties['display_name'],
            self.basic_properties['description'],
            self.basic_properties['notes'])
        bindings.repo.update(self.repo_id, {'scratchpad': self.basic_properties['scratchpad']})
        # distributors
        for details in self.distributors:
            dist_id = details['id']
            dist = Distributor(self.repo_id, dist_id, details)
            dist.add()
        # importers
        for details in self.importers:
            imp_id = details['id']
            importer = Importer(self.repo_id, imp_id, details)
            importer.add()
        log.info('Repository: %s, added', self.repo_id)

    def update(self, delta):
        """
        Update this repository.
        :param delta: The properties that need to be updated.
        :type delta: dict
        """
        bindings = resources.pulp_bindings()
        bindings.repo.update(self.repo_id, delta)
        log.info('Repository: %s, updated', self.repo_id)

    def delete(self):
        """
        Delete this repository.
        """
        bindings = resources.pulp_bindings()
        bindings.repo.delete(self.repo_id)
        log.info('Repository: %s, deleted', self.repo_id)

    def merge(self, repository):
        """
        Merge another repository.
          1. Determine the delta and update the repository properties.
          2. Merge importers
          3. Merge distributors
        :param repository: Another repository.
        :type repository: Repository
        """
        delta = {}
        for k, v in repository.basic_properties.items():
            if self.basic_properties.get(k) != v:
                self.basic_properties[k] = v
                delta[k] = v
        if delta:
            self.update(delta)
        self.merge_importers(repository)
        self.merge_distributors(repository)

    def merge_importers(self, repository):
        """
        Merge importers.
          - Delete importers associated to this repository but not
            associated with the other repository.
          - Merge importers associated with this repository AND associated
            with the other repository.
          - Add importers associated with the other repository but NOT associated
            with this repository.
        :param repository: Another repository.
        :type repository: Repository
        """
        self.delete_importers(repository)
        for details in repository.importers:
            imp_id = details['id']
            importer_in = Importer(self.repo_id, imp_id, details)
            importer = Importer.fetch(self.repo_id, imp_id)
            if importer:
                importer.merge(importer_in)
            else:
                importer_in.add()

    def delete_importers(self, repository):
        """
        Delete importers associated with this repository but not
        associated with the other repository.
        :param repository: Another repository.
        :type repository: Repository
        """
        wanted_ids = [d['id'] for d in repository.importers]
        for details in self.importers:
            imp_id = details['id']
            if imp_id not in wanted_ids:
                importer = Importer(self.repo_id, imp_id, {})
                importer.delete()

    def merge_distributors(self, repository):
        """
        Merge distributors.
          - Merge distributors associated with this repository AND
            associated with the other repository.
          - Add distributors associated with the other repository but
            NOT associated with this repository.
        :param repository: Another repository.
        :type repository: Repository
        """
        for details in repository.distributors:
            dist_id = details['id']
            distributor_in = Distributor(self.repo_id, dist_id, details)
            distributor = Distributor.fetch(self.repo_id, dist_id)
            if distributor:
                distributor.merge(distributor_in)
            else:
                distributor_in.add()

    def run_synchronization(self, progress, cancelled, options):
        """
        Run a repo_sync() on this repository.
        :param progress: A progress report.
        :type progress: pulp_node.progress.RepositoryProgress
        :param options: node synchronization options.
        :type options: dict
        :return: The task result.
        """
        bindings = resources.pulp_bindings()
        poller = TaskPoller(bindings)
        max_download = options.get(
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD,
            constants.DEFAULT_DOWNLOAD_CONCURRENCY)
        node_certificate = options[constants.PARENT_SETTINGS][constants.NODE_CERTIFICATE]
        key, certificate = Bundle.split(node_certificate)
        configuration = {
            importer_constants.KEY_MAX_DOWNLOADS: max_download,
            importer_constants.KEY_MAX_SPEED: options.get(constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD),
            importer_constants.KEY_SSL_CLIENT_KEY: key,
            importer_constants.KEY_SSL_CLIENT_CERT: certificate,
            importer_constants.KEY_SSL_VALIDATION: False,
        }
        http = bindings.repo_actions.sync(self.repo_id, configuration)
        if http.response_code != httplib.ACCEPTED:
            raise RepoSyncRestError(self.repo_id, http.response_code)
        # The repo sync is returned with a single sync task in the Call Report
        task = http.response_body.spawned_tasks[0]
        result = poller.join(task.task_id, progress, cancelled)
        if cancelled():
            self._cancel_synchronization(task)
        return result

    def _cancel_synchronization(self, task):
        """
        Cancel a task associated with a repository synchronization.
        :param task: A running task.
        :type task: pulp.bindings.responses.Task
        """
        bindings = resources.pulp_bindings()
        http = bindings.tasks.cancel_task(task.task_id)
        if http.response_code == httplib.ACCEPTED:
            log.info('Task [%s] cancelled', task.task_id)
        else:
            log.error('Task [%s] cancellation failed http=%s', task.task_id, http.response_code)

    def __str__(self):
        return 'repository: %s' % self.repo_id


class Distributor(Entity):
    """
    Represents a repository-distributor association.
    :ivar repo_id: Repository ID.
    :type repo_id: str
    :param dist_id: Distributor ID.
    :type dist_id: str
    :ivar details: Distributor details as modeled in the bind payload.
    :type details: dict
    """

    @staticmethod
    def fetch(repo_id, dist_id):
        """
        Fetch the repository-distributor from the inventory.
        :param repo_id: The repository ID.
        :type repo_id: str
        :param dist_id: A distributor ID.
        :type dist_id: str
        :return: The fetched distributor.
        :rtype: Distributor
        """
        try:
            bindings = resources.pulp_bindings()
            http = bindings.repo_distributor.distributor(repo_id, dist_id)
            details = http.response_body
            return Distributor(repo_id, dist_id, details)
        except NotFoundException:
            return None

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

    def add(self):
        """
        Add this repository-distributor to the inventory.
        """
        bindings = resources.pulp_bindings()
        bindings.repo_distributor.create(
            self.repo_id,
            self.details['distributor_type_id'],
            self.details['config'],
            self.details['auto_publish'],
            self.dist_id)
        log.info('Distributor: %s/%s, added', self.repo_id, self.dist_id)

    def update(self, configuration):
        """
        Update this repository-distributor in the inventory.
        :param configuration: The updated configuration.
        :type configuration: dict
        """
        bindings = resources.pulp_bindings()
        bindings.repo_distributor.update(self.repo_id, self.dist_id, configuration)
        log.info('Distributor: %s/%s, updated', self.repo_id, self.dist_id)

    def delete(self):
        """
        Delete this distributor.
        """
        bindings = resources.pulp_bindings()
        bindings.repo_distributor.delete(self.repo_id, self.dist_id)
        log.info('Distributor: %s/%s, deleted', self.repo_id, self.dist_id)

    def merge(self, distributor):
        """
        Merge the distributor configuration from another distributor.
        :param distributor: Another distributor.
        :type distributor: Distributor
        """
        key = 'config'
        configuration = distributor.details[key]
        if self.details[key] != configuration:
            self.update(configuration)

    def __str__(self):
        return 'distributor: %s.%s' % (self.repo_id, self.dist_id)


class Importer(Entity):
    """
    Represents a repository-importer association.
    :ivar repo_id: Repository ID.
    :type repo_id: str
    :param imp_id: Importer ID.
    :type imp_id: str
    :ivar details: Importer details as modeled in the bind payload.
    :type details: dict
    """

    @staticmethod
    def fetch(repo_id, imp_id):
        """
        Fetch the repository-importer from the inventory.
        :return: The fetched importer.
        :rtype: Importer
        """
        try:
            bindings = resources.pulp_bindings()
            http = bindings.repo_importer.importer(repo_id, imp_id)
            details = http.response_body
            return Importer(repo_id, imp_id, details)
        except NotFoundException:
            return None

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

    def add(self):
        """
        Add this importer to the inventory.
        """
        conf = self.details['config']
        bindings = resources.pulp_bindings()
        bindings.repo_importer.create(self.repo_id, self.imp_id, conf)
        log.info('Importer %s/%s, added', self.repo_id, self.imp_id)

    def update(self, configuration):
        """
        Update this importer.
        :param configuration: The updated configuration.
        :type configuration: dict
        """
        bindings = resources.pulp_bindings()
        bindings.repo_importer.update(self.repo_id, self.imp_id, configuration)
        log.info('Importer: %s/%s, updated', self.repo_id, self.imp_id)

    def delete(self):
        """
        Delete this importer.
        """
        bindings = resources.pulp_bindings()
        bindings.repo_importer.delete(self.repo_id, self.imp_id)
        log.info('Importer: %s/%s, deleted', self.repo_id, self.imp_id)

    def merge(self, importer):
        """
        Merge this importer configuration from another importer.
        :param importer: Another importer.
        :type importer: Importer
        """
        self.update(importer.details['config'])

    def __str__(self):
        return 'importer: %s.%s' % (self.repo_id, self.imp_id)


class RepositoryBinding(Entity):
    """
    Represents a parent node bindings to a repository.
    """

    @staticmethod
    def fetch_all(bindings, node_id):
        """
        Fetch a list of ALL bind payloads for this consumer.
        :param bindings: A pulp API object.
        :type bindings: pulp.bindings.bindings.Bindings
        :param node_id: The node ID.
        :type node_id: str
        :return: List of bind payloads.
        :rtype: list
        """
        http = bindings.bind.find_by_id(node_id)
        if http.response_code == httplib.OK:
            return RepositoryBinding.filtered(http.response_body)
        else:
            raise GetBindingsError(http.response_code)

    @staticmethod
    def fetch(bindings, node_id, repo_ids):
        """
        Fetch a list of bind payloads for the specified list of repository ID.
        :param bindings: A pulp API object.
        :type bindings: pulp.bindings.bindings.Bindings
        :param node_id: The node ID.
        :type node_id: str
        :param repo_ids: A list of repository IDs.
        :type repo_ids:  list
        :return: List of bind payloads.
        :rtype: list
        """
        binds = []
        for repo_id in repo_ids:
            http = bindings.bind.find_by_id(node_id, repo_id)
            if http.response_code == httplib.OK:
                binds.extend(RepositoryBinding.filtered(http.response_body))
            else:
                raise GetBindingsError(http.response_code)
        return binds

    @staticmethod
    def filtered(binds):
        """
        Get a filtered list of binds.
          - Includes only the nodes_ distributors.
        :param binds: A list of bind payloads.
        :type binds: list
        :return: The filtered list of bind payloads.
        :rtype: list
        """
        return [b for b in binds if b['type_id'] in constants.ALL_DISTRIBUTORS]
