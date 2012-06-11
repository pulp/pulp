# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import itertools
import logging
import pickle

from pulp.server.api.base import BaseApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.errata import ErrataApi
#from pulp.server.api.repo import RepoApi
from pulp.server.async import AsyncTask
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.exceptions import PulpException
from pulp.server.tasking.task import Task, AsyncTask
from pulp.server.tasking.job import Job
from pulp.server.async import AsyncAgent
from pulp.server.agent import PulpAgent
from pulp.server.util import encode_unicode

# Temporary hack to use V2 repositories with V1 consumers. This will be removed once consumers are migrated to V2.
from pulp.server.exceptions import MissingResource
import pulp.server.managers.factory as manager_factory

log = logging.getLogger(__name__)


class ConsumerGroupApi(BaseApi):

    def __init__(self):
        self.consumerApi = ConsumerApi()
# <V2 Repo changes>
        #self.repoApi = RepoApi()
# </V2 Repo changes>
        self.errataApi = ErrataApi()

    def _getcollection(self):
        return model.ConsumerGroup.get_collection()


    @audit(params=['id', 'consumerids'])
    def create(self, id, description, consumerids=[]):
        """
        Create a new ConsumerGroup object and return it
        """
        id = encode_unicode(id)
        consumergroup = self.consumergroup(id)
        if(consumergroup):
            raise PulpException("A Consumer Group with id %s already exists" % id)

        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            if (consumer is None):
                raise PulpException("No Consumer with id: %s found" % consumerid)

        c = model.ConsumerGroup(id, description, consumerids)
        self.collection.insert(c, safe=True)
        return c

    @audit()
    def update(self, id, delta):
        """
        Updates a consumer group object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        group = self.consumergroup(id)
        if not group:
            raise PulpException('Group [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('description',):
                group[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(group, safe=True)

    def consumergroups(self, spec=None, fields=None):
        """
        List all consumer groups.
        """
        return list(self.collection.find(spec=spec, fields=fields))

    def consumergroup(self, id):
        """
        Return a single ConsumerGroup object
        """
        return self.collection.find_one({'id': id})


    def consumers(self, id):
        """
        Return consumer ids belonging to this ConsumerGroup
        """
        consumer = self.collection.find_one({'id': id})
        return consumer['consumerids']


    @audit()
    def add_consumer(self, groupid, consumerid):
        """
        Adds the passed in consumer to this group
        """
        consumergroup = self.consumergroup(groupid)
        if (consumergroup is None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException("No Consumer with id: %s found" % consumerid)
        conflicting_keyvalues = self.find_conflicting_keyvalues(groupid, consumerid)
        if len(conflicting_keyvalues.keys()) > 0:
            raise PulpException('Consumer [%s] cannot be added to consumergroup [%s] because of the following '
                                'conflicting key-value pairs. You need to delete these key-values from the consumer '
                                'in order to add it to this consumergroup: %s', consumerid, groupid, conflicting_keyvalues)
        self._add_consumer(consumergroup, consumer)
        self.collection.save(consumergroup, safe=True)

    def _add_consumer(self, consumergroup, consumer):
        """
        Responsible for properly associating a Consumer to a ConsumerGroup
        """
        consumerids = consumergroup['consumerids']
        if consumer["id"] in consumerids:
            return

        consumerids.append(consumer["id"])
        consumergroup["consumerids"] = consumerids

    @audit()
    def delete_consumer(self, groupid, consumerid):
        consumergroup = self.consumergroup(groupid)
        if (consumergroup is None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumerids = consumergroup['consumerids']
        if consumerid not in consumerids:
            return
        consumerids.remove(consumerid)
        consumergroup["consumerids"] = consumerids
        self.collection.save(consumergroup, safe=True)

    @audit()
    def bind(self, id, repoid):
        """
        Bind (subscribe) a consumer group to a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to bind.
        @type repoid: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)

# <V2 Repo changes>
        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repoid)
        if repo is None:
            raise MissingResource(repoid)
# </V2 Repo changes>

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.bind(consumerid, repoid)

    @audit()
    def unbind(self, id, repoid):
        """
        Unbind (unsubscribe) a consumer group from a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to unbind.
        @type repoid: str
        @raise PulpException: When consumer group not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)

# <V2 Repo changes>
        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repoid)
        if repo is None:
            raise MissingResource(repoid)
# </V2 Repo changes>

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.unbind(consumerid, repoid)

    def find_conflicting_keyvalues(self, id, consumerid):
        """
        Find keyvalues of a consumer that are conflicting with this consumer group
        """
        conflicting_keyvalues = {}
        consumergroup = self.consumergroup(id)
        consumer_keyvalues = self.consumerApi.get_keyvalues(consumerid)
        for key, value in consumergroup['key_value_pairs'].items():
            if key in consumer_keyvalues.keys() and value != consumer_keyvalues[key]:
                conflicting_keyvalues[key] = consumer_keyvalues[key]
        return conflicting_keyvalues

    def find_consumers_with_conflicting_keyvalues(self, id, key, value):
        """
        Find consumers belonging to this consumer group with conflicting key-values.
        """
        conflicting_consumers = []
        consumergroup = self.consumergroup(id)
        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            consumer_keyvalues = consumer['key_value_pairs']
            if key in consumer_keyvalues.keys() and consumer_keyvalues[key] != value:
                conflicting_consumers.append(consumerid)
        return conflicting_consumers


    @audit()
    def add_key_value_pair(self, id, key, value, force='false'):
        """
        Add key-value info to a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)

        key_value_pairs = consumergroup['key_value_pairs']
        if key not in key_value_pairs.keys():
            conflicting_consumers = self.find_consumers_with_conflicting_keyvalues(id, key, value)
            if len(conflicting_consumers) == 0:
                key_value_pairs[key] = value
            else:
                if force == 'false':
                    raise PulpException('Given key [%s] has different value for consumers %s '
                                        'belonging to this group. You can use --force to '
                                        'delete consumer\'s original value.', key, conflicting_consumers)
                else:
                    for consumerid in conflicting_consumers:
                        self.consumerApi.delete_key_value_pair(consumerid, key)
                    key_value_pairs[key] = value

        else:
            raise PulpException('Given key [%s] already exists', key)
        consumergroup['key_value_pairs'] = key_value_pairs
        self.collection.save(consumergroup, safe=True)


    @audit()
    def delete_key_value_pair(self, id, key):
        """
        delete key-value info from a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)

        key_value_pairs = consumergroup['key_value_pairs']
        if key in key_value_pairs.keys():
            del key_value_pairs[key]
        else:
            raise PulpException('Given key [%s] does not exist', key)
        consumergroup['key_value_pairs'] = key_value_pairs
        self.collection.save(consumergroup, safe=True)

    @audit()
    def update_key_value_pair(self, id, key, value):
        """
        Update key-value info of a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if not consumergroup:
            raise PulpException('Consumer Group [%s] does not exist', id)

        key_value_pairs = consumergroup['key_value_pairs']
        if key not in key_value_pairs.keys():
            raise PulpException('Given key [%s] does not exist', key)
        else:
            conflicting_consumers = self.find_consumers_with_conflicting_keyvalues(id, key, value)
            if len(conflicting_consumers) == 0:
                key_value_pairs[key] = value
            else:
                raise PulpException('Given key [%s] has different value for consumers %s '
                                    'belonging to this group. You can use --force to '
                                    'delete consumer\'s original value.', key, conflicting_consumers)

        consumergroup['key_value_pairs'] = key_value_pairs
        self.collection.save(consumergroup, safe=True)


    @audit()
    def installpackages(self, id, names=()):
        """
        Install packages on the consumers in a consnumer group.
        @param id: A consumer group id.
        @type id: str
        @param names: The package names to install.
        @type names: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        job = Job()
        for consumerid in consumergroup['consumerids']:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            task = AsyncTask(self.__installpackages, [consumerid, names])
            job.add(task)
        return job

    def __installpackages(self, consumerid, names, **options):
        """
        Task callback.
        @param consumerid: A consumer id.
        @type consumerid: str
        @param names: A list of package names.
        @type names: list
        @param options: Install options:
            - reboot : Suggest reboot (default: False)
            - importkeys : Import GPG keys.
        """
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', consumerid)
        secret = PulpAgent.getsecret(consumer)
        agent = AsyncAgent(consumerid, secret)
        reboot = options.get('reboot', False)
        importkeys = options.get('importkeys', False)
        task = AsyncTask.current()
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(task, timeout=tm)
        packages(importkeys=importkeys)
        return packages.install(names, reboot)

    @audit()
    def updatepackages(self, id, names=()):
        """
        Update packages on the consumers in a consnumer group.
        @param id: A consumer group id.
        @type id: str
        @param names: The package names to update.  Empty means ALL.
        @type names: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        job = Job()
        for consumerid in consumergroup['consumerids']:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            task = AsyncTask(self.__updatepackages, [consumerid, names])
            job.add(task)
        return job

    def __updatepackages(self, consumerid, names):
        """
        Task callback.
        @param consumerid: A consumer id.
        @type consumerid: str
        @param names: A list of package names.  Empty means ALL.
        @type names: list
        """
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', consumerid)
        secret = PulpAgent.getsecret(consumer)
        agent = AsyncAgent(consumerid, secret)
        task = AsyncTask.current()
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(task, timeout=tm)
        return packages.update(names)

    @audit()
    def uninstallpackages(self, id, names=()):
        """
        Uninstall packages on the consumers in a consnumer group.
        @param id: A consumer group id.
        @type id: str
        @param names: The package names to uninstall.
        @type names: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        job = Job()
        for consumerid in consumergroup['consumerids']:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            task = AsyncTask(self.__uninstallpackages, [consumerid, names])
            job.add(task)
        return job

    def __uninstallpackages(self, consumerid, names=()):
        """
        Task callback.
        @param consumerid: A consumer id.
        @type consumerid: str
        @param names: A list of package names.
        @type names: list
        """
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', consumerid)
        secret = PulpAgent.getsecret(consumer)
        agent = AsyncAgent(consumerid, secret)
        task = AsyncTask.current()
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(task, timeout=tm)
        return packages.uninstall(names)

    def __nopackagestoinstall(self, consumerid, names=(), **options):
        return ([], (False, False))

    @audit()
    def installpackagegroups(self, id, grpids):
        """
        Task callback to install package groups.
        @param id: The consumer group ID.
        @type id: str
        @param grpids: A list of package group ids.
        @type grpids: list
        @return: Whatever the agent returns.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        job = Job()
        for consumerid in consumergroup['consumerids']:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            task = AsyncTask(self.__installpackagegroups, [consumerid, grpids])
            job.add(task)
        return job

    def __installpackagegroups(self, consumerid, grpids):
        """
        Task callback to install package groups.
        @param consumerid: The consumer ID.
        @type consumerid: str
        @param grpids: A list of package group ids.
        @type grpids: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', consumerid)
        secret = PulpAgent.getsecret(consumer)
        agent = AsyncAgent(consumerid, secret)
        task = AsyncTask.current()
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        pkgrps = agent.PackageGroups(task, timeout=tm)
        return pkgrps.install(grpids)

    @audit()
    def uninstallpackagegroups(self, id, grpids):
        """
        Task callback to uninstall package groups.
        @param id: The consumer group ID.
        @type id: str
        @param grpids: A list of package group ids.
        @type grpids: list
        @return: Whatever the agent returns.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        job = Job()
        for consumerid in consumergroup['consumerids']:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            task = AsyncTask(self.__uninstallpackagegroups, [consumerid, grpids])
            job.add(task)
        return job

    def __uninstallpackagegroups(self, consumerid, grpids):
        """
        Task callback to uninstall package groups.
        @param consumerid: The consumer ID.
        @type consumerid: str
        @param grpids: A list of package group ids.
        @type grpids: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumerApi.consumer(consumerid)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', consumerid)
        secret = PulpAgent.getsecret(consumer)
        agent = AsyncAgent(consumerid, secret)
        task = AsyncTask.current()
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        pkgrps = agent.PackageGroups(task, timeout=tm)
        return pkgrps.uninstall(grpids)

    def installerrata(self, id, errataids=[], types=[], importkeys=False):
        """
        Install errata on a consumer group.
        @param id: A consumergroup id.
        @type id: str
        @param errataids: The errata ids to install.
        @type errataids: [str,..]
        @param types: Errata type filter
        @type types: str
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        consumerids = consumergroup['consumerids']
        job = Job()
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            if consumer is None:
                log.error('consumer [%s], not-found', consumerid)
                continue
            pkgs = []
            reboot_suggested = False
            if errataids:
                applicable_errata = self.consumerApi._applicable_errata(consumer, types)
                rlist = []
                for eid in errataids:
                    if self.errataApi.erratum(eid) is None:
                        raise Exception('Erratum [%s], not found' % eid)
                    errata = applicable_errata.get(eid)
                    if errata is None:
                        log.info('%s, not applicable to: %s', eid, consumerid)
                        continue
                    for pobj in applicable_errata[eid]['packages']:
                        if pobj["arch"] != "src":
                            pkgs.append(pobj["name"]) # + "." + pobj["arch"])
                    rlist.append(applicable_errata[eid]['reboot_suggested'])
                if True in rlist:
                    # if there is atleast one reboot_suggested=True, we trigger a reboot.
                    reboot_suggested = True
            else:
                #apply all updates
                pkgobjs = self.consumerApi.list_package_updates(id, types)
                for pobj in pkgobjs:
                    if pobj["arch"] != "src":
                        pkgs.append(pobj["name"]) # + "." + pobj["arch"])
            if pkgs:
                log.info("For consumer id %s Packages to install %s",
                          consumerid,
                          pkgs)
                task = AsyncTask(
                    self.__installpackages,
                    [consumerid, pkgs],
                    dict(reboot=reboot_suggested,
                         importkeys=importkeys))
            else:
                task = Task(
                    self.__nopackagestoinstall,
                    [consumerid, pkgs])
            job.add(task)
        return job
