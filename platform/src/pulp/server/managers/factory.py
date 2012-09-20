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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Provides a loosely coupled way of retrieving references into other manager
instances. Test cases can manipulate this module to mock out the class of
manager returned for a given type to isolate and simulate edge cases such
as exceptions.

When changing manager class mappings for a test, be sure to call reset()
in the test clean up to restore the mappings to the defaults. Failing to
do so may indirectly break other tests.
"""


# -- constants ----------------------------------------------------------------

# Keys used to look up a specific builtin manager (please alphabetize)
TYPE_CDS                    = 'cds-manager'
TYPE_CERTIFICATE            = 'certificate-manager'
TYPE_CERT_GENERATION        = 'cert-generation-manager'
TYPE_CONSUMER               = 'consumer-manager'
TYPE_CONSUMER_AGENT         = 'consumer-agent-manager'
TYPE_CONSUMER_APPLICABILITY = 'consumer-applicability-manager'
TYPE_CONSUMER_BIND          = 'consumer-bind-manager'
TYPE_CONSUMER_CONTENT       = 'consumer-content-manager'
TYPE_CONSUMER_GROUP         = 'consumer-group-manager'
TYPE_CONSUMER_GROUP_QUERY   = 'consumer-group-query-manager'
TYPE_CONSUMER_HISTORY       = 'consumer-history-manager'
TYPE_CONSUMER_PROFILE       = 'consumer-profile-manager'
TYPE_CONSUMER_QUERY         = 'consumer-query-manager'
TYPE_CONTENT                = 'content-manager'
TYPE_CONTENT_ORPHAN         = 'content-orphan-manager'
TYPE_CONTENT_QUERY          = 'content-query-manager'
TYPE_CONTENT_UPLOAD         = 'content-upload-manager'
TYPE_DEPENDENCY             = 'dependencies-manager'
TYPE_EVENT_FIRE             = 'event-fire-manager'
TYPE_EVENT_LISTENER         = 'event-listener-manager'
TYPE_PASSWORD               = 'password-manager'
TYPE_PERMISSION             = 'permission-manager'
TYPE_PERMISSION_QUERY       = 'permission-query-manager'
TYPE_PLUGIN_MANAGER         = 'plugin-manager'
TYPE_PRINCIPAL              = 'principal'
TYPE_REPO                   = 'repo-manager'
TYPE_REPO_ASSOCIATION       = 'repo-association-manager'
TYPE_REPO_ASSOCIATION_QUERY = 'repo-association-query-manager'
TYPE_REPO_GROUP             = 'repo-group-manager'
TYPE_REPO_GROUP_DISTRIBUTOR = 'repo-group-distributor'
TYPE_REPO_GROUP_PUBLISH     = 'repo-group-publish'
TYPE_REPO_GROUP_QUERY       = 'repo-group-query-manager'
TYPE_REPO_IMPORTER          = 'repo-importer-manager'
TYPE_REPO_DISTRIBUTOR       = 'repo-distributor-manager'
TYPE_REPO_PUBLISH           = 'repo-publish-manager'
TYPE_REPO_QUERY             = 'repo-query-manager'
TYPE_REPO_SYNC              = 'repo-sync-manager'
TYPE_ROLE                   = 'role-manager'
TYPE_ROLE_QUERY             = 'role-query-manager'
TYPE_SCHEDULE               = 'schedule-manager'
TYPE_TOPIC_PUBLISH          = 'topic-publish-manager'
TYPE_USER                   = 'user-manager'
TYPE_USER_QUERY             = 'user-query-manager'


# Mapping of key to class that will be instantiated in the factory method
# Initialized to a copy of the defaults so changes won't break the defaults
_CLASSES = {}

# Mapping of key to a particular instance that will be returned by the factory
# method. This should only be used for testing purposes to inject a mock object.
_INSTANCES = {}

# -- exceptions ---------------------------------------------------------------

class InvalidType(Exception):
    """
    Raised when a manager type is requested that has no class mapping.
    """

    def __init__(self, type_key):
        Exception.__init__(self)
        self.type_key = type_key

    def __str__(self):
        return 'Invalid manager type requested [%s]' % self.type_key

# -- manager retrieval --------------------------------------------------------

# When adding these syntactic sugar methods, please use the @rtype tag to make
# sure IDEs can correctly guess at the returned type and provide auto-complete.

# Be sure to add an entry to test_syntactic_sugar_methods in test_manager_factory.py
# to verify the correct type of manager is returned.

def certificate_manager(content=None):
    """
    @rtype: L{pulp.server.managers.auth.cert.certificate.CertificateManager}
    """
    return get_manager(TYPE_CERTIFICATE, content)


def cert_generation_manager():
    """
    @rtype: L{pulp.server.managers.auth.cert.cert_generator.CertGenerationManager}
    """
    return get_manager(TYPE_CERT_GENERATION)

def consumer_manager():
    """
    @rtype: L{pulp.server.managers.consumer.cud.ConsumerManager}
    """
    return get_manager(TYPE_CONSUMER)

def consumer_agent_manager():
    """
    @rtype: L{pulp.server.managers.consumer.agent.AgentManager}
    """
    return get_manager(TYPE_CONSUMER_AGENT)

def consumer_applicability_manager():
    """
    @rtype: L{pulp.server.managers.consumer.applicability.ApplicabilityManager}
    """
    return get_manager(TYPE_CONSUMER_APPLICABILITY)

def consumer_bind_manager():
    """
    @rtype: L{pulp.server.managers.consumer.bind.BindManager}
    """
    return get_manager(TYPE_CONSUMER_BIND)

def consumer_content_manager():
    """
    @rtype: L{pulp.server.managers.consumer.content.ConsumerContentManager}
    """
    return get_manager(TYPE_CONSUMER_CONTENT)

def consumer_group_manager():
    """
    @rtype: L{pulp.server.managers.consumer.group.ConsumerGroupManager}
    """
    return get_manager(TYPE_CONSUMER_GROUP)

def consumer_group_query_manager():
    """
    @rtype: L{pulp.server.managers.consumer.group.ConsumerGroupQueryManager}
    """
    return get_manager(TYPE_CONSUMER_GROUP_QUERY)

def consumer_query_manager():
    """
    @rtype: L{pulp.server.managers.consumer.query.ConsumerQueryManager}
    """
    return get_manager(TYPE_CONSUMER_QUERY)

def consumer_history_manager():
    """
    @rtype: L{pulp.server.managers.consumer.history.ConsumerHistoryManager}
    """
    return get_manager(TYPE_CONSUMER_HISTORY)

def consumer_profile_manager():
    """
    @rtype: L{pulp.server.managers.consumer.profile.ConsumerProfileManager}
    """
    return get_manager(TYPE_CONSUMER_PROFILE)

def content_manager():
    """
    @rtype: L{pulp.server.managers.content.cud.ContentManager}
    """
    return get_manager(TYPE_CONTENT)

def content_orphan_manager():
    """
    @rtype: L{pulp.server.managers.content.orphan.OrphanManager}
    """
    return get_manager(TYPE_CONTENT_ORPHAN)

def content_query_manager():
    """
    @rtype: L{pulp.server.managers.content.query.ContentQueryManager}
    """
    return get_manager(TYPE_CONTENT_QUERY)

def content_upload_manager():
    """
    @rtype: L{pulp.server.managers.content.upload.ContentUploadManager}
    """
    return get_manager(TYPE_CONTENT_UPLOAD)

def dependency_manager():
    """
    @rtype: L{pulp.server.managers.repo.dependency.DependencyManager}
    """
    return get_manager(TYPE_DEPENDENCY)

def event_fire_manager():
    """
    @rtype: L{pulp.server.managers.event.fire.EventFireManager}
    """
    return get_manager(TYPE_EVENT_FIRE)

def event_listener_manager():
    """
    @rtype: L{pulp.server.managers.event.crud.EventListenerManager}
    """
    return get_manager(TYPE_EVENT_LISTENER)

def password_manager():
    """
    @rtype: L{pulp.server.managers.auth.password.PasswordManager}
    """
    return get_manager(TYPE_PASSWORD)

def permission_manager():
    """
    @rtype: L{pulp.server.managers.auth.permission.cud.PermissionManager}
    """
    return get_manager(TYPE_PERMISSION)

def permission_query_manager():
    """
    @rtype: L{pulp.server.managers.auth.permission.query.PermissionQueryManager}
    """
    return get_manager(TYPE_PERMISSION_QUERY)

def plugin_manager():
    """
    @rtype: L{pulp.server.managers.plugin.PluginManager}
    """
    return get_manager(TYPE_PLUGIN_MANAGER)

def principal_manager():
    """
    @rtype: L{pulp.server.managers.auth.principal.PrincipalManager}
    """
    return get_manager(TYPE_PRINCIPAL)

def repo_group_manager():
    """
    @rtype: L{pulp.server.managers.repo.group.cud.RepoGroupManager}
    """
    return get_manager(TYPE_REPO_GROUP)

def repo_group_distributor_manager():
    """
    @rtype: L{pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager}
    """
    return get_manager(TYPE_REPO_GROUP_DISTRIBUTOR)

def repo_group_publish_manager():
    """
    @rtype: L{pulp.server.managers.repo.group.publish.RepoGroupPublishManager}
    """
    return get_manager(TYPE_REPO_GROUP_PUBLISH)

def repo_group_query_manager():
    """
    @rtype: L{pulp.server.managers.repo.group.query.RepoGroupQueryManager}
    """
    return get_manager(TYPE_REPO_GROUP_QUERY)

def repo_manager():
    """
    @rtype: L{pulp.server.managers.repo.cud.RepoManager}
    """
    return get_manager(TYPE_REPO)

def repo_importer_manager():
    """
    @rtype: L{pulp.server.managers.repo.importer.RepoImporterManager}
    """
    return get_manager(TYPE_REPO_IMPORTER)

def repo_distributor_manager():
    """
    @rtype: L{pulp.server.managers.repo.distributor.RepoDistributorManager}
    """
    return get_manager(TYPE_REPO_DISTRIBUTOR)

def repo_unit_association_manager():
    """
    @rtype: L{pulp.server.managers.repo.unit_association.RepoUnitAssociationManager}
    """
    return get_manager(TYPE_REPO_ASSOCIATION)

def repo_unit_association_query_manager():
    """
    @rtype: L{pulp.server.managers.repo.unit_association_query.RepoUnitAssociationQueryManager}
    """
    return get_manager(TYPE_REPO_ASSOCIATION_QUERY)

def repo_publish_manager():
    """
    @rtype: L{pulp.server.managers.repo.publish.RepoPublishManager}
    """
    return get_manager(TYPE_REPO_PUBLISH)

def repo_query_manager():
    """
    @rtype: L{pulp.server.managers.repo.query.RepoQueryManager}
    """
    return get_manager(TYPE_REPO_QUERY)

def repo_sync_manager():
    """
    @rtype: L{pulp.server.managers.repo.sync.RepoSyncManager}
    """
    return get_manager(TYPE_REPO_SYNC)

def role_manager():
    """
    @rtype: L{pulp.server.managers.auth.role.cud.RoleManager}
    """
    return get_manager(TYPE_ROLE)

def role_query_manager():
    """
    @rtype: L{pulp.server.managers.auth.role.query.RoleQueryManager}
    """
    return get_manager(TYPE_ROLE_QUERY)

def schedule_manager():
    """
    @rtype: L{pulp.server.managers.schedule.aggregate.AggregateScheduleManager}
    """
    return get_manager(TYPE_SCHEDULE)

def topic_publish_manager():
    """
    @rtype: L{pulp.server.managers.event.remote.TopicPublishManager}
    """
    return get_manager(TYPE_TOPIC_PUBLISH)

def user_manager():
    """
    @rtype: L{pulp.server.managers.auth.user.cud.UserManager}
    """
    return get_manager(TYPE_USER)

def user_query_manager():
    """
    @rtype: L{pulp.server.managers.auth.user.query.UserQueryManager}
    """
    return get_manager(TYPE_USER_QUERY)

# -- other --------------------------------------------------------------------

def initialize():
    """
    Initialize the manager factory by importing and setting Pulp's builtin
    (read: default) managers.
    """
    # imports for individual managers to prevent circular imports
    from pulp.server.managers.auth.cert.certificate import CertificateManager
    from pulp.server.managers.auth.cert.cert_generator import CertGenerationManager
    from pulp.server.managers.auth.principal import PrincipalManager
    from pulp.server.managers.auth.user.cud import UserManager
    from pulp.server.managers.auth.user.query import UserQueryManager
    from pulp.server.managers.auth.password import PasswordManager
    from pulp.server.managers.auth.permission.cud import PermissionManager
    from pulp.server.managers.auth.permission.query import PermissionQueryManager
    from pulp.server.managers.auth.role.cud import RoleManager
    from pulp.server.managers.auth.role.query import RoleQueryManager
    from pulp.server.managers.consumer.cud import ConsumerManager
    from pulp.server.managers.consumer.agent import AgentManager
    from pulp.server.managers.consumer.applicability import ApplicabilityManager
    from pulp.server.managers.consumer.bind import BindManager
    from pulp.server.managers.consumer.content import ConsumerContentManager
    from pulp.server.managers.consumer.group.cud import ConsumerGroupManager
    from pulp.server.managers.consumer.group.query import ConsumerGroupQueryManager
    from pulp.server.managers.consumer.history import ConsumerHistoryManager
    from pulp.server.managers.consumer.profile import ProfileManager
    from pulp.server.managers.consumer.query import ConsumerQueryManager
    from pulp.server.managers.content.cud import ContentManager
    from pulp.server.managers.content.orphan import OrphanManager
    from pulp.server.managers.content.query import ContentQueryManager
    from pulp.server.managers.content.upload import ContentUploadManager
    from pulp.server.managers.event.crud import EventListenerManager
    from pulp.server.managers.event.fire import EventFireManager
    from pulp.server.managers.event.remote import TopicPublishManager
    from pulp.server.managers.plugin import PluginManager
    from pulp.server.managers.repo.cud import RepoManager
    from pulp.server.managers.repo.dependency import DependencyManager
    from pulp.server.managers.repo.distributor import RepoDistributorManager
    from pulp.server.managers.repo.group.cud import RepoGroupManager
    from pulp.server.managers.repo.group.distributor import RepoGroupDistributorManager
    from pulp.server.managers.repo.group.publish import RepoGroupPublishManager
    from pulp.server.managers.repo.group.query import RepoGroupQueryManager
    from pulp.server.managers.repo.importer import RepoImporterManager
    from pulp.server.managers.repo.publish import RepoPublishManager
    from pulp.server.managers.repo.query import RepoQueryManager
    from pulp.server.managers.repo.sync import RepoSyncManager
    from pulp.server.managers.repo.unit_association import RepoUnitAssociationManager
    from pulp.server.managers.repo.unit_association_query import RepoUnitAssociationQueryManager
    from pulp.server.managers.schedule.aggregate import AggregateScheduleManager

    # Builtins for a normal running Pulp server (used to reset the state of the
    # factory between runs)
    builtins = {
        TYPE_CERTIFICATE : CertificateManager,
        TYPE_CERT_GENERATION: CertGenerationManager,
        TYPE_CONSUMER: ConsumerManager,
        TYPE_CONSUMER_AGENT: AgentManager,
        TYPE_CONSUMER_APPLICABILITY: ApplicabilityManager,
        TYPE_CONSUMER_BIND: BindManager,
        TYPE_CONSUMER_CONTENT: ConsumerContentManager,
        TYPE_CONSUMER_GROUP: ConsumerGroupManager,
        TYPE_CONSUMER_GROUP_QUERY: ConsumerGroupQueryManager,
        TYPE_CONSUMER_HISTORY: ConsumerHistoryManager,
        TYPE_CONSUMER_PROFILE: ProfileManager,
        TYPE_CONSUMER_QUERY: ConsumerQueryManager,
        TYPE_CONTENT: ContentManager,
        TYPE_CONTENT_ORPHAN: OrphanManager,
        TYPE_CONTENT_QUERY: ContentQueryManager,
        TYPE_CONTENT_UPLOAD: ContentUploadManager,
        TYPE_DEPENDENCY: DependencyManager,
        TYPE_EVENT_FIRE: EventFireManager,
        TYPE_EVENT_LISTENER: EventListenerManager,
        TYPE_PASSWORD: PasswordManager,
        TYPE_PERMISSION: PermissionManager,
        TYPE_PERMISSION_QUERY: PermissionQueryManager,
        TYPE_PLUGIN_MANAGER: PluginManager,
        TYPE_PRINCIPAL: PrincipalManager,
        TYPE_REPO: RepoManager,
        TYPE_REPO_ASSOCIATION: RepoUnitAssociationManager,
        TYPE_REPO_ASSOCIATION_QUERY : RepoUnitAssociationQueryManager,
        TYPE_REPO_DISTRIBUTOR: RepoDistributorManager,
        TYPE_REPO_GROUP: RepoGroupManager,
        TYPE_REPO_GROUP_DISTRIBUTOR : RepoGroupDistributorManager,
        TYPE_REPO_GROUP_PUBLISH : RepoGroupPublishManager,
        TYPE_REPO_GROUP_QUERY : RepoGroupQueryManager,
        TYPE_REPO_IMPORTER: RepoImporterManager,
        TYPE_REPO_PUBLISH: RepoPublishManager,
        TYPE_REPO_QUERY: RepoQueryManager,
        TYPE_REPO_SYNC: RepoSyncManager,
        TYPE_ROLE: RoleManager,
        TYPE_ROLE_QUERY: RoleQueryManager,
        TYPE_SCHEDULE: AggregateScheduleManager,
        TYPE_TOPIC_PUBLISH: TopicPublishManager,
        TYPE_USER: UserManager,
        TYPE_USER_QUERY: UserQueryManager,
    }
    _CLASSES.update(builtins)


def get_manager(type_key, init_args=None):
    """
    Returns a manager instance of the given type according to the current
    manager class mappings.

    This can be called directly, but the preferred method for retrieving managers
    is to use the syntactic sugar methods in this module.

    @param type_key: identifies the manager being requested; should be one of
                     the TYPE_* constants in this module
    @type  type_key: str

    @return: manager instance that (should) adhere to the expected API for
             managers of the requested type
    @rtype:  some sort of object  :)

    @raises InvalidType: if there is no class mapping for the requested type
    """

    if type_key not in _CLASSES:
        raise InvalidType(type_key)

    # If a specific object is provided, return that
    if type_key in _INSTANCES:
        return _INSTANCES[type_key]

    cls = _CLASSES[type_key]
    if init_args:
        manager = cls(init_args)
    else:
        manager = cls()

    return manager


def register_manager(type_key, manager_class):
    """
    Sets the manager class for the given type key, either replacing the existing
    mapping or creating a new one.

    @param type_key: identifies the manager type
    @type  type_key: str

    @param manager_class: class to instantiate when requesting a manager of the
                          type specified in type_key
    @type  manager_class: class
    """

    _CLASSES[type_key] = manager_class


def reset():
    """
    Resets the type to class mappings back to the defaults. This should be called
    in test cleanup to prepare the state for other test runs.
    """

    global _INSTANCES
    _INSTANCES = {}

    global _CLASSES
    _CLASSES = {}
    initialize()

