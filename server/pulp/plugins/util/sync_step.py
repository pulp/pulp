import logging

from pulp.plugins.util.publish_step import PluginStep, PluginStepIterativeProcessingMixin

_LOG = logging.getLogger(__name__)


class SyncStep(PluginStep):
    """
    A step to perform syncs
    """

    def __init__(self, step_type, repo=None, conduit=None, config=None, plugin_type=None):
        """
        Set up the sync step

        :param step_type: The id of the step this processes
        :type  step_type: str
        :param repo: The repo to be synced to
        :type  repo: pulp.plugins.model.Repository
        :param conduit: The sync conduit for the repo to be synced
        :type  conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config: The sync configuration
        :type  config: PluginCallConfiguration
        :param plugin_type: The type of the plugin that is being synced
        :type  plugin_type: str
        """
        super(SyncStep, self).__init__(step_type, repo=repo, conduit=conduit, config=config,
                                       plugin_type=plugin_type)
        self.plugin_type = plugin_type
        self.repo = repo
        self.conduit = conduit
        self.config = config

    def sync(self):
        """
        Perform the sync action
        """
        self.process_lifecycle()
        return self._build_final_report()


class UnitSyncStep(SyncStep, PluginStepIterativeProcessingMixin):

    def __init__(self, step_type, unit_type=None):
        """
        Set up unit sync step. This is the class to use when iterating over items to sync

        :param step_type: The id of the step this processes
        :typstep_typeid: str
        :param unit_type: The type of unit this step processes
        :type unit_type: str or list of str
        """
        super(UnitSyncStep, self).__init__(step_type, unit_type)
        if isinstance(unit_type, list):
            self.unit_type = unit_type
        else:
            self.unit_type = [unit_type]
        self.skip_list = set()

    def get_generator(self):
        """
        The items created by this generator will be iterated over by the process_item method.

        For sync, you'll want this to return a generator that is based on
        whatever metadata you downloaded.

        :return: generator of units
        :rtype:  GeneratorType of Units
        """
        raise NotImplementedError()

    def _get_total(self, id_list=None):
        """
        Return the total number of units that are processed by this step.
        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.

        You'll want this to be the number of items to work with from your metadata.

        :param id_list: List of type ids to get the total count of
        :type id_list: list of str
        """
        raise NotImplementedError()
