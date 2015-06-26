from pulp.bindings import auth, consumer, consumer_groups, repo_groups, repository
from pulp.bindings.actions import ActionsAPI
from pulp.bindings.content import OrphanContentAPI, ContentSourceAPI, ContentCatalogAPI
from pulp.bindings.event_listeners import EventListenerAPI
from pulp.bindings.server_info import ServerInfoAPI, ServerStatusAPI
from pulp.bindings.tasks import TasksAPI, TaskSearchAPI
from pulp.bindings.upload import UploadAPI


class Bindings(object):

    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """

        # Please keep the following in alphabetical order to ease reading
        self.actions = ActionsAPI(pulp_connection)
        self.bind = consumer.BindingsAPI(pulp_connection)
        self.bindings = consumer.BindingSearchAPI(pulp_connection)
        self.profile = consumer.ProfilesAPI(pulp_connection)
        self.consumer = consumer.ConsumerAPI(pulp_connection)
        self.consumer_content = consumer.ConsumerContentAPI(pulp_connection)
        self.consumer_content_schedules = consumer.ConsumerContentSchedulesAPI(pulp_connection)
        self.consumer_group = consumer_groups.ConsumerGroupAPI(pulp_connection)
        self.consumer_group_search = consumer_groups.ConsumerGroupSearchAPI(pulp_connection)
        self.consumer_group_actions = consumer_groups.ConsumerGroupActionAPI(pulp_connection)
        self.consumer_group_bind = consumer_groups.ConsumerGroupBindAPI(pulp_connection)
        self.consumer_group_content = consumer_groups.ConsumerGroupContentAPI(pulp_connection)
        self.consumer_history = consumer.ConsumerHistoryAPI(pulp_connection)
        self.consumer_search = consumer.ConsumerSearchAPI(pulp_connection)
        self.content_orphan = OrphanContentAPI(pulp_connection)
        self.content_source = ContentSourceAPI(pulp_connection)
        self.content_catalog = ContentCatalogAPI(pulp_connection)
        self.event_listener = EventListenerAPI(pulp_connection)
        self.permission = auth.PermissionAPI(pulp_connection)
        self.repo = repository.RepositoryAPI(pulp_connection)
        self.repo_actions = repository.RepositoryActionsAPI(pulp_connection)
        self.repo_distributor = repository.RepositoryDistributorAPI(pulp_connection)
        self.repo_group = repo_groups.RepoGroupAPI(pulp_connection)
        self.repo_group_actions = repo_groups.RepoGroupActionAPI(pulp_connection)
        self.repo_group_distributor = repo_groups.RepoGroupDistributorAPI(pulp_connection)
        self.repo_group_distributor_search = repo_groups.RepoGroupSearchAPI(pulp_connection)
        self.repo_group_search = repo_groups.RepoGroupSearchAPI(pulp_connection)
        self.repo_history = repository.RepositoryHistoryAPI(pulp_connection)
        self.repo_importer = repository.RepositoryImporterAPI(pulp_connection)
        self.repo_publish_schedules = repository.RepositoryPublishSchedulesAPI(pulp_connection)
        self.repo_search = repository.RepositorySearchAPI(pulp_connection)
        self.repo_sync_schedules = repository.RepositorySyncSchedulesAPI(pulp_connection)
        self.repo_unit = repository.RepositoryUnitAPI(pulp_connection)
        self.role = auth.RoleAPI(pulp_connection)
        self.server_info = ServerInfoAPI(pulp_connection)
        self.server_status = ServerStatusAPI(pulp_connection)
        self.tasks = TasksAPI(pulp_connection)
        self.tasks_search = TaskSearchAPI(pulp_connection)
        self.uploads = UploadAPI(pulp_connection)
        self.user = auth.UserAPI(pulp_connection)
        self.user_search = auth.UserSearchAPI(pulp_connection)
