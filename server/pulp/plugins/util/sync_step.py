import logging

from pulp.plugins.util.publish_step import PublishStep, UnitPublishStep

_LOG = logging.getLogger(__name__)


class SyncStep(PublishStep):
    """
    This currently inherits from PublishStep because they share a lot of code.
    Ideally they would inherit from a SyncPublishStep but I'm trying to keep
    the changes small for now.
    """

    def __init__(self, step_type, repo=None, sync_conduit=None, config=None, importer_type=None):
        """
        Set the default parent, step_type and unit_type for the the sync step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :type step_type: str
        :param repo: The repo to be synced to
        :type repo: pulp.plugins.model.Repository
        :param sync_conduit: The sync conduit for the repo to be synced
        :type sync_conduit: tbd
        :param config: The sync configuration
        :type config: PluginCallConfiguration
        :param importer_type: The type of the importer that is being synced
        :type importer_type: str
        """
        super(SyncStep, self).__init__(step_type, repo, sync_conduit, config,
                                       None, importer_type)
        self.importer_type = importer_type
        self.repo = repo
        self.sync_conduit = sync_conduit
        self.config = config

    def sync(self):
        """
        Perform the sync action the repo & information specified in the constructor
        """
        self.process_lifecycle()
        return self._build_final_report()

    def get_conduit(self):
        """
        :returns: Return the conduit for this sync action
        :rtype: tbd
        """
        if self.sync_conduit:
            return self.sync_conduit
        return self.parent.get_conduit()


class UnitSyncStep(UnitPublishStep):

    def __init__(self, step_type, unit_type=None, association_filters=None,
                 unit_fields=None):
        """
        Set the default parent, step_type and unit_type for the sync step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :typstep_typeid: str
        :param unit_type: The type of unit this step processes
        :type unit_type: str or list of str
        """
        super(UnitSyncStep, self).__init__(step_type, unit_type, association_filters, unit_fields)
        if isinstance(unit_type, list):
            self.unit_type = unit_type
        else:
            self.unit_type = [unit_type]
        self.skip_list = set()
        self.unit_fields = unit_fields

    def get_unit_generator(self):
        """
        This method returns a generator for the unit_type specified on the SyncStep.
        The units created by this generator will be iterated over by the process_unit method.

        You'll want this to return a generator that is based on whatever metadata you downloaded.

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
