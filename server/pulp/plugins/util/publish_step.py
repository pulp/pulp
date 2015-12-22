from gettext import gettext as _
from itertools import chain, imap
import copy
import itertools
import logging
import os
import shutil
import sys
import tarfile
import time
import traceback
import uuid

from pulp.common import error_codes
from pulp.common.plugins import reporting_constants, importer_constants
from pulp.common.util import encode_unicode
from pulp.plugins.util import manifest_writer, misc
from pulp.plugins.util.nectar_config import importer_config_to_nectar_config
from pulp.server.controllers import repository as repo_controller
from pulp.server.db.model.criteria import Criteria, UnitAssociationCriteria
from pulp.server.exceptions import PulpCodedTaskFailedException
from pulp.server.controllers import units as units_controller
from nectar import listener
from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader
import pulp.server.managers.factory as manager_factory
from pulp.server.managers.repo import _common as common_utils
from pulp.server.util import copytree


_logger = logging.getLogger(__name__)


def _post_order(step):
    """
    Create a generator to perform a pre-order traversal of a step tree

    :param step: a Publish step step to traverse
    :type step: PublishStep
    :returns: generator
    """
    for v in chain(*imap(_post_order, step.children)):
        yield v
    yield step


class Step(object):
    """
    Base class for step processing. The only tie to the platform is an assumption of
    the use of a conduit that extends StatusMixin for reporting status along the way.

    GETTING STARTED:

    Override the process_main() method and do your work there.

    If you are iterating over items and doing the same work on each, also override the
    get_iterator() and get_total() methods.

    A partial map of the execution flow:

    process()
    |
    +-- initialize()
    |
    +-- _process_block()
    |   |
    |   +-- process_main()
    |   |
    |   +-- report_progress()
    |
    +-- finalize()
    |
    +-- post_process()

    """

    def __init__(self, step_type, status_conduit=None, non_halting_exceptions=None,
                 disable_reporting=False):
        """
        :param step_type: The id of the step this processes
        :type step_type: str
        :param status_conduit: The conduit used for reporting status as the step executes
        :type status_conduit: pulp.plugins.conduits.mixins.StatusMixin
        :param non_halting_exceptions: Disable progress reporting for this step or any child steps
        :type non_halting_exceptions: list of Exception
        :param disable_reporting: Disable progress reporting for this step or any child steps
        :type disable_reporting: bool
        """
        self.status_conduit = status_conduit
        self.uuid = str(uuid.uuid4())
        self.parent = None
        self.step_id = step_type
        self.canceled = False
        self.description = ""
        self.progress_details = ""
        self.state = reporting_constants.STATE_NOT_STARTED
        self.progress_successes = 0
        self.progress_failures = 0
        self.error_details = []
        self.total_units = 1
        self.children = []
        self.last_report_time = 0
        self.last_reported_state = self.state
        self.timestamp = str(time.time())
        self.non_halting_exceptions = non_halting_exceptions or []
        self.exceptions = []
        self.disable_reporting = disable_reporting

    def add_child(self, step):
        """
        Add a child step to the end of the child steps list

        :param step: The step to add
        :type step: Step
        """
        step.parent = self
        self.children.append(step)

    def insert_child(self, index, step):
        """
        Insert a child step at the beginning of the child steps list

        :param index: the location in the child step list where the child should be added
        :type index: int
        :param step: The step to insert
        :type step: Step
        """
        step.parent = self
        self.children.insert(index, step)

    def get_status_conduit(self):
        if self.status_conduit:
            return self.status_conduit
        return self.parent.get_status_conduit()

    def clear_children(self):
        """
        Remove any added children
        """
        self.children = []

    def process_lifecycle(self):
        """
        Process the lifecycle assuming this step is the root of the tree

        The tree will be processed using post-order (depth first) traversal

        For each step in the tree initialize will be called using pre-order traversal
        The overall Lifecycle ordering is as follows:
        * initialize
        * process_main
        * finalize - All finalize steps will be called even if one of them throws an exception.
                     This is so that open file handles can be closed.
        * post_process
        """
        try:
            # Process the steps in post order
            for step in _post_order(self):
                step.process()
        finally:
            self.report_progress(force=True)

    def is_skipped(self):
        """
        Test to find out if the step should be skipped.

        :return: whether or not the step should be skipped
        :rtype:  bool
        """
        return False

    def initialize(self):
        """
        Method called to initialize after all publish steps have been created
        """
        pass

    def finalize(self):
        """
        Method called to finalize after process_main has been called.  This will
        be called even if process_main or initialize raises an exceptions
        """
        pass

    def post_process(self):
        """
        Method called after finalize so that items can be moved into final locations on disk
        """
        pass

    def process_main(self, item=None):
        """
        START HERE: override this method to do whatever work your step needs to do.

        If your step performs the same work iteratively on numerous items, consider also
        overriding get_iterator() and get_total().

        Otherwise, ignore the "item" argument, and just do your work.

        :param item: The item to process or None if this get_iterator is not defined
        :param item: object or None
        """
        pass

    def process(self):
        """
        You probably do not want to override this method. It handles workflow for the rest of the
        methods on your step. It will update the step progress and raise an exception on error.
        """
        if self.canceled:
            return

        if self.is_skipped():
            self.state = reporting_constants.STATE_SKIPPED
            return

        self.state = reporting_constants.STATE_RUNNING

        try:
            try:
                self.total_units = self._get_total()
                self.report_progress()
                self.initialize()
                self.report_progress()
                item_iterator = self.get_iterator()
                if item_iterator is not None:
                    # We are using a generator and will call _process_block for each item
                    for item in item_iterator:
                        if self.canceled:
                            break
                        try:
                            self._process_block(item=item)
                        except Exception as e:
                            raise_exception = True
                            for exception in self.non_halting_exceptions:
                                if isinstance(e, exception):
                                    raise_exception = False
                                    self._record_failure(e=e)
                                    self.exceptions.append(e)
                                    break
                            if raise_exception:
                                raise
                        # Clean out the progress_details for the individual item
                        self.progress_details = ""
                    if self.exceptions:
                        raise PulpCodedTaskFailedException(error_code=error_codes.PLP0032,
                                                           task_id=self.status_conduit.task_id)
                else:
                    self._process_block()
                self.progress_details = ""
                # Double check & return if we have been canceled
                if self.canceled:
                    return
            finally:
                # Always call finalize to allow cleanup of file handles
                self.finalize()
            self.post_process()
        except Exception as e:
            tb = sys.exc_info()[2]
            if not isinstance(e, PulpCodedTaskFailedException):
                self._record_failure(e, tb)
            parent = self
            while parent:
                parent.state = reporting_constants.STATE_FAILED
                try:
                    parent.on_error()
                except Exception:
                    # Eat exceptions from the error handler since we
                    # still want to notify up the tree
                    pass
                parent = parent.parent
            raise

        self.state = reporting_constants.STATE_COMPLETE

    def on_error(self):
        """
        this block is called if a child step raised an exception
        """
        pass

    def _process_block(self, item=None):
        """
        This is part of the workflow internals that should not be overridden unless you are sure of
        what you are doing. If you want somewhere to generally perform work in your step, this is
        not the place. See the class doc block for more info on where to put your code.
        """
        failures = self.progress_failures
        # Need to keep backwards compatibility
        if item:
            self.process_main(item=item)
        else:
            self.process_main()
        if failures == self.progress_failures:
            self.progress_successes += 1
        self.report_progress()

    def _get_total(self):
        """
        DEPRECATED in favor of get_total()
        """
        return self.get_total()

    def get_total(self):
        """
        Process steps default to one action.

        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.
        """
        return 1

    def report_progress(self, force=False):
        """
        Bubble up that something has changed where progress should be reported.
        It is up to the parent to determine what actions should be taken.
        :param force: Whether or not a write to the database should be forced
        :type force: bool
        """
        if self.disable_reporting:
            return

        # Force an update if the step state has changed
        if self.state != self.last_reported_state:
            force = True
            self.last_reported_state = self.state
        if self.parent:
            self.parent.report_progress(force)
        else:
            if force:
                self.get_status_conduit().set_progress(self.get_progress_report())
            else:
                current_time = time.time()
                if current_time != self.last_report_time:
                    # Update at most once a second
                    self.get_status_conduit().set_progress(self.get_progress_report())
                    self.last_report_time = current_time

    def get_progress_report(self):
        """
        Return the machine readable progress report for this task

        :returns: The machine readable progress report for this task
        :rtype: dict
        """
        if self.progress_failures > 0:
            self.state = reporting_constants.STATE_FAILED

        total_processed = self.progress_successes + self.progress_failures
        report = {
            reporting_constants.PROGRESS_STEP_UUID: self.uuid,
            reporting_constants.PROGRESS_STEP_TYPE_KEY: self.step_id,
            reporting_constants.PROGRESS_NUM_SUCCESSES_KEY: self.progress_successes,
            reporting_constants.PROGRESS_STATE_KEY: self.state,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: self.error_details,
            reporting_constants.PROGRESS_NUM_PROCESSED_KEY: total_processed,
            reporting_constants.PROGRESS_NUM_FAILURES_KEY: self.progress_failures,
            reporting_constants.PROGRESS_ITEMS_TOTAL_KEY: self.total_units,
            reporting_constants.PROGRESS_DESCRIPTION_KEY: self.description,
            reporting_constants.PROGRESS_DETAILS_KEY: self.progress_details
        }
        if self.children:
            child_reports = []
            for step in self.children:
                child_reports.extend(step.get_progress_report())
            report[reporting_constants.PROGRESS_SUB_STEPS_KEY] = child_reports
            # Root object is just a list of reports, this should be the object at some point
            if self.parent is None:
                return child_reports

        return [report]

    def _record_failure(self, e=None, tb=None):
        """
        Record a failure in a step's progress sub-report.

        :param e: exception instance (if any)
        :type  e: Exception or None
        :param tb: traceback instance (if any)
        :type  tb: Traceback or None
        """
        self.progress_failures += 1

        error_details = {'error': None,
                         'traceback': None}

        if tb is not None:
            error_details['traceback'] = '\n'.join(traceback.format_tb(tb))

        if e is not None:
            error_details['error'] = str(e)

        if error_details.values() != (None, None):
            self.error_details.append(error_details)

        if self.parent:
            self.parent._record_failure()

    def cancel(self):
        """
        Cancel the current step
        """
        if self.state not in reporting_constants.FINAL_STATES:
            self.state = reporting_constants.STATE_CANCELLED
            self.canceled = True
            for step in self.children:
                step.cancel()

    def get_iterator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_main method.

        :return: a list or other iterable
        :rtype: iterator
        """
        return None


class PluginStep(Step):
    """
    Base plugin step. It's likely you want to inherit from this and not use it directly.
    """

    def __init__(self, step_type, repo=None, conduit=None, config=None, working_dir=None,
                 plugin_type=None, **kwargs):
        """
        Set the default parent and step_type or the the plugin step

        :param step_type: The id of the step this processes
        :type  step_type: str
        :param repo: The repo being worked on
        :type  repo: pulp.plugins.model.Repository
        :param conduit: The conduit for the repo
        :type  conduit: a conduit from pulp.plugins.conduits
        :param config: The configuration
        :type  config: PluginCallConfiguration
        :param working_dir: The temp directory this step should use for processing
        :type  working_dir: str
        :param plugin_type: The type of the plugin
        :type  plugin_type: str
        """
        super(PluginStep, self).__init__(step_type, conduit, **kwargs)
        self.plugin_type = plugin_type
        self.working_dir = working_dir
        self.repo = repo
        self.conduit = conduit
        self.config = config

    def get_working_dir(self):
        """
        Return the working directory. The working dir is checked first, then
        the step's repo, then the parent step's repo's working dir. Note that
        the parent's working dir is not directly checked as part of this process.

        :returns: the working directory
        :rtype: str
        """
        if self.working_dir:
            return self.working_dir
        elif self.parent:
            return self.parent.get_working_dir()
        else:
            self.working_dir = common_utils.get_working_directory()
            return self.working_dir

    def get_plugin_type(self):
        """
        Return the plugin type

        :returns: the type of plugin this action is for
        :rtype: str or None
        """
        if self.plugin_type:
            return self.plugin_type
        if self.parent:
            return self.parent.get_plugin_type()
        return None

    def get_repo(self):
        """
        Return the repo associated with the step

        :returns: the repository for this action
        :rtype: pulp.plugins.model.Repository
        """
        if self.repo:
            return self.repo
        return self.parent.get_repo()

    def get_conduit(self):
        """
        Return the conduit associated with the step

        :returns: Return the conduit for this action
        :rtype: a conduit from pulp.plugins.conduits
        """
        if self.conduit:
            return self.conduit
        if self.parent:
            return self.parent.get_conduit()
        else:
            return None

    def get_config(self):
        """
        Return the config associated with the step

        :returns: Return the config for this action
        :rtype: pulp.plugins.config.PluginCallConfiguration
        """
        if self.config:
            return self.config
        return self.parent.get_config()

    def get_progress_report_summary(self):
        """
        Get the simpler, more human legible progress report

        :return: report describing the run
        :rtype:  pulp.plugins.model.PublishReport
        """
        report = {}
        for step in self.children:
            report.update({step.step_id: step.state})
        return report

    def _build_final_report(self):
        """
        Build the PublishReport to be returned as the result after task completion

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """
        if self.disable_reporting:
            return None

        overall_success = True
        if self.state == reporting_constants.STATE_FAILED:
            overall_success = False

        progres_report = self.get_progress_report()
        summary_report = self.get_progress_report_summary()

        if overall_success:
            final_report = self.get_conduit().build_success_report(summary_report, progres_report)
        else:
            final_report = self.get_conduit().build_failure_report(summary_report, progres_report)

        final_report.canceled_flag = self.canceled

        return final_report

    def process_lifecycle(self):
        """
        Changes the parent class behavior by returning a report.

        :return: report describing the step's run
        :rtype:  pulp.plugins.model.PublishReport
        """
        super(PluginStep, self).process_lifecycle()

        return self._build_final_report()


class UnitModelPluginStep(PluginStep):
    """
    Useful for performing actions on units that are defined as mongoengine models.

    QuerySetNoCache objects returned by the unit_queryset property are cached, so multiple accesses
    to that property will return the same list containing the same objects.

    The QuerySetNoCache objects themselves do not cache results, as the name implies.
    """
    def __init__(self, step_type, model_classes, repo_content_unit_q=None, repo=None, conduit=None,
                 config=None, working_dir=None, plugin_type=None, **kwargs):
        """
        :param step_type: The id of the step this processes
        :type  step_type: str
        :param model_classes:   list of ContentUnit subclasses that should be queried
        :type  model_classes:   list
        :param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against each ContentUnit class that gets passed in
        :type  repo_content_unit_q: mongoengine.Q
        :param repo: The repo being worked on
        :type  repo: pulp.plugins.model.Repository
        :param conduit: The conduit for the repo
        :type  conduit: a conduit from pulp.plugins.conduits
        :param config: The configuration
        :type  config: PluginCallConfiguration
        :param working_dir: The temp directory this step should use for processing
        :type  working_dir: str
        :param plugin_type: The type of the plugin
        :type  plugin_type: str
        """
        super(UnitModelPluginStep, self).__init__(step_type, repo, conduit, config, working_dir,
                                                  plugin_type, **kwargs)

        self.model_classes = model_classes
        self._repo_content_unit_q = repo_content_unit_q

        # the corresponding publicly-accessible values get cached here
        self._unit_querysets = None
        self._total = None

    def get_iterator(self):
        """
        This method returns a generator to loop over ContentUnits. The items created by this
        generator will be iterated over by the process_main method.

        ContentUnit results are not cached, so calling this a second time will cause results to be
        retrieved from the database a second time.

        :return: a generator of ContentUnit objects
        :rtype:  generator
        """
        return itertools.chain(*self.unit_querysets)

    @property
    def unit_querysets(self):
        """
        :return: list of QuerySetNoCache objects that correspond to ContentUnit searches for the
                 classes passed in to this step. The return value is cached, so multiple accesses of
                 this property will return the same list containing the same objects.
        :rtype:  list
        """
        if self._unit_querysets is None:
            self._unit_querysets = []
            for model_class in self.model_classes:
                queries = repo_controller.get_unit_model_querysets(self.get_repo().id,
                                                                   model_class,
                                                                   self._repo_content_unit_q)
                self._unit_querysets.extend(queries)
        return self._unit_querysets

    def get_total(self):
        """
        :return: total number of ContentUnits this step will operate on. This value is cached, so
                 multiple accesses will only incur one database query.
        :rtype:  int
        """
        if self._total is None:
            self._total = sum(query.count() for query in self.unit_querysets)
        return self._total


class PublishStep(PluginStep):
    """
    The PublishStep has been deprecated in favor of the PluginStep
    All code that is currently using the PublishStep should migrate to use the PluginStep
    """

    def __init__(self, step_type, repo=None, publish_conduit=None, config=None, working_dir=None,
                 distributor_type=None):
        """
        Set the default parent, step_type and unit_type for the the publish step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :type step_type: str
        :param repo: The repo to be published
        :type repo: pulp.plugins.model.Repository
        :param publish_conduit: The publish conduit for the repo to be published
        :type publish_conduit: RepoPublishConduit
        :param config: The publish configuration
        :type config: PluginCallConfiguration
        :param working_dir: The temp directory this step should use for processing
        :type working_dir: str
        :param distributor_type: The type of the distributor that is being published
        :type distributor_type: str
        """
        super(PublishStep, self).__init__(step_type, repo=repo, conduit=publish_conduit,
                                          config=config, working_dir=working_dir,
                                          plugin_type=distributor_type)

    def get_distributor_type(self):
        """
        Compatability method for get_plugin_type()

        :returns: the type of distributor this action is for
        :rtype: str or None
        """
        return self.get_plugin_type()

    def publish(self):
        """
        DEPRECATED

        Perform the publish action for the repo

        A compatibility method. process_lifecycle() should be called directly instead.

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """
        return self.process_lifecycle()

    @staticmethod
    def _create_symlink(source_path, link_path):
        """
        Create a symlink from the link path to the source path.

        If the link_path points to a directory that does not exist the directory
        will be created first.

        If we are overriding a current symlink with a new target - a debug message will be logged

        If a file already exists at the location specified by link_path an exception will be raised

        :param source_path: path of the source to link to
        :type  source_path: str
        :param link_path: path of the link
        :type  link_path: str
        """
        misc.create_symlink(source_path, link_path)

    @staticmethod
    def _clear_directory(path, skip_list=()):
        """
        Clear out the contents of the given directory.

        :param path: path of the directory to clear out
        :type  path: str
        :param skip_list: list of files or directories to not remove
        :type  skip_list: list or tuple
        """
        misc.clear_directory(path, skip_list)


class UnitPublishStep(PublishStep):
    """
    Contains logic specific to publishing units, such as determining the total number
    of units.
    """

    def __init__(self, step_type, unit_type=None, association_filters=None,
                 unit_fields=None):
        """
        Set the default parent, step_type and unit_type for the the publish step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :type step_type: str
        :param unit_type: The type of unit this step processes
        :type unit_type: str or list of str
        """
        super(UnitPublishStep, self).__init__(step_type)
        if isinstance(unit_type, list):
            self.unit_type = unit_type
        else:
            self.unit_type = [unit_type]
        self.skip_list = set()
        self.association_filters = association_filters
        self.unit_fields = unit_fields

    def get_unit_generator(self):
        """
        DEPRECATED function name. Please override get_iterator instead of this method. Do not call
        this function directly.

        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_main method.

        :return: a list or other iterable
        :rtype: iterator
        """
        types_to_query = (set(self.unit_type)).difference(self.skip_list)
        criteria = UnitAssociationCriteria(type_ids=list(types_to_query),
                                           association_filters=self.association_filters,
                                           unit_fields=self.unit_fields)
        return self.get_conduit().get_units(criteria, as_generator=True)

    def get_iterator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_main method.

        :return: a list or other iterable
        :rtype: iterator
        """
        return self.get_unit_generator()

    def is_skipped(self):
        """
        Test to find out if the step should be skipped.

        :return: whether or not the step should be skipped
        :rtype:  bool
        """
        if not self.skip_list:
            config = self.get_config()
            skip = config.get('skip', [])
            # there is a chance that the skip list is actually a dictionary with a
            # boolean to indicate whether or not each item should be skipped
            # if that is the case iterate over it to build a list of the items
            # that should be skipped instead
            if type(skip) is dict:
                return [k for k, v in skip.items() if v]
            self.skip_list = set(skip)

        return set(self.unit_type).issubset(self.skip_list)

    def process_main(self, item=None):
        """
        Alias to provide compatibility. Can be removed when process_unit gets removed.
        """
        return self.process_unit(item)

    def process_unit(self, unit):
        """
        DEPRECATED: override process_main instead.
        """
        pass

    def _get_total(self, id_list=None, ignore_filter=False):
        """
        Return the total number of units that are processed by this step.
        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.

        :param id_list: List of type ids to get the total count of
        :type id_list: list of str
        :param ignore_filter: Ignore the association filter and get all units of the given types
        :type ignore_filter: bool
        """
        if id_list is None:
            id_list = self.unit_type
        total = 0
        types_to_query = set(id_list).difference(self.skip_list)
        if not ignore_filter and self.association_filters:
            # We are copying using a filter so we have to get everything
            new_filter = copy.deepcopy(self.association_filters)
            new_filter['unit_type_id'] = {'$in': list(types_to_query)}
            criteria = Criteria(filters=new_filter)
            association_query_manager = manager_factory.repo_unit_association_query_manager()
            units_cursor = association_query_manager.find_by_criteria(criteria)
            total = units_cursor.count()
        else:
            for type_id in types_to_query:
                total += self.parent.repo.content_unit_counts.get(type_id, 0)
        return total


class AtomicDirectoryPublishStep(PluginStep):
    """
    Perform a publish of a working directory to a published directory with an atomic action.
    This works by first copying the files to a master directory and creating or updating a symbolic
    links in the publish locations

    :param source_dir: The source directory to be copied
    :type source_dir: str
    :param publish_locations: The target locations that are being updated
    :type publish_locations: list of tuples (relative_directory_in_source_dir, absolute publish
            location)
    :param master_publish_dir: The directory that will contain the master_publish_directories
    :type master_publish_dir: str
    :param step_type: The id of the step, so that this step can be used with custom names.
    :type step_type: str
    :param only_publish_directory_contents: If true, do not create the target directory,
            link each file in the source directory to a file with the same name in the target
            directory
    :type only_publish_directory_contents: bool
    """
    def __init__(self, source_dir, publish_locations, master_publish_dir, step_type=None,
                 only_publish_directory_contents=False):
        step_type = step_type if step_type else reporting_constants.PUBLISH_STEP_DIRECTORY
        super(AtomicDirectoryPublishStep, self).__init__(step_type)
        self.context = None
        self.source_dir = source_dir
        self.publish_locations = publish_locations
        self.master_publish_dir = master_publish_dir
        self.only_publish_directory_contents = only_publish_directory_contents

    def process_main(self, item=None):
        """
        Publish a directory from the repo to a target directory.
        """

        # Use the timestamp as the name of the current master repository
        # directory. This allows us to identify when these were created as well
        # as having more than one side-by-side during the publishing process.
        timestamp_master_dir = os.path.join(self.master_publish_dir,
                                            self.parent.timestamp)

        # Given that it is timestamped for this publish/repo we could skip the copytree
        # for items where http & https are published to a separate directory

        _logger.debug('Copying tree from %s to %s' % (self.source_dir, timestamp_master_dir))
        copytree(self.source_dir, timestamp_master_dir, symlinks=True)

        for source_relative_location, publish_location in self.publish_locations:
            if source_relative_location.startswith('/'):
                source_relative_location = source_relative_location[1::]

            timestamp_master_location = os.path.join(timestamp_master_dir, source_relative_location)
            timestamp_master_location = timestamp_master_location.rstrip('/')

            # Without the trailing '/'
            publish_location = publish_location.rstrip('/')

            # Create the parent directory of the published repository tree, if needed
            publish_dir_parent = os.path.dirname(publish_location)
            if not os.path.exists(publish_dir_parent):
                os.makedirs(publish_dir_parent, 0750)

            if not self.only_publish_directory_contents:
                # Create a temporary symlink in the parent of the published directory tree
                tmp_link_name = os.path.join(publish_dir_parent, self.parent.timestamp)
                os.symlink(timestamp_master_location, tmp_link_name)

                # Rename the symlink to the official published location name.
                # This has two desirable effects:
                # 1. it will overwrite an existing link, if it's there
                # 2. the operation is atomic, instantly changing the published directory
                # NOTE: it's not easy (possible?) to directly edit the target of a symlink
                os.rename(tmp_link_name, publish_location)
            else:
                if not os.path.exists(publish_location):
                    os.makedirs(publish_location, 0750)
                for file_name in os.listdir(timestamp_master_location):
                    tmp_link_name = os.path.join(publish_location, self.parent.timestamp)
                    master_source_file = os.path.join(timestamp_master_location, file_name)
                    os.symlink(master_source_file, tmp_link_name)
                    final_name = os.path.join(publish_location, file_name)
                    os.rename(tmp_link_name, final_name)

        # Clear out any previously published masters
        misc.clear_directory(self.master_publish_dir, skip_list=[self.parent.timestamp])


class SaveTarFilePublishStep(PublishStep):
    """
    Save a directory as a tar file
    :param source_dir: The directory to turn into a tar file
    :type source_dir: str
    :param publish_file: Fully qualified name of the final location for the generated tar file
    :type publish_file: str
    :param step_id: The id of the step, so that this step can be used with custom names.
    :type step_id: str
    """
    def __init__(self, source_dir, publish_file, step_type=None):
        step_type = step_type if step_type else reporting_constants.PUBLISH_STEP_TAR
        super(SaveTarFilePublishStep, self).__init__(step_type)
        self.source_dir = source_dir
        self.publish_file = publish_file
        self.description = _('Saving tar file.')

    def process_main(self):
        """
        Publish a directory from to a tar file
        """
        # Generate the tar file in the working directory
        tar_file_name = os.path.join(self.source_dir, os.path.basename(self.publish_file))
        tar_file = tarfile.TarFile(name=tar_file_name, mode='w', dereference=True)
        try:
            tar_file.add(name=self.source_dir, arcname='')
        finally:
            tar_file.close()

        # Move the tar file to the final location
        publish_dir_parent = os.path.dirname(self.publish_file)
        if not os.path.exists(publish_dir_parent):
            os.makedirs(publish_dir_parent, 0750)
        shutil.copy(os.path.join(self.source_dir, tar_file_name), self.publish_file)


class CreatePulpManifestStep(Step):
    """
    This will create a PULP_MANIFEST file in the specified directory. This step should be used when
    the checksums of the files are not already known, because it will read and calculate new
    checksums for each one.

    If you already know the SHA256 checksums of the files going in the manifest, see an example
    in the FileDistributor that creates this file in a different way.
    """
    def __init__(self, target_dir):
        """
        :param target_dir:  full path to the directory where the PULP_MANIFEST file should
                            be created
        :type  target_dir:  basestring
        """
        super(CreatePulpManifestStep, self).__init__(reporting_constants.STEP_CREATE_PULP_MANIFEST)
        self.target_dir = target_dir
        self.description = _('Creating PULP_MANIFEST')

    def process_main(self, item=None):
        """
        creates the manifest file

        :param item:    not used
        """
        manifest_writer.make_manifest_for_dir(self.target_dir)


class CopyDirectoryStep(PublishStep):
    """
    Copy a directory from another directory

    :param source_dir: The directory to copy
    :type source_dir: str
    :param target_dir: Fully qualified name of the final location to copy to
    :type target_dir: str
    :param step_type: The id of the step, so that this step can be used with custom names.
    :type step_type: str
    :param delete_before_copy: Whether or not the contents of the target_dir should be cleared
                              before copying from source_dir
    :type delete_before_copy: bool
    :param preserve_symlinks: Whether or not the symlinks in the original source directory should
                              be copied as symlinks or as the content of the linked files.
                              Defaults to False.
    :type preserve_symlinks: bool
    """
    def __init__(self, source_dir, target_dir, step_type=None, delete_before_copy=True,
                 preserve_symlinks=False):
        step_type = step_type if step_type else reporting_constants.PUBLISH_STEP_TAR
        super(CopyDirectoryStep, self).__init__(step_type)
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.delete_before_copy = delete_before_copy
        self.description = _('Copying files')
        self.preserve_symlinks = preserve_symlinks

    def process_main(self):
        """
        Copy one directory to another.
        """
        if self.delete_before_copy:
            shutil.rmtree(self.target_dir, ignore_errors=True)
        copytree(self.source_dir, self.target_dir, symlinks=self.preserve_symlinks)


class DownloadStep(PluginStep, listener.DownloadEventListener):

    def __init__(self, step_type, downloads=None, repo=None, conduit=None, config=None,
                 working_dir=None, plugin_type=None, description=''):
        """
        Set the default parent and step_type for the Download step

        :param step_type: The id of the step this processes
        :type  step_type: str
        :param downloads: A list of DownloadRequests
        :type  downloads: list of nectar.request.DownloadRequest
        :param repo: The repo to be published
        :type  repo: pulp.plugins.model.Repository
        :param conduit: The conduit for the repo
        :type  conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config: The publish configuration
        :type  config: PluginCallConfiguration
        :param working_dir: The temp directory this step should use for processing
        :type  working_dir: str
        :param plugin_type: The type of the plugin
        :type  plugin_type: str
        :param description: The text description that will be displayed to users
        :type  description: basestring
        """

        super(DownloadStep, self).__init__(step_type, repo=repo, conduit=conduit,
                                           config=config, working_dir=working_dir,
                                           plugin_type=plugin_type)
        if downloads is not None:
            self._downloads = downloads
        else:
            self._downloads = []
        self.step_type = step_type
        self.repo = repo
        self.conduit = conduit
        self.config = config
        self.working_dir = working_dir
        self.plugin_type = plugin_type
        self.description = description

    def initialize(self):
        """
        Set up the nectar downloader

        Originally based on the ISO sync setup
        """
        config = self.get_config()
        self._validate_downloads = config.get(importer_constants.KEY_VALIDATE, default=True)
        self._repo_url = encode_unicode(config.get(importer_constants.KEY_FEED))
        # The _repo_url must end in a trailing slash, because we will use
        # urljoin to determine the path later
        if self._repo_url[-1] != '/':
            self._repo_url = self._repo_url + '/'

        downloader_config = importer_config_to_nectar_config(config.flatten())

        # We will pass self as the event_listener, so that we can receive the
        # callbacks in this class
        if self._repo_url.lower().startswith('file'):
            self.downloader = LocalFileDownloader(downloader_config, self)
        else:
            self.downloader = HTTPThreadedDownloader(downloader_config, self)

    @property
    def downloads(self):
        """
        This lets the class be instantiated with "downloads" as a generator that
        gets lazily evaluated. This is helpful, because at the time of
        instantiation, it is probably not known what downloads will be
        required.

        :return:    list of download requests (nectar.request.DownloadRequest)
        :rtype:     list
        """
        if not isinstance(self._downloads, list):
            self._downloads = list(self._downloads)
        return self._downloads

    def get_total(self):
        """
        Get total number of items to download

        :returns: number of DownloadRequests
        :rtype: int
        """
        return len(self.downloads)

    def process_main(self, item=None):
        """
        the main "do stuff" method. In this case, just kick off all the
        downloads.
        """
        self.downloader.download(self.downloads)

    # from listener.DownloadEventListener
    def download_succeeded(self, report):
        """
        This is the callback that we will get from the downloader library when any individual
        download succeeds. Bump the successes counter and report progress.

        :param report: report (passed in from nectar but currently not used)
        :type  report: nectar.report.DownloadReport
        """
        self.progress_successes += 1
        self.report_progress()

    # from listener.DownloadEventListener
    def download_failed(self, report):
        """
        This is the callback that we will get from the downloader library when any individual
        download fails. Bump the failure counter and report progress.

        :param report: report (passed in from nectar but currently not used)
        :type  report: nectar.report.DownloadReport
        """
        self.progress_failures += 1
        self.report_progress()

    def cancel(self):
        """
        Cancel the current step
        """
        super(DownloadStep, self).cancel()
        self.downloader.cancel()


class SaveUnitsStep(PluginStep):
    """
    Base class for steps that save/associate units with a repository

    Any step that saves units to the database should use this step in order to ensure that
    the repo unit counts are udpated properly.
    """

    def finalize(self):
        repo_controller.rebuild_content_unit_counts(self.get_repo().repo_obj)


class GetLocalUnitsStep(SaveUnitsStep):
    """
    Associate existing units & produce a list of unknown units.

    Given an iterator of units, associate the ones that are already in Pulp with the
    repository and create a list of all the units that do not yet exist in Pulp.
    This requires an iterable of "available_units", which must be an iterable of unit model
    instances with the unit keys populated. By default it will use it's parent step's
    available_units attribute, but can be overridden in the constructor.
    """

    def __init__(self, importer_type, unit_pagination_size=50, available_units=None, **kwargs):
        """
        :param importer_type:        unique identifier for the type of importer
        :type  importer_type:        basestring
        :param unit_pagination_size: How many units should be queried at one time (default 50)
        :type  importer_type:        int
        :param available_units:      An iterable of Units available for retrieval. This defaults to
                                     this step's parent's available_units attribute if not provided.
        :type  available_units:      iterable
        """
        super(GetLocalUnitsStep, self).__init__(step_type=reporting_constants.SYNC_STEP_GET_LOCAL,
                                                plugin_type=importer_type,
                                                **kwargs)
        self.description = _('Copying units already in pulp')

        # list of unit model instances
        self.units_to_download = []
        self.unit_pagination_size = unit_pagination_size
        self.available_units = available_units

    def process_main(self, item=None):
        """
        given the passed-in unit keys, determine which of them already exist in
        pulp, and save those with the conduit found on the parent.

        :param item: The item to process or none if get_iterator is not defined
        :param item: object or None
        """
        # any units that are already in pulp
        units_we_already_had = set()

        # If available_units was defined in the constructor, let's use it. Otherwise let's use the
        # default of self.parent.available_units
        available_units = self.available_units or self.parent.available_units

        for units_group in misc.paginate(available_units, self.unit_pagination_size):
            # Get this group of units
            query = units_controller.find_units(units_group)

            for found_unit in query:
                units_we_already_had.add(hash(found_unit))
                repo_controller.associate_single_unit(self.get_repo().repo_obj, found_unit)

            for unit in units_group:
                if hash(unit) not in units_we_already_had:
                    self.units_to_download.append(unit)
