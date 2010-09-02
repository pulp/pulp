#!/usr/bin/python
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

import logging

# Pulp
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.agent import Agent
from pulp.server.api.base import BaseApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.pexceptions import PulpException
from pulp.server.util import chunks, compare_packages


log = logging.getLogger(__name__)
    
consumer_fields = model.Consumer(None, None).keys()


class ConsumerApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.errataapi  = ErrataApi()
        self.repoapi    = RepoApi()
        self.packageapi = PackageApi()
        self.consumer_history_api = ConsumerHistoryApi()

    def _getcollection(self):
        return get_object_db('consumers',
                             self._unique_indexes,
                             self._indexes)

    @property
    def _unique_indexes(self):
        return ["id"]

    @property
    def _indexes(self):
        return ["package_profile.name", "repoids"]

    @audit(params=['id'])
    def create(self, id, description):
        """
        Create a new Consumer object and return it
        """
        consumer = self.consumer(id)
        if(consumer):
            raise PulpException("Consumer [%s] already exists" % id)
        c = model.Consumer(id, description)
        self.insert(c)
        return c
    
    @audit()
    def delete(self, id):
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] does not exist', id)
        self.objectdb.remove(consumer, safe=True)
    
    @audit()
    def certificate(self, id):
        """
        Create a X509 Consumer Identity Certificate to associate with the 
        given Consumer 
        """
        consumer = self.consumer(id)
        if not consumer:
            raise PulpException('Consumer [%s] not found', id)
        private_key, cert = cert_generator.make_cert(id)
        return (private_key, cert) 
        
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
            self.objectdb.insert(chunk, check_keys=False, safe=False)
            inserted = inserted + chunksize

    def consumers(self, spec=None, fields=None):
        """
        List all consumers.  Can be quite large
        """
        return list(self.objectdb.find(spec=spec, fields=fields))

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
            #consumers.extend(self.objectdb.find({'package_profile.name': name}, fields))
            consumers.extend(self.consumers({'package_profile.name': name}, fields))
        return consumers

    @audit()
    def bind(self, id, repoid):
        """
        Bind (subscribe) a consumer to a repo.
        @param id: A consumer id.
        @type id: str
        @param repoid: A repo id to bind.
        @type repoid: str
        @raise PulpException: When consumer not found.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        repoids = consumer.setdefault('repoids', [])
        if repoid in repoids:
            return
        repoids.append(repoid)
        self.update(consumer)

    @audit()
    def unbind(self, id, repoid):
        """
        Unbind (unsubscribe) a consumer to a repo.
        @param id: A consumer id.
        @type id: str
        @param repoid: A repo id to unbind.
        @type repoid: str
        @raise PulpException: When consumer not found.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        repoids = consumer.setdefault('repoids', [])
        if repoid not in repoids:
            return
        repoids.remove(repoid)
        self.update(consumer)
        
    @audit(params=['id'])
    def profile_update(self, id, package_profile):
        """
        Update the consumer information such as package profile
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('Consumer [%s] not found', id)
        consumer["package_profile"] =  package_profile
        self.update(consumer)

    @audit()
    def installpackages(self, id, packagenames=()):
        """
        Install packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        agent = Agent(id)
        data = []
        for pkg in packagenames:
            info = pkg.split('.')
            if len(info) > 1:
                data.append(('.'.join(info[:-1]), info[-1]))
            else:
                data.append(pkg)
        log.debug("Packages to Install: %s" % data)
        return agent.packages.install(data)
    
    @audit()
    def installpackagegroups(self, id, packageids=()):
        """
        Install package groups on the consumer.
        @param id: A consumer id.
        @type id: str
        @param packageids: The package ids to install.
        @type packageids: [str,..]
        """
        agent = Agent(id)
        agent.packagegroups.install(packageids)
        return packageids
    
    def installerrata(self, id, errataids=(), types=()):
        """
        Install errata on the consumer.
        @param id: A consumer id.
        @type id: str
        @param errataids: The errata ids to install.
        @type errataids: [str,..]
        @param types: Errata type filter
        @type types: str
        """
        agent = Agent(id)
        consumer = self.consumer(id)
        pkgs = []
        if errataids:
            applicable_errata = self._applicable_errata(consumer, types)
            for eid in errataids:
                for pobj in applicable_errata[eid]:
                    if pobj["arch"] != "src":
                        pkgs.append(pobj["name"])
        else:
            #apply all updates
            pkgobjs = self.list_package_updates(id, types)
            for pobj in pkgobjs:
                if pobj["arch"] != "src":
                    pkgs.append(pobj["name"])
        log.error("Packages to install [%s]" % pkgs)
        agent.packages.install(pkgs)
        return pkgs
        
    def listerrata(self, id, types=()):
        """
        List applicable errata for a given consumer id
        """
        consumer = self.consumer(id)
        return self._applicable_errata(consumer, types).keys()
    
    def list_package_updates(self, id, types=()):
        """
        List applicable package updates for a given consumer id
        """
        consumer = self.consumer(id)
        return [ item for etype in self._applicable_errata(consumer, types).values() \
                for item in etype ]
    
    def _applicable_errata(self, consumer, types=()):
        """ 
        Logic to filter applicable errata for a consumer
        """
        applicable_errata = {}
        pkg_profile = consumer["package_profile"]

        pkg_profile_dict = [dict(pkg) for pkg in pkg_profile]
        pkg_profile_names = [pkg['name'] for pkg in pkg_profile]

        #Compute applicable errata by subscribed repos
        errataids = [eid for repoid in consumer["repoids"] \
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
                                applicable_errata[erratumid] = []
                            applicable_errata[erratumid].append(pkg)
        return applicable_errata
