# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from copy import deepcopy
import datetime

from pulp.server.db.model.base import Model
from pulp.common import dateutils

# -- classes -----------------------------------------------------------------

class Consumer(Model):
    """
    Represents a consumer of the content on Pulp server.

    @ivar consumer_id: uniquely identifies the consumer
    @type consumer_id: str

    @ivar display_name: user-friendly name of the consumer
    @type display_name: str

    @ivar description: user-friendly description of the consumer
    @type description: str

    @ivar notes: arbitrary key-value pairs programmatically describing the consumer
    @type notes: dict

    @param capabilities: operations permitted on the consumer
    @type capabilities: dict

    @param certificate: x509 certificate for the consumer
    @type certificate: str
    """

    collection_name = 'consumers'
    unique_indices = ('id',)
    search_indices = ('notes',)

    def __init__(self, consumer_id, display_name, description=None, notes=None, capabilities=None, certificate=None):
        super(Consumer, self).__init__()

        self.id = consumer_id
        self.display_name = display_name
        self.description = description
        self.notes = notes or {}

        self.capabilities = capabilities or {}
        self.certificate = certificate or None


class Bind(Model):
    """
    Represents consumer binding to a repo/distributor.

    Each consumer action entry will be of the format: {id:<str>, action:<str>, status:<str>}
    * Status: (pending|succeeded|failed)
    * Action: (bind|unbind)

    :ivar consumer_id: uniquely identifies the consumer.
    :type consumer_id: str
    :ivar repo_id: uniquely identifies the repository
    :type repo_id: str
    :ivar distributor_id: uniquely identifies a distributor
    :type distributor_id: str
    :ivar notify_agent: indicates if the agent should be sent a message informing it of the binding
    :type notify_agent: bool
    :ivar binding_config: value only applicable to this particular binding
    :type binding_config: object
    :ivar consumer_actions: tracks consumer bind/unbind actions; see above for format
    :ivar deleted: indicates the bind has been deleted
    :type deleted: bool
    """
    collection_name = 'consumer_bindings'
    unique_indices = (
        ('repo_id', 'distributor_id', 'consumer_id'),
    )
    search_indices = (
        ('consumer_id',),
    )

    class Action:
        # enumerated actions
        BIND = 'bind'
        UNBIND = 'unbind'

    class Status:
        # enumerated status
        PENDING = 'pending'
        SUCCEEDED = 'succeeded'
        FAILED = 'failed'

    def __init__(self, consumer_id, repo_id, distributor_id, notify_agent, binding_config):
        """
        :param consumer_id: uniquely identifies the consumer.
        :type consumer_id: str
        :param repo_id: uniquely identifies the repository.
        :type repo_id: str
        :param distributor_id: uniquely identifies a distributor.
        :type distributor_id: str
        :ivar notify_agent: controls whether or not the consumer agent will be sent a message
                            about the binding
        ;type notify_agent: bool
        :ivar binding_config: configuration to pass the distributor during payload creation for this
                              binding
        :type binding_config: object
        """
        super(Bind, self).__init__()

        # Required, Unique
        self.consumer_id = consumer_id
        self.repo_id = repo_id
        self.distributor_id = distributor_id

        # Configuration
        self.notify_agent = notify_agent
        self.binding_config = binding_config

        # State
        self.consumer_actions = []
        self.deleted = False


class UnitProfile(Model):
    """
    Represents a consumer profile, which is a data structure that records which content is installed
    on a particular consumer for a particular type.

    Due to the nature of the data conversion used to generate a profile's hash, it is impossible for
    Pulp to know if the ordering of list structures found in the profile are significant or
    not. Therefore, the hash of a list must assume that the ordering of the list is significant. The
    SON objects that Pulp stores in the database cannot contain Python sets.

    It is up to the plugin Profilers to handle this limitation if they wish to store lists in
    the database in such a way that the order shouldn't matter for hash comparison purposes. In
    these cases, the Profiler must order the list in some repeatable manner, so that any two
    profiles that it wants the platform to consider as being the same will have exactly the same
    ordering to those lists.

    For example, the RPM profile contains a list of dictionaries, where each dictionary contains
    information about RPMs stored on a consumer. The order of the list is not important for the
    purpose of determining what is installed on the system - it might as well be a set. However,
    since a set cannot be stored in MongoDB, it is up to the RPM Profiler to sort the list of
    installed RPMs in some repeatable fashion, such that any two consumers that have exactly the
    same RPMs installed will end up with the same ordering of their RPMs in the database.

    :param consumer_id:  A consumer ID.
    :type  consumer_id:  str
    :param content_type: The profile (unit) type ID.
    :type  content_type: str
    :param profile:      The stored profile.
    :type  profile:      object
    """

    collection_name = 'consumer_unit_profiles'
    unique_indices = (
        ('consumer_id', 'content_type'),
    )

    def __hash__(self):
        """
        Return a custom hash of self.profile. Since self.profile can be any serializable type, and
        since not all serializable types are hashable, this method converts the profile to a
        hashable representation of the profile, and then hashes that. This hash is useful for
        quickly comparing profiles to determine if they are the same.

        :return: Hash of self.profile
        :rtype:  int
        """
        hashable_profile = self._convert_to_hashable(self.profile)
        return hash(hashable_profile)

    def __init__(self, consumer_id, content_type, profile):
        """
        :param consumer_id:  A consumer ID.
        :type  consumer_id:  str
        :param content_type: The profile (unit) type ID.
        :type  content_type: str
        :param profile:      The stored profile.
        :type  profile:      object
        """
        super(UnitProfile, self).__init__()
        self.consumer_id = consumer_id
        self.content_type = content_type
        self.profile = profile

    @staticmethod
    def _convert_to_hashable(unhashable_object):
        """
        This method will convert the profile attribute of the UnitProfile into a hashable
        representation. It will traverse list, tuple, or dictionary structures, ensuring that all
        the types represented in them are also converted to hashable types.

        Lists will be converted to tuples. Dictionaries will be converted into frozensets of tuples,
        representing the keys and values found in them. Only lists and dicts get converted.

        Note that this method does not attempt to convert any possible type, but only those
        explicitly documented above. All types that are the Python equivalent of the allowed JSON
        types[0] are supported, though not all are converted.

        [0] int, float, str, bool, None, list, dict

        :param unhashable_object: Some object that is not hashable that you need a hashable
                                  representation of
        :type  unhashable_object: object
        :return:                  A hashable representation of self.profile
        :rtype:                   object
        """
        unhashable_object = deepcopy(unhashable_object)
        if isinstance(unhashable_object, tuple) or isinstance(unhashable_object, list):
            unhashable_object = list(unhashable_object)
            for i, item in enumerate(unhashable_object):
                unhashable_object[i] = UnitProfile._convert_to_hashable(item)
            unhashable_object = tuple(unhashable_object)
        elif isinstance(unhashable_object, dict):
            for key, value in unhashable_object.items():
                unhashable_object[key] = UnitProfile._convert_to_hashable(value)
            unhashable_object = frozenset(unhashable_object.items())
        return unhashable_object


class ConsumerHistoryEvent(Model):
    """
    Represents a consumer history event.

    @ivar consumer_id: identifies the consumer
    @type consumer_id: str

    @ivar originator: consumer or username of the admin who initiated the event
    @type originator: str

    @param type: event type
                 current supported event types: 'consumer_registered', 'consumer_unregistered', 'repo_bound', 'repo_unbound',
                 'content_unit_installed', 'content_unit_uninstalled', 'unit_profile_changed', 'added_to_group', 'removed_from_group'
    @type  type: str

    @param details: event details
    @type details: dict
    """
    collection_name = 'consumer_history'
    search_indices = ('consumer_id', 'originator', 'type', )

    def __init__(self, consumer_id, originator, event_type, details):
        super(ConsumerHistoryEvent, self).__init__()

        self.consumer_id = consumer_id
        self.originator = originator
        self.type = event_type
        self.details = details
        now = datetime.datetime.now(dateutils.utc_tz())
        self.timestamp = dateutils.format_iso8601_datetime(now)

class ConsumerGroup(Model):
    """
    Represents a group of consumers.
    """
    collection_name = 'consumer_groups'
    search_indices = ('display_name', 'consumer_ids')

    def __init__(self, consumer_group_id, display_name=None, description=None, 
            consumer_ids=None, notes=None):
        super(ConsumerGroup, self).__init__()

        self.id = consumer_group_id
        self.display_name = display_name
        self.description = description
        self.consumer_ids = consumer_ids or []
        self.notes = notes or {}

        self.scratchpad = None
