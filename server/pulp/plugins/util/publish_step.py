from gettext import gettext as _
import os
from pprint import pformat
import shutil
import sys
import time
import traceback
import logging

from pulp.common.plugins import reporting_constants
from pulp.server.db.model.criteria import UnitAssociationCriteria


_LOG = logging.getLogger(__name__)


class BasePublisher(object):
    """
    The BasePublisher can be used as the foundation for any step based processor

    Publishers follow the following phases
    1) Initialize metadata - Perform any global metadata initialization
    2) Process Steps - Process units that are part of the repository
    3) Finalize Metadata - Perform any metadata processing needed before final publish
    4) Post Metadata processing - Perform any final actions needed for the publish.  Usually
       this will include moving the data from the working directory to it's final location
       on the filesystem and making it available publicly
    """

    def __init__(self,
                 repo, publish_conduit, config,
                 initialize_metadata_steps=None,
                 process_steps=None,
                 finalize_metadata_steps=None,
                 post_metadata_process_steps=None):
        """
        :param repo: The repo to be published
        :type repo: pulp.plugins.model.Repository
        :param publish_conduit: The publish conduit for the repo to be published
        :type publish_conduit: RepoPublishConduit
        :param config: The publish configuration
        :type config: PluginCallConfiguration
        :param initialize_metadata_steps: A list of steps that will have metadata initialized
        :type initialize_metadata_steps: list of UnitPublishStep
        :param process_steps: A list of steps that are part of the primary publish action
        :type process_steps: list of UnitPublishStep
        :param finalize_metadata_steps: A list of steps that are run as part of the metadata
                                        finalization phase
        :type finalize_metadata_steps: list of UnitPublishStep
        :param post_metadata_process_steps: A list of steps that are run after metadata has
                                            been processed
        :type post_metadata_process_steps: list of UnitPublishStep

        """

        self.timestamp = str(time.time())

        self.repo = repo
        self.conduit = publish_conduit
        self.config = config
        self.canceled = False
        self.working_dir = repo.working_dir

        self.all_steps = {}
        self.initialize_metadata_steps = []
        self.process_steps = []
        self.finalize_metadata_steps = []
        self.post_metadata_process_steps = []

        self._add_steps(initialize_metadata_steps, self.initialize_metadata_steps)
        self._add_steps(process_steps, self.process_steps)
        self._add_steps(finalize_metadata_steps, self.finalize_metadata_steps)
        self._add_steps(post_metadata_process_steps, self.post_metadata_process_steps)

    def _add_steps(self, step_list, target_list):
        """
        Add a step to step specified list and to the map of all known steps

        :param step_list: The list of steps to be added to the publisher
        :type step_list: list of PublishStep
        :param target_list: the list that the steps should be added to
        :type step_list: list of PublishStep
        """
        if step_list:
            for step in step_list:
                if step.step_id in self.all_steps:
                    if step != self.all_steps[step.step_id]:
                        raise ValueError(_('An attempt has been made to register two different '
                                           'steps with the same id: %s' % step.step_id))

                self.all_steps[step.step_id] = step
                step.parent = self
            target_list.extend(step_list)

    def add_initialize_metadata_steps(self, steps):
        """
        Add additional metadata initialization steps
        :param steps: The list of step objects to process
        :type steps: list of PublishStep
        """
        self._add_steps(steps, self.initialize_metadata_steps)

    def add_process_steps(self, steps):
        """
        Add additional processing steps
        :param steps: The list of step objects to process
        :type steps: list of PublishStep
        """
        self._add_steps(steps, self.process_steps)

    def add_finalize_metadata_steps(self, steps):
        """
        Add additional metadata finalization steps
        :param steps: The list of step objects to process
        :type steps: list of PublishStep
        """
        self._add_steps(steps, self.finalize_metadata_steps)

    def add_post_process_steps(self, steps):
        """
        Add additional post processing steps
        :param steps: The list of step objects to process
        :type steps: list of PublishStep
        """
        self._add_steps(steps, self.post_metadata_process_steps)

    def get_step(self, step_id):
        """
        Get a step using the unique ID

        :param step_id: a unique identifier for the step to be returned
        :type step_id: str
        :returns: The step matching the step_id
        :rtype: UnitPublishStep
        """
        return self.all_steps[step_id]

    def publish(self):
        """
        Perform the publish action the repo & information specified in the constructor
        """
        _LOG.debug('Starting publish for repository: %s' % self.repo.id)

        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        try:
            # attempt processing of all the steps
            try:
                for step in self.initialize_metadata_steps:
                    step.initialize_metadata()
                for step in self.process_steps:
                    step.process()
            finally:
                # metadata steps may have open file handles so attempt finalization
                for step in self.finalize_metadata_steps:
                    step.finalize_metadata()
                    # Since this step doesn't go through the normal processing we must update it
                    step.state = reporting_constants.STATE_COMPLETE
            for step in self.post_metadata_process_steps:
                step.process()
        finally:
            # Always cleanup the working directory
            shutil.rmtree(self.working_dir, ignore_errors=True)

        _LOG.debug('Publish completed with progress:\n%s' % pformat(self.get_progress_report()))

        return self._build_final_report()

    @property
    def skip_list(self):
        """
        Calculate the list of resource types that should be skipped during processing
        """
        skip = self.config.get('skip', [])
        # there is a chance that the skip list is actually a dictionary with a
        # boolean to indicate whether or not each item should be skipped
        # if that is the case iterate over it to build a list of the items
        # that should be skipped instead
        if type(skip) is dict:
            return [k for k, v in skip.items() if v]
        return skip

    def cancel(self):
        """
        Cancel an in-progress publication.
        """
        _LOG.debug('Canceling publish for repository: %s' % self.repo.id)

        if self.canceled:
            return

        self.canceled = True

        # put the reporting logic here so I don't have to put it everywhere
        for step in self.all_steps.itervalues():
            step.cancel()

    def _build_final_report(self):
        """
        Build the PublishReport to be returned as the result task completion

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """

        overall_success = True
        for step in self.all_steps.itervalues():
            if step.state is reporting_constants.STATE_FAILED:
                overall_success = False

        progres_report = self.get_progress_report()
        summary_report = self.get_progress_report_summary()

        if overall_success:
            final_report = self.conduit.build_success_report(summary_report, progres_report)
        else:
            final_report = self.conduit.build_failure_report(summary_report, progres_report)

        final_report.canceled_flag = self.canceled

        return final_report

    def get_progress_report(self):
        """
        Get the machine readable progress report for the entire step processor
        """
        report = {}
        for step in self.all_steps.itervalues():
            report[step.step_id] = step.get_progress_report()
        return report

    def get_progress_report_summary(self):
        """
        Get the simpler, more human legible progress report
        """
        report = {}
        for step in self.all_steps.itervalues():
            report.update(step.get_progress_report_summary())
        return report

    def report_progress(self):
        """
        Save the progress bubbled up from a sub-step to the database
        """
        self.conduit.set_progress(self.get_progress_report())


class PublishStep(object):

    def __init__(self, step_id):
        """
        Set the default parent, step_id and unit_type for the the publish step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_id: The id of the step this processes
        :type step_id: str
        :param unit_type: The type of unit this step processes
        :type unit_type: str or list of str
        """
        self.parent = None
        self.step_id = step_id
        self.canceled = False

        self.state = reporting_constants.STATE_NOT_STARTED
        self.progress_successes = 0
        self.progress_failures = 0
        self.error_details = []
        self.total_units = 1

    def get_working_dir(self):
        """
        Return the working directory

        :returns: the working directory from the parent
        :rtype: str
        """
        return self.parent.working_dir

    def get_repo(self):
        """
        :returns: the repoository for this publish action
        :rtype: pulp.plugins.model.Repository
        """
        return self.parent.repo

    def get_conduit(self):
        """
        :returns: Return the conduit for this publish action
        :rtype: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        """
        return self.parent.conduit

    def get_step(self, step_id):
        """
        get a step from the parent
        :returns: the a step from the parent matching the given id
        """
        return self.parent.get_step(step_id)

    def is_skipped(self):
        """
        Test to find out if the step should be skipped.

        :return: whether or not the step should be skipped
        :rtype:  bool
        """
        return False

    def initialize_metadata(self):
        """
        Method called to initialize metadata after units are processed
        """
        pass

    def finalize_metadata(self):
        """
        Method called to finalize metadata after units are processed
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

        _LOG.debug('Processing publish step of type %(type)s for repository: %(repo)s' %
                   {'type': self.step_id, 'repo': self.parent.repo.id})

        total = 0
        try:
            self.total_units = self._get_total()
            total = self.total_units
            if total == 0:
                self.state = reporting_constants.STATE_COMPLETE
                return
            self.initialize_metadata()
            self.report_progress()
            self._process_block()
            # Double check & return if we have been canceled
            if self.canceled:
                return
        except Exception:
            e_type, e_value, tb = sys.exc_info()
            self._record_failure(e_value, tb)
            self.state = reporting_constants.STATE_FAILED
            raise

        finally:
            try:
                # Only finalize the metadata if we would have made it to initialization
                if total != 0:
                    self.finalize_metadata()
            except Exception, e:
                # on the off chance that one of the finalize steps raise an exception we need to
                # record it as a failure.  If a finalize does fail that error should take precedence
                # over a previous error
                self._record_failure(e)
                self.state = reporting_constants.STATE_FAILED
                raise

        self.state = reporting_constants.STATE_COMPLETE

    def _process_block(self):
        """
        This block is called for the main processing loop
        """
        self.process_main()
        self.report_progress()
        self.progress_successes += 1

    def _get_total(self):
        """
        Process steps default to one action.
        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.
        """
        return 1

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

    def report_progress(self):
        """
        Bubble up that something has changed where progess should be reported.
        It is up to the parent to determine what actions should be taken.
        """
        self.parent.report_progress()

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
            error_details['error'] = e.message or str(e)

        if error_details.values() != (None, None):
            self.error_details.append(error_details)

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

    def cancel(self):
        """
        Cancel the current step
        """
        if self.state not in reporting_constants.FINAL_STATES:
            self.state = reporting_constants.STATE_CANCELLED
            self.canceled = True

    def get_progress_report(self):
        """
        Return the machine readable progress report for this task

        :returns: The machine readable progress report for this task
        :rtype: dict
        """
        total_processed = self.progress_successes + self.progress_failures
        return {
            reporting_constants.PROGRESS_SUCCESSES_KEY: self.progress_successes,
            reporting_constants.PROGRESS_STATE_KEY: self.state,
            reporting_constants.PROGRESS_ERROR_DETAILS_KEY: self.error_details,
            reporting_constants.PROGRESS_PROCESSED_KEY: total_processed,
            reporting_constants.PROGRESS_FAILURES_KEY: self.progress_failures,
            reporting_constants.PROGRESS_TOTAL_KEY: self.total_units
        }

    def get_progress_report_summary(self):
        """
        Get the human readable summary of this tasks state
        :returns: The human readable progress for this task
        :rtype: dict
        """
        return {
            self.step_id: self.state
        }


class UnitPublishStep(PublishStep):

    def __init__(self, step_id, unit_type=None):
        """
        Set the default parent, step_id and unit_type for the the publish step
        the unit_type defaults to none since some steps are not used for processing units.

        :param step_id: The id of the step this processes
        :type step_id: str
        :param unit_type: The type of unit this step processes
        :type unit_type: str or list of str
        """
        super(UnitPublishStep, self).__init__(step_id)
        self.unit_type = unit_type

    def get_unit_generator(self):
        """
        This method returns a generator for the unit_type specified on the PublishStep.
        The units created by this generator will be iterated over by the process_unit method.

        :return: generator of units
        :rtype:  GeneratorTyp of Units
        """
        criteria = UnitAssociationCriteria(type_ids=[self.unit_type])
        return self.parent.conduit.get_units(criteria, as_generator=True)

    def is_skipped(self):
        """
        Test to find out if the step should be skipped.

        :return: whether or not the step should be skipped
        :rtype:  bool
        """
        return self.unit_type in self.parent.skip_list

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
        self.report_progress()

        for package_unit in package_unit_generator:
            if self.canceled:
                return
            self.process_unit(package_unit)
            self.progress_successes += 1
        self.report_progress()

    def _get_total(self, id_list=None):
        """
        Return the total number of units that are processed by this step.
        This is used generally for progress reporting.  The value returned should not change
        during the processing of the step.
        """
        if id_list is None:
            id_list = self.unit_type
        total = 0
        if isinstance(id_list, list):
            for type_id in id_list:
                total += self.parent.repo.content_unit_counts.get(type_id, 0)
        else:
            total = self.parent.repo.content_unit_counts.get(id_list, 0)
        return total
