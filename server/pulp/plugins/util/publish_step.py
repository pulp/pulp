import copy
from gettext import gettext as _
from itertools import chain, imap
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
from pulp.plugins.model import Unit
from pulp.plugins.util import misc
from pulp.plugins.util.nectar_config import importer_config_to_nectar_config
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.criteria import Criteria
import pulp.server.managers.factory as manager_factory
from pulp.server.exceptions import PulpCodedTaskFailedException
from nectar import listener
from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader



_LOG = logging.getLogger(__name__)


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
    """

    def __init__(self, step_type, status_conduit=None, non_halting_exceptions=None):
        """
        :param step_type: The id of the step this processes
        :type step_type: str
        :param status_conduit: The conduit used for reporting status as the step executes
        :type status_conduit: pulp.plugins.conduits.mixins.StatusMixin
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
        self.non_halting_exceptions = non_halting_exceptions
        self.exceptions = []

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
        Do any primary work required for this step
        """
        pass

    def process(self):
        """
        The process method is used to perform the work needed for this step.
        It will update the step progress and raise an exception on error.
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
                if self.get_iterator():
                    #We are using a generator and will call _process_block for each item
                    for item in self.get_iterator():
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
        This block is called for the main processing loop
        """
        failures = self.progress_failures
        #Need to keep backwards compatibility
        if item:
            self.process_main(item=item)
        else:
            self.process_main()
        if failures == self.progress_failures:
            self.progress_successes += 1
        self.report_progress()

    def _get_total(self):
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
                child_reports.append(step.get_progress_report())
            report[reporting_constants.PROGRESS_SUB_STEPS_KEY] = child_reports
            # Root object is just a list of reports, this should be the object at some point
            if self.parent is None:
                return child_reports

        return report

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
            error_details['error'] = str(e.message) or str(e)

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
                 plugin_type=None):
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
        super(PluginStep, self).__init__(step_type, conduit)
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
        if not self.working_dir:
            repo = self.get_repo()
            self.working_dir = repo.working_dir

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
        return self.parent.get_conduit()

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
        Perform the action for the step

        :return: report describing the step's run
        :rtype:  pulp.plugins.model.PublishReport
        """
        working_dir = self.get_working_dir()
        if not working_dir:
            raise RuntimeError("working_dir for step not found, unable to execute step")
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        try:
            super(PluginStep, self).process_lifecycle()
        finally:
            # Always cleanup the working directory
            shutil.rmtree(working_dir, ignore_errors=True)

        return self._build_final_report()


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
        Perform the publish action for the repo

        A compatability method. process_lifecycle() should be called directly instead.

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
    The UnitPublishStep has been deprecated in favor of the PluginStep with the
    PluginStepIterativeProcessingMixin

    All code that is currently using the UnitPublishStep should migrate to use the
    PluginStep with the PluginStepIterativeProcessingMixin
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
        This method returns a generator for the unit_type specified on the PublishStep.
        The units created by this generator will be iterated over by the process_unit method.

        :return: generator of units
        :rtype:  GeneratorTyp of Units
        """
        types_to_query = (set(self.unit_type)).difference(self.skip_list)
        criteria = UnitAssociationCriteria(type_ids=list(types_to_query),
                                           association_filters=self.association_filters,
                                           unit_fields=self.unit_fields)
        return self.get_conduit().get_units(criteria, as_generator=True)

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

    def process_unit(self, unit):
        """
        Do any work required for publishing a unit in this step

        :param unit: The unit to process
        :type unit: Unit
        """
        pass

    def _process_block(self):
        """
        This block is called for the main processing loop
        """
        package_unit_generator = self.get_unit_generator()
        for package_unit in package_unit_generator:
            if self.canceled:
                return
            self.process_unit(package_unit)
            self.progress_successes += 1
            self.progress_details = ""
            self.report_progress()

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


class AtomicDirectoryPublishStep(PublishStep):
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

    def process_main(self):
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

        _LOG.debug('Copying tree from %s to %s' % (self.source_dir, timestamp_master_dir))
        shutil.copytree(self.source_dir, timestamp_master_dir, symlinks=True)

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
        self._clear_directory(self.master_publish_dir, skip_list=[self.parent.timestamp])


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
        shutil.move(os.path.join(self.source_dir, tar_file_name), self.publish_file)


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
        shutil.copytree(self.source_dir, self.target_dir, symlinks=self.preserve_symlinks)


class PluginStepIterativeProcessingMixin(object):
    """
    A mixin for steps that iterate over a generator
    """


    def _process_block(self):
        """
        This block is called for the main processing loop and handles reporting.
        """
        generator = self.get_generator()
        for item in generator:
            if self.canceled:
                return
            # Clear the details text so that the details from a previous iteration won't
            # show up for the next iteration
            self.progress_details = ""
            self.process_item(item)
            self.progress_successes += 1
            self.report_progress()

    def get_generator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_item method.

        :return: generator of items
        :rtype: GeneratorType of items
        """
        raise NotImplementedError()


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

    def _get_total(self):
        """
        Get total number of items to download

        :returns: number of DownloadRequests
        :rtype: int
        """
        return len(self.downloads)

    def _process_block(self):
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
        :type  report: pulp.plugins.model.PublishReport
        """
        self.progress_successes += 1
        self.report_progress()

    # from listener.DownloadEventListener
    def download_failed(self, report):
        """
        This is the callback that we will get from the downloader library when any individual
        download fails. Bump the failure counter and report progress.

        :param report: report (passed in from nectar but currently not used)
        :type  report: pulp.plugins.model.PublishReport
        """
        self.progress_failures += 1
        self.report_progress()

    def cancel(self):
        """
        Cancel the current step
        """
        super(DownloadStep, self).cancel()
        self.downloader.cancel()


class GetLocalUnitsStep(PluginStep):
    """
    Given a list of unit keys, this will determine which ones are already in
    pulp, and it will use the conduit to save each. This depends on there being
    a parent step with attribute "available_units", which must be a list of
    unit keys (which themselves are dictionaries).
    """
    def __init__(self, importer_type, unit_type, unit_key_fields, working_dir):
        """
        :param importer_type:   unique identifier for the type of importer
        :type  importer_type:   basestring
        :param unit_type:       unique identifier for the unit type in use
        :type  unit_type:       basestring
        :param unit_key_fields: a list of field names in the unit type's unit key.
        :type  unit_key_fields: list
        :param working_dir:     full path to a working directory
        :type  working_dir:     basestring
        """
        super(GetLocalUnitsStep, self).__init__(step_type=reporting_constants.SYNC_STEP_GET_LOCAL,
                                                plugin_type=importer_type,
                                                working_dir=working_dir)
        self.description = _('Copying units already in pulp')

        self.unit_type = unit_type
        self.unit_key_fields = unit_key_fields
        self.content_query_manager = manager_factory.content_query_manager()
        # list of unit keys
        self.units_to_download = []

    def process_main(self):
        """
        given the passed-in unit keys, determine which of them already exist in
        pulp, and save those with the conduit found on the parent.
        """
        # any units that are already in pulp
        units_we_already_had = set()

        # for any unit that is already in pulp, save it into the repo
        for unit_dict in self.content_query_manager.get_multiple_units_by_keys_dicts(
                self.unit_type, self.parent.available_units, self.unit_key_fields):
            unit = self._dict_to_unit(unit_dict)
            self.get_conduit().save_unit(unit)
            units_we_already_had.add(unit)

        for unit_key in self.parent.available_units:
            # build a temp Unit instance just to use its comparison feature
            unit = Unit(self.unit_type, unit_key, {}, '')
            if unit not in units_we_already_had:
                self.units_to_download.append(unit_key)

    def _dict_to_unit(self, unit_dict):
        """
        convert a unit dictionary (a flat dict that has all unit key, metadata,
        etc. keys at the root level) into a Unit object. This requires knowing
        not just what fields are part of the unit key, but also how to derive
        the storage path.

        This should be overridden in a subclass.

        :param unit_dict:   a flat dictionary that has all unit key, metadata,
                            etc. keys at the root level, representing a unit
                            in pulp
        :type  unit_dict:   dict

        :return:    a unit instance
        :rtype:     pulp.plugins.model.Unit
        """
        raise NotImplementedError
