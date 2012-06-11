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

import hashlib
import itertools
import logging
import pickle

# Pulp
import pulp.server.auth.cert_generator as cert_generator
import pulp.server.cds.round_robin as round_robin
from pulp.server import config
import pulp.server.consumer_utils as consumer_utils

from pulp.server.api.base import BaseApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.keystore import KeyStore
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException
from pulp.server.tasking.task import Task
from pulp.server.util import chunks, compare_packages
from pulp.server.agent import PulpAgent
from pulp.common.bundle import Bundle
from pulp.common.capabilities import AgentCapabilities

# Temporary hack to use V2 repositories with V1 consumers. This will be removed once consumers are migrated to V2.
from pulp.server.exceptions import MissingResource
import pulp.server.managers.factory as manager_factory


log = logging.getLogger(__name__)

consumer_fields = model.Consumer(None, None).keys()


class ConsumerApi(BaseApi):

    def __init__(self):
        self.errataapi = ErrataApi()
        self.repoapi = RepoApi()
        self.packageapi = PackageApi()
        self.consumer_history_api = ConsumerHistoryApi()

    def _getcollection(self):
        return model.Consumer.get_collection()

    def _get_consumergroup_collection(self):
        '''
        The circular dependency of requiring the consumergroup API causes issues, so
        this method returns a hook to that collection.

        @return: pymongo database connection to the consumergroup connection
        @rtype:  ?
        '''
        return model.ConsumerGroup.get_collection()

    @event(subject='consumer.created')
    @audit()
    def create(self, id, description, capabilities={}, key_value_pairs={}):
        """
        Create a new Consumer object and return it
        """
        self.check_id(id)
        consumer = self.consumer(id)
        if consumer:
            raise PulpException("Consumer [%s] already exists" % id)
        expiration_date = config.config.getint('security', 'consumer_cert_expiration')
        key, crt = cert_generator.make_cert(id, expiration_date)
        c = model.Consumer(id, description)
        c.capabilities = capabilities
        c.certificate = crt.strip()
        self.collection.insert(c, safe=True)
        for key, value in key_value_pairs.items():
            self.add_key_value_pair(c.id, key, value)
        self.consumer_history_api.consumer_registered(c.id)
        c.certificate = Bundle.join(key, crt)
        return c

    @audit()
    def update(self, id, delta):
        """
        Updates a consumer object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('description',):
                consumer[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(consumer, safe=True)

    @event(subject='consumer.deleted')
    @audit()
    def delete(self, id):
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)

        consumergroup_db = self._get_consumergroup_collection()
        consumergroups = list(consumergroup_db.find({'consumerids' : consumer['id']}))
        for consumergroup in consumergroups:
            consumerids = consumergroup['consumerids']
            consumerids.remove(consumer['id'])
            consumergroup['consumerids'] = consumerids
            consumergroup_db.save(consumergroup, safe=True)
            
        # notify agent
        agent = PulpAgent(consumer, async=True)
        agent_consumer = agent.ConsumerXXX()
        agent_consumer.unregistered()

        self.collection.remove(dict(id=id), safe=True)
        self.consumer_history_api.consumer_unregistered(id)


    def find_consumergroup_with_conflicting_keyvalues(self, id, key, value):
        """
        Find consumer group that this consumer belongs to with conflicting key-values.
        """
        consumergroup_db = self._get_consumergroup_collection()
        consumergroups = list(consumergroup_db.find({'consumerids' : id}))
        for consumergroup in consumergroups:
            group_keyvalues = consumergroup['key_value_pairs']
            if key in group_keyvalues.keys() and group_keyvalues[key] != value:
                return consumergroup['id']
        return None

    @audit()
    def add_key_value_pair(self, id, key, value):
        """
        Add key-value info to a consumer.
        @param id: consumer id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer is not found or given key exists.
        """
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        key_value_pairs = consumer['key_value_pairs']
        if key not in key_value_pairs.keys():
            conflicting_group = self.find_consumergroup_with_conflicting_keyvalues(id, key, value)
            if conflicting_group is None:
                key_value_pairs[key] = value
            else:
                raise PulpException('Given key [%s] has different value for this consumer '
                                    'because of its membership in group [%s]. You can delete consumer '
                                    'from that group and try again.', key, conflicting_group)
        else:
            raise PulpException('Given key [%s] already exists', key)
        consumer['key_value_pairs'] = key_value_pairs
        self.collection.save(consumer, safe=True)

    @audit()
    def delete_key_value_pair(self, id, key):
        """
        Delete key-value information from a consumer.
        @param id: consumer id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @raise PulpException: When consumer does not exist or key is not found.
        """
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        key_value_pairs = consumer['key_value_pairs']
        if key in key_value_pairs.keys():
            del key_value_pairs[key]
        else:
            raise PulpException('Given key [%s] does not exist', key)
        consumer['key_value_pairs'] = key_value_pairs
        self.collection.save(consumer, safe=True)

    @audit()
    def update_key_value_pair(self, id, key, value):
        """
        Update key-value info of a consumer.
        @param id: consumer id.
        @type id: str
        @param repoid: key
        @type repoid: str
        @param value: value
        @type: str
        @raise PulpException: When consumer is not found or given key exists.
        """
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        key_value_pairs = consumer['key_value_pairs']
        if key not in key_value_pairs.keys():
            raise PulpException('Given key [%s] does not exist', key)
        else:
            conflicting_group = self.find_consumergroup_with_conflicting_keyvalues(id, key, value)
            if conflicting_group is None:
                key_value_pairs[key] = value
            else:
                raise PulpException('Given key [%s] has different value for this consumer '
                                    'because of its membership in group [%s]. You can delete consumer '
                                    'from that group and try again.', key, conflicting_group)

        consumer['key_value_pairs'] = key_value_pairs
        self.collection.save(consumer, safe=True)

    def get_keyvalues (self, id):
        """
        Get all key-values corresponding to consumer. This also includes key-values inherited from
        consumergroups that this consumer belongs.
        @param id: consumer id
        @type id: str
        @raise PulpException: When consumer does not exist
        """
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        key_value_pairs = consumer.get('key_value_pairs', {})

        consumergroup_db = self._get_consumergroup_collection()
        consumergroups = list(consumergroup_db.find({'consumerids' : consumer['id']}))
        for consumergroup in consumergroups:
            group_key_value_pairs = consumergroup['key_value_pairs']
            key_value_pairs.update(group_key_value_pairs)

        return key_value_pairs

    def consumers_with_key_value(self, key, value, fields=None):
        """
        List consumers with given key-values
        """
        consumer_key = 'key_value_pairs.' + key
        return self.consumers({consumer_key: value}, fields)

    @audit()
    def bulkcreate(self, consumers):
        """
        Create a set of Consumer objects in a bulk manner
        @type consumers: list of dictionaries
        @param consumers: dictionaries representing new consumers
        """
        ## Have to chunk this because of issue with PyMongo and network
        ## See: http://tinyurl.com/2eyumnc
        chunksize = 50
        chunked = chunks(consumers, chunksize)
        inserted = 0
        for chunk in chunked:
            self.collection.insert(chunk, check_keys=False, safe=False)
            inserted = inserted + chunksize

    def consumers(self, spec=None, fields=None):
        """
        List all consumers.  Can be quite large
        """
        return list(self.collection.find(spec=spec, fields=fields))

    def consumer(self, id, fields=None):
        """
        Return a single Consumer object
        """
        consumers = self.consumers({'id': id}, fields)
        if not consumers:
            return None
        return consumers[0]

    def packages(self, id):
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        return consumer.get('package_profile', [])

    def consumers_with_package_names(self, names, fields=None):
        """
        List consumers using passed in names
        """
        consumers = []
        for name in names:
            #consumers.extend(self.collection.find({'package_profile.name': name}, fields))
            consumers.extend(self.consumers({'package_profile.name': name}, fields))
        return consumers

    @audit()
    def bind(self, id, repoid):
        '''
        Binds (subscribe) the consumer identified by id to an existing repo. If the
        consumer is already bound to the repo, this call has no effect.
        See consumer_utils.build_bind_data for more information on the contents of the
        bind data dictionary.
        @param id: identifies the consumer; a consumer with this ID must exist
        @type  id: string
        @param repoid: identifies the repo to bind; a repo with this ID must exist
        @type  repoid: string
        @return: dictionary containing details about the repo that will describe how
                 to use the bound repo; None if no binding took place
        @rtype:  dict
        @raise PulpException: if either the consumer or repo cannot be found
        '''

        # Parameter tests
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found' % id)

# <V2 Repo changes>
        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repoid)
        if repo is None:
            raise MissingResource(repoid)

#        repo = self.repoapi.repository(repoid)
#        if repo is None:
#            raise PulpException('Repo [%s] does not exist' % repoid)
# </V2 Repo changes>

        # Short circuit if the repo is already bound
        repoids = consumer.setdefault('repoids', [])
        if repoid in repoids:
            return None

        log.info('Bind consumer:%s, repoid: %s', id, repoid)

        # Update the consumer with the new repo, adding an entry to its history
        repoids.append(repoid)
        self.collection.save(consumer, safe=True)
        self.consumer_history_api.repo_bound(id, repoid)

# <V2 Repo changes>
        # Collect the necessary information to return to the caller (see __doc__ above)
        host_list = round_robin.generate_cds_urls(repoid)
#
#        # Retrieve the latest set of key names and contents and send to consumers
#        ks = KeyStore(repo['relative_path'])
#        gpg_keys = ks.keys_and_contents()
#        bind_data = consumer_utils.build_bind_data(repo, host_list, gpg_keys)
        bind_data = consumer_utils.build_bind_data(repo, hostnames=host_list, key_list=None)
# </V2 Repo changes>

        # Send the bind request over to the consumer only if bind()
        # is supported in capabilities
        capabilities = AgentCapabilities(consumer['capabilities'])
        if capabilities.bind():
            agent = PulpAgent(consumer, async=True, timeout=None)
            agent_consumer = agent.ConsumerXXX()
            agent_consumer.bind(repoid, bind_data)

        # Return the bind data to the caller
        return bind_data


    @audit()
    def unbind(self, id, repo_id):
        '''
        Unbinds a consumer from the given repo. If the consumer is not bound to the
        repo, this call has no effect.
        @param id: identifies the consumer; this must represent a consumer currently in the DB
        @type  id: string
        @param repo_id: identifies the repo being unbound
        @type  repo_id: string
        @raise PulpException: if the consumer cannot be found
        '''

        # Parameter test
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)

        # Short circuit if the repo isn't bound to the consumer
        repoids = consumer['repoids']
        if repo_id not in repoids:
            return

        log.info('Unbind consumer:%s, repoid: %s', id, repo_id)

        # Update the consumer entry in the DB
        repoids.remove(repo_id)
        self.collection.save(consumer, safe=True)

        # Send the bind request over to the consumer only if bind()
        # is supported in capabilities
        capabilities = AgentCapabilities(consumer['capabilities'])
        if capabilities.bind():
            agent = PulpAgent(consumer, async=True, timeout=None)
            agent_consumer = agent.ConsumerXXX()
            agent_consumer.unbind(repo_id)

        self.consumer_history_api.repo_unbound(id, repo_id)

    @audit(params=['id'])
    def profile_update(self, id, package_profile):
        """
        Update the consumer information such as package profile
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        consumer["package_profile"] = package_profile
        self.collection.save(consumer, safe=True)
        log.info('Successfully updated package profile for consumer %s' % id)

    @audit()
    def installpackages(self, id, names=()):
        """
        Install packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param names: The package names to install.
        @type names: [str,..]
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        task = Task(self.__installpackages, [id, names])
        return task

    def __installpackages(self, id, names, reboot=False, importkeys=False):
        """
        Task callback to install packages.
        @param id: The consumer ID.
        @type id: str
        @param names: A list of package names.
        @type names: list
        @param reboot: Reboot after package install.
        @type reboot: bool
        @param importkeys: Permit GPG keys to be imported as needed.
        @type importkeys: bool
        @return: Whatever the agent returns.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        agent = PulpAgent(consumer)
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(timeout=tm)
        packages(importkeys=importkeys)
        return packages.install(names, reboot)

    @audit()
    def uninstallpackages(self, id, names=()):
        """
        Uninstall packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param names: The package names to erase.
        @type names: [str,..]
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        task = Task(self.__uninstallpackages, [id, names])
        return task

    def __uninstallpackages(self, id, names):
        """
        Task callback to uninstall packages.
        @param id: The consumer ID.
        @type id: str
        @param names: A list of package names.
        @type names: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        agent = PulpAgent(consumer)
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(timeout=tm)
        return packages.uninstall(names)

    @audit()
    def updatepackages(self, id, names=()):
        """
        Update packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param names: The package names to update.  Empty means ALL.
        @type names: [str,..]
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        task = Task(self.__updatepackages, [id, names])
        return task

    def __updatepackages(self, id, names):
        """
        Task callback to install packages.
        @param id: The consumer ID.
        @type id: str
        @param names: A list of package names.  Empty means ALL.
        @type names: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        agent = PulpAgent(consumer)
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        packages = agent.Packages(timeout=tm)
        return packages.update(names)

    @audit()
    def installpackagegroups(self, id, grpids):
        """
        Install package groups on the consumer.
        @param id: A consumer id.
        @type id: str
        @param grpids: The package group ids to install.
        @type grpids: [str,..]
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        task = Task(self.__installpackagegroups, [id, grpids])
        return task

    def __installpackagegroups(self, id, grpids):
        """
        Task callback to install package groups.
        @param id: The consumer ID.
        @type id: str
        @param grpids: A list of package group names.
        @type v: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        agent = PulpAgent(consumer)
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        pkgrps = agent.PackageGroups(timeout=tm)
        return pkgrps.install(grpids)

    @audit()
    def uninstallpackagegroups(self, id, grpids):
        """
        Uninstall package groups on the consumer.
        @param id: A consumer id.
        @type id: str
        @param grpids: The package group ids to uninstall.
        @type grpids: [str,..]
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        task = Task(self.__uninstallpackagegroups, [id, grpids])
        return task

    def __uninstallpackagegroups(self, id, grpids):
        """
        Task callback to uninstall package groups.
        @param id: The consumer ID.
        @type id: str
        @param grpids: A list of package group names.
        @type v: list
        @return: Whatever the agent returns.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        agent = PulpAgent(consumer)
        tm = (10, 600) # start in 10 seconds, finish in 10 minutes
        pkgrps = agent.PackageGroups(timeout=tm)
        return pkgrps.uninstall(grpids)

    def installerrata(self, id, errataids=(), types=(), importkeys=False):
        """
        Install errata on the consumer.
        @param id: A consumer id.
        @type id: str
        @param errataids: The errata ids to install.
        @type errataids: [str,..]
        @param types: Errata type filter
        @type types: str
        """
        consumer = self.consumer(id)
        pkgs = []
        errata_titles = []
        reboot_suggested = False
        if errataids:
            applicable_errata = self._applicable_errata(consumer, types)
            rlist = []
            for eid in errataids:
                if self.errataapi.erratum(eid) is None:
                    raise Exception('Erratum [%s], not found' % eid)
                if eid not in applicable_errata.keys():
                    log.error("ErrataId %s is not part of applicable errata. Skipping" % eid)
                    continue
                errata_titles.append(eid)
                for pobj in applicable_errata[eid]['packages']:
                    if pobj["arch"] != "src":
                        pkgs.append(pobj["name"])
                rlist.append(applicable_errata[eid]['reboot_suggested'])
            if True in rlist:
                # if there is atleast one reboot_suggested=True, we trigger a reboot.
                reboot_suggested = True
        else:
            #apply all updates
            install_data = self.list_package_updates(id, types)
            pkgobjs = install_data['packages']
            reboot_suggested = install_data['reboot_suggested']
            for pobj in pkgobjs:
                if pobj["arch"] != "src":
                    pkgs.append(pobj["name"])
        if not len(pkgs):
            return None
        log.error("Packages to install [%s]" % pkgs)
        task = Task(
            self.__installpackages,
            [id, pkgs],
            dict(reboot=reboot_suggested,importkeys=importkeys))
        return task

    def listerrata(self, id, types=()):
        """
        List applicable errata for a given consumer id
        """
        consumer = self.consumer(id)
        consumer_errata = []
        for errataid in self._applicable_errata(consumer, types).keys():
            consumer_errata.append( self.errataapi.erratum(errataid))
        return consumer_errata

    def list_package_updates(self, id, types=()):
        """
        List applicable package updates for a given consumer id
        """
        consumer = self.consumer(id)
        applicable_errata = self._applicable_errata(consumer, types)
        pkglist = [ item for etype in applicable_errata.values() \
                                    for item in etype['packages'] ]
        return {'packages' : pkglist,
                'reboot_required' : self.check_reboot_required(applicable_errata)}

    def list_errata_package(self, id, types=()):
        consumer = self.consumer(id)
        applicable_errata = self._applicable_errata(consumer, types)
        pkglist = [ item for etype in applicable_errata.values() \
                                    for item in etype['packages'] ]
        elist = applicable_errata.keys()
        return {'packages' : pkglist,
                'errata'  : elist}

    def check_reboot_required(self, applicable_errata):
        reboot_suggested = False
        if True in [item['reboot_suggested'] for item in applicable_errata.values()]:
            # if there is atleast one reboot_suggested=True, we trigger a reboot.
            reboot_suggested = True
        return reboot_suggested

    def _applicable_errata(self, consumer, types=(), repoids=None):
        """
        Logic to filter applicable errata for a consumer
        """
        if repoids is None:
            repoids = consumer["repoids"]

        applicable_errata = {}
        pkg_profile = consumer["package_profile"]

        pkg_profile_dict = [dict(pkg) for pkg in pkg_profile]
        pkg_profile_names = [pkg['name'] for pkg in pkg_profile]
        #Compute applicable errata by subscribed repos

        errataids = [eid['id'] for repoid in repoids \
                     for eid in self.repoapi.errata(repoid, types) ]

        for erratumid in errataids:
            # compare errata packages to consumer package profile and
            # extract applicable errata
            erratum = self.errataapi.erratum(erratumid)
            for epkg in erratum["pkglist"]:
                for pkg in epkg["packages"]:
                    epkg_info = {
                                'name': pkg["name"],
                                'version': pkg["version"],
                                'arch': pkg["arch"],
                                'epoch': pkg["epoch"] or 0,
                                'release': pkg["release"],
                                }
                    if epkg_info['name'] not in pkg_profile_names:
                        #if errata pkg not in installed profile, update is not
                        # applicable move on
                        continue
                    for ppkg in pkg_profile_dict:
                        if epkg_info['name'] != ppkg['name']:
                            continue

                        status = compare_packages(epkg_info, ppkg)
                        if status == 1:
                            # erratum pkg is newer, add to update list
                            if not applicable_errata.has_key(erratumid):
                                applicable_errata[erratumid] = {'packages' : [],
                                                                'reboot_suggested' : erratum['reboot_suggested']}
                            applicable_errata[erratumid]['packages'].append(pkg)
        return applicable_errata
    


    @audit()
    def get_consumers_applicable_errata(self, repoids, send_only_applicable_errata='true'):
        """
        List all errata associated with a group of repositories along with consumers that it is applicable to
        """
        all_repo_errata = []

        # Get all errata ids from all given repositories
        for repoid in repoids:
            repo = self.repoapi.repository(repoid)
            if not repo:
                raise PulpException('Repository [%s] does not exist', repoid)
            for errata in repo['errata'].values():
                all_repo_errata.extend(errata)

        # Initialize applicable_errata_consumers with errata id and empty list of applicable consumers
        applicable_errata_consumers = {}
        for erratum in all_repo_errata:
            applicable_errata_consumers[erratum] = {}
            applicable_errata_consumers[erratum]['consumerids'] = []

        for repoid in repoids:
            registered_consumers = [ consumer for consumer in self.consumers() \
                                    if repoid in consumer['repoids']]

            repo_errataids = []
            repo = self.repoapi.repository(repoid)
            for errata in repo['errata'].values():
                repo_errataids.extend(errata)

            # for each consumer add itself to applicable_errata_consumers for applicable errata id
            for consumer in registered_consumers:
                applicable_errata = self._applicable_errata(consumer=consumer, repoids=[repoid])
                for repo_errataid in repo_errataids:
                    if repo_errataid in applicable_errata:
                        applicable_errata_consumers[repo_errataid]['consumerids'].append(consumer['id'])

        # if send_only_applicable_errata is true, remove all other errata
        if send_only_applicable_errata == 'true':
            for errataid, info in applicable_errata_consumers.items():
                if not info['consumerids']:
                    del applicable_errata_consumers[errataid]

        # add errata details
        for errataid, info in applicable_errata_consumers.items():
            e = self.errataapi.erratum(errataid, fields=['title','type','severity','repoids'])
            info['title'] = e['title']
            info['type'] = e['type']
            info['severity'] = e['severity']
            info['repoids'] = e['repoids']
            applicable_errata_consumers[errataid] = info

        return applicable_errata_consumers


