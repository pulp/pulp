# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

from pulp.server.api.base import BaseApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.async import AsyncAgent, AgentTask
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)


class ConsumerGroupApi(BaseApi):

    def __init__(self):
        self.consumerApi = ConsumerApi()
        self.repoApi = RepoApi()

    def _getcollection(self):
        return model.ConsumerGroup.get_collection()


    @audit(params=['id', 'consumerids'])
    def create(self, id, description, consumerids=[]):
        """
        Create a new ConsumerGroup object and return it
        """
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
        repo = self.repoApi.repository(repoid)
        if repo is None:
            raise PulpException("No Repository with id: %s found" % repoid)

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
        repo = self.repoApi.repository(repoid)
        if (repo is None):
            raise PulpException("No Repository with id: %s found" % repoid)

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
    def add_key_value_pair(self, id, key, value, force):
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
    def installpackages(self, id, packagenames=[]):
        """
        Install packages on the consumers in a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        items = []
        for consumerid in consumergroup['consumerids']:
            install_data = {"consumerid" : consumerid,
                            "packages"   : packagenames,
                            "reboot_suggested" : False,
                            "assumeyes"  : False}
            items.append(install_data)
        task = InstallPackages(items)
        return task

    def installerrata(self, id, errataids=[], types=[], assumeyes=False):
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
        items = []
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            pkgs = []
            reboot_suggested = False
            if errataids:
                applicable_errata = self.consumerApi._applicable_errata(consumer, types)
                rlist = []
                for eid in errataids:
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
            log.error("Foe consumer id %s Packages to install %s" % (consumerid, pkgs))
            install_data = {"consumerid" : consumerid,
                            "packages"   : pkgs,
                            "reboot_suggested" : reboot_suggested,
                            "assumeyes"  : assumeyes}
            items.append(install_data)
        task = InstallErrata(items)
        return task


class InstallPackages(AgentTask):
    """
    Install packages task
    @ivar items: The list of tuples (consumerid, [package,..]).
    @type items: list]
    @ivar serials: A dict of RMI serial # to consumer ids.
    @type serials: dict.
    @ivar __succeeded: A list of succeeded RMI.
    @type __succeeded: tuple (consumerid, result)
    @ivar __failed: A list of failed RMI.
    @type __failed: tuple (consumerid, exception)
    """

    def __init__(self, items, errata=()):
        """
        @param items: The list of tuples (consumerid, [package,..]).
        @type items: list
        @param errata: A list of errata titles.
        @type errata: list
        """
        self.items = items
        self.errata = errata
        self.serials = {}
        self.__succeeded = []
        self.__failed = []
        AgentTask.__init__(self, self.install)
        self._enqueue()

    def install(self):
        """
        Perform the RMI to the agent to install packages.
        """
        for item in self.items:
            agent = AsyncAgent(item['consumerid'])
            packages = agent.Packages(self)
            sn = packages.install(item['packages'], item['reboot_suggested'], item['assumeyes'])
            self.serials[sn] = item['consumerid']

    def succeeded(self, sn, result):
        """
        The agent RMI Succeeded.
        Find the consumer id using the serial number.  Then, append the
        result to the succeeded list and check to see if we have all
        of the replies (finished).
        @param sn: The RMI serial #.
        @type sn: uuid
        @param result: The object returned by the RMI call.
        @type result: object
        """
        id = self.serials.get(sn)
        if not id:
            log.error('serial %s, not found', sn)
            return
        self.__succeeded.append((id, result))
        self.__finished()

    def failed(self, sn, exception, tb=None):
        """
        The agent RMI Failed.
        Find the consumer id using the serial number.  Then, append the
        exception and traceback to the failed list and check to see if
        we have all of the replies (finished).
        @param sn: The RMI serial #.
        @type sn: uuid
        @param exception: The I{representation} of the raised exception.
        @type exception: str
        @param tb: The formatted traceback.
        @type tb: str
        """
        id = self.serials.get(sn)
        if not id:
            log.error('serial %s, not found', sn)
            return
        self.__failed.append((id, exception, tb))
        self.__finished()

    def __finished(self):
        """
        See if were finished.
        @param reply: An RMI reply object.
        @type reply: Reply
        """
        total = len(self.serials)
        total -= len(self.__succeeded)
        total -= len(self.__failed)
        if total: # still have outstanding replies
            return
        result = (self.__succeeded, self.__failed)
        AgentTask.succeeded(self, None, result)
        chapi = ConsumerHistoryApi()
        for id, result in self.__succeeded:
            chapi.packages_installed(
                    id,
                    result,
                    errata_titles=self.errata)


class InstallErrata(InstallPackages):
    """
    Install errata task.
    """
    pass
