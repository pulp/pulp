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

from pulp.common.plugins import reporting_constants
from pulp.server.db.model.criteria import UnitAssociationCriteria

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
    Base class for step processing. The only tie to the platofrm is an assumption of
    the use of a conduit that extends StatusMixin for reporting status along the way.
    """

    def __init__(self, step_type, status_conduit=None):
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
        self.state = reporting_constants.STATE_NOT_STARTED
        self.progress_successes = 0
        self.progress_failures = 0
        self.error_details = []
        self.total_units = 1
        self.children = []
        self.last_report_time = 0
        self.last_reported_state = self.state
        self.timestamp = str(time.time())

    def add_child(self, step):
        step.parent = self
        self.children.append(step)

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

    def process_main(self):
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
                self._process_block()
                # Double check & return if we have been canceled
                if self.canceled:
                    return
            finally:
                # Always call finalize to allow cleanup of file handles
                self.finalize()
            self.post_process()
        except Exception:
            e_type, e_value, tb = sys.exc_info()
            self._record_failure(e_value, tb)
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

    def _process_block(self):
        """
        This block is called for the main processing loop
        """
        self.process_main()
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
            reporting_constants.PROGRESS_DESCRIPTION_KEY: self.description
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


class PluginStep(Step):
    """
    Common functionality plugin-based steps. You probably want to inherit this in your own Step.
    """

    def __init__(self, step_type, repo=None, conduit=None, config=None, plugin_type=None,
                 working_dir=None):
        """
        Set the default parent, step_type and unit_type for the the plugin step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :type  step_type: str
        :param repo: The repo to be published
        :type  repo: pulp.plugins.model.Repository
        :param conduit: The conduit for the repo
        :type  conduit: conduit
        :param config: The configuration
        :type  config: PluginCallConfiguration
        :param plugin_type: the plugin type
        :type  plugin_type: str
        :param working_dir: working directory path
        :type  working_dir: str
        """
        super(PluginStep, self).__init__(step_type, conduit)
        self.repo = repo
        self.conduit = conduit
        self.config = config
        self.plugin_type = plugin_type
        self.working_dir = working_dir

    def get_working_dir(self):
        """
        Return the working directory

        :returns: directory path
        :rtype: str
        """
        if not self.working_dir:
            repo = self.get_repo()
            self.working_dir = repo.working_dir

        return self.working_dir


    def get_repo(self):
        """
        :returns: the repository for this step
        :rtype: pulp.plugins.model.Repository
        """
        if self.repo:
            return self.repo
        return self.parent.get_repo()

    def get_conduit(self):
        """
        :returns: Return the conduit for this step
        :rtype: conduit
        """
        if self.conduit:
            return self.conduit
        return self.parent.get_conduit()

    def get_config(self):
        """
        :returns: Return the config for this step
        :rtype: pulp.plugins.config.PluginCallConfiguration
        """
        if self.config:
            return self.config
        return self.parent.get_config()

    def get_plugin_type(self):
        """
        :returns: the type of distributor this action is for
        :rtype: str or None
        """
        if self.plugin_type:
            return self.plugin_type
        if self.parent:
            return self.parent.get_plugin_type()
        return None

    def get_progress_report_summary(self):
        """
        Get the simpler, more human legible progress report
        """
        report = {}
        for step in self.children:
            report.update({step.step_id: step.state})
        return report

    def _build_final_report(self):
        """
        Build the PublishReport to be returned as the result after task completion.

        Note that PublishReport is also used for other types of reporting, like sync.

        :return: report describing the step run
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


class PublishStep(PluginStep):

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
                                          config=config, plugin_type=distributor_type)
        self.working_dir = working_dir

    def publish(self):
        """
        Perform the publish action the repo & information specified in the constructor
        """
        working_dir = self.get_working_dir()
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        try:
            self.process_lifecycle()
        finally:
            # Always cleanup the working directory
            shutil.rmtree(working_dir, ignore_errors=True)

        return self._build_final_report()

    def get_distributor_type(self):
        """
        :returns: the type of distributor this action is for
        :rtype: str or None
        """
        return self.get_plugin_type()

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

        if not os.path.exists(source_path):
            msg = _('Will not create a symlink to a non-existent source [%(s)s]')
            raise RuntimeError(msg % {'s': source_path})

        if link_path.endswith('/'):
            link_path = link_path[:-1]

        link_parent_dir = os.path.dirname(link_path)

        if not os.path.exists(link_parent_dir):
            os.makedirs(link_parent_dir, mode=0770)
        elif os.path.lexists(link_path):
            if os.path.islink(link_path):
                link_target = os.readlink(link_path)
                if link_target == source_path:
                    # a pre existing link already points to the correct location
                    return
                msg = _('Removing old link [%(l)s] that was pointing to [%(t)s]')
                _LOG.debug(msg % {'l': link_path, 't': link_target})
                os.unlink(link_path)
            else:
                msg = _('Link path [%(l)s] exists, but is not a symbolic link')
                raise RuntimeError(msg % {'l': link_path})

        msg = _('Creating symbolic link [%(l)s] pointing to [%(s)s]')
        _LOG.debug(msg % {'l': link_path, 's': source_path})
        os.symlink(source_path, link_path)

    @staticmethod
    def _clear_directory(path, skip_list=()):
        """
        Clear out the contents of the given directory.

        :param path: path of the directory to clear out
        :type  path: str
        :param skip_list: list of files or directories to not remove
        :type  skip_list: list or tuple
        """
        _LOG.debug('Clearing out directory: %s' % path)

        if not os.path.exists(path):
            return

        for entry in os.listdir(path):

            if entry in skip_list:
                continue

            entry_path = os.path.join(path, entry)

            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)

            elif os.path.isfile(entry_path):
                os.unlink(entry_path)


class PluginStepIterativeProcessingMixin():

    def _process_block(self):
        """
        This block is called for the main processing loop and handles reporting.
        """
        generator = self.get_generator()
        for item in generator:
            if self.canceled:
                return
            self.process_item(item)
            self.progress_successes += 1
            self.report_progress()

    def get_generator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_item method.

        :return: generator of items
        :rtype:  GeneratorType of items
        """
        raise NotImplementedError()


class UnitPublishStep(PluginStepIterativeProcessingMixin, PluginStep):

    def __init__(self, step_type, unit_type=None, association_filters=None,
                 unit_fields=None):
        """
        Set up the unit publish step.

        the unit_type defaults to none since some steps are not used for processing units.

        :param step_type: The id of the step this processes
        :typstep_typeid: str
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

    def get_generator(self):
        """
        This method returns a generator for the unit_type specified on the PublishStep.
        The units created by this generator will be iterated over by the process_item method.

        :return: generator of units
        :rtype:  GeneratorType of Units
        """
        types_to_query = (set(self.unit_type)).difference(self.skip_list)
        criteria = UnitAssociationCriteria(type_ids=list(types_to_query),
                                           association_filters=self.association_filters,
                                           unit_fields=self.unit_fields)
        return self.get_conduit().get_units(criteria, as_generator=True)

    def process_item(self, unit):
        """
        Do any work required for publishing a unit in this step

        :param unit: The unit to process
        :type unit: Unit
        """
        pass

    def _get_total(self, id_list=None):
        """
        Return the total number of units that are processed by this step.
        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.

        :param id_list: List of type ids to get the total count of
        :type id_list: list of str
        """
        if id_list is None:
            id_list = self.unit_type
        total = 0
        if self.association_filters:
            # We have no good way to get this count without iterating over all units so punt
            total = 1
        else:
            types_to_query = (set(id_list)).difference(self.skip_list)
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
    """
    def __init__(self, source_dir, target_dir, step_type=None, delete_before_copy=True):
        step_type = step_type if step_type else reporting_constants.PUBLISH_STEP_TAR
        super(CopyDirectoryStep, self).__init__(step_type)
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.delete_before_copy = delete_before_copy
        self.description = _('Copying files')

    def process_main(self):
        """
        Copy one directory to another.
        """
        if self.delete_before_copy:
            shutil.rmtree(self.target_dir, ignore_errors=True)
        shutil.copytree(self.source_dir, self.target_dir)
