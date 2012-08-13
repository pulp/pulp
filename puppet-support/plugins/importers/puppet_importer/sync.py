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

from   datetime import datetime
from   gettext import gettext as _
import sys
import traceback

import downloaders
from   pulp_puppet.common import constants
from   pulp_puppet.common.model import RepositoryMetadata, Module

from   pulp.plugins.conduits.mixins import UnitAssociationCriteria

# -- constants ----------------------------------------------------------------

STATE_NOT_STARTED = 'not-started'
STATE_RUNNING = 'running'
STATE_SUCCESS = 'success'
STATE_FAILED = 'failed'

INCOMPLETE_STATES = (STATE_NOT_STARTED, STATE_RUNNING, STATE_FAILED)

# -- public classes -----------------------------------------------------------

class PuppetModuleSyncRun(object):

    def __init__(self, repo, sync_conduit, config):
        self.repo = repo
        self.sync_conduit = sync_conduit
        self.config = config

        self.progress_report = ProgressReport(sync_conduit)

    def perform_sync(self):
        """
        Performs the sync operation according to the configured state of the
        instance. The report to be sent back to Pulp is returned from this
        call. This call will make calls into the conduit's progress update
        as appropriate.

        This call executes serially. No threads are created by this call. It
        will not return until either a step fails or the entire sync is
        completed.

        :return: the report object to return to Pulp from the sync call
        """

        try:
            metadata = self._parse_metadata()
            if not metadata:
                return

            self._import_modules(metadata)
        finally:
            # One final progress update before finishing
            self._update_progress()

            report = self.progress_report.build_final_report()
            return report

    def _parse_metadata(self):
        """
        Takes the necessary actions (according to the run configuration) to
        retrieve and parse the repository's metadata. This call will return
        either the successfully parsed metadata or None if it could not
        be retrieved or parsed. The progress report will be updated with the
        appropriate description of what went wrong in the event of an error,
        so the caller should interpet a None return as an error occuring and
        not continue the sync.

        :return: object representation of the metadata
        :rtype:  RepositoryMetadata
        """
        self.progress_report.metadata_state = STATE_RUNNING
        self._update_progress()

        start_time = datetime.now()

        # Retrieve the metadata from the source
        try:
            downloader = self._create_downloader()
            metadata_json = downloader.retrieve_metadata(self.config)
        except Exception, e:
            self.progress_report.metadata_state = STATE_FAILED
            self.progress_report.metadata_error_message = _('Error downloading metadata')
            self.progress_report.metadata_exception = e
            self.progress_report.metadata_traceback = sys.exc_info()[3]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.metadata_execution_time = duration

            self._update_progress()

            return None

        # Parse the retrieved metadata
        try:
            metadata = RepositoryMetadata.from_json(metadata_json)
        except Exception, e:
            self.progress_report.metadata_state = STATE_FAILED
            self.progress_report.metadata_error_message = _('Error parsing repository modules metadata document')
            self.progress_report.metadata_exception = e
            self.progress_report.metadata_traceback = sys.exc_info()[3]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.metadata_execution_time = duration

            self._update_progress()

            return None

        # Last update to the progress report before returning
        self.progress_report.metadata_state = STATE_SUCCESS

        end_time = datetime.now()
        duration = end_time - start_time
        self.progress_report.metadata_execution_time = duration

        self._update_progress()

        return metadata

    def _import_modules(self, metadata):
        """
        Imports each module in the repository into Pulp.

        This method is mostly just a wrapper on top of the actual logic
        of performing an import to set the stage for the progress report and
        more importantly catch any rogue exceptions that crop up.

        :param metadata: object representation of the repository metadata
               containing the modules to import
        :type  metadata: RepositoryMetadata
        """
        self.progress_report.modules_state = STATE_RUNNING
        self.progress_report.modules_total_count = len(metadata.modules)
        self.progress_report.modules_finished_count = 0
        self.progress_report.modules_error_count = 0
        self._update_progress()

        start_time = datetime.now()

        # Perform the actual logic
        try:
            self._do_import_modules(metadata)
        except Exception, e:
            self.progress_report.modules_state = STATE_FAILED
            self.progress_report.modules_error_message = _('Error retrieving modules')
            self.progress_report.modules_exception = e
            self.progress_report.modules_traceback = sys.exc_info()[3]

            end_time = datetime.now()
            duration = end_time - start_time
            self.progress_report.modules_execution_time = duration

            self._update_progress()

            return None

        # Last update to the progress report before returning
        self.progress_report.metadata_state = STATE_SUCCESS

        end_time = datetime.now()
        duration = end_time - start_time
        self.progress_report.metadata_execution_time = duration

        self._update_progress()

    def _do_import_modules(self, metadata):
        """
        Actual logic of the import. This method will do a best effort per module;
        if an individual module fails it will be recorded and the import will
        continue. This method will only raise an exception in an extreme case
        where it cannot react and continue.
        """

        downloader = self._create_downloader()

        # Ease lookup of modules
        modules_by_key = dict([(m.unit_key(), m) for m in metadata.modules])

        # Collect information about the repository's modules before changing it
        module_criteria = UnitAssociationCriteria(type_ids=[constants.TYPE_PUPPET_MODULE])
        existing_units = self.sync_conduit.get_units(criteria=module_criteria)
        existing_modules = [Module.from_dict(x) for x in existing_units]
        existing_module_keys = [m.unit_key() for m in existing_modules]

        new_unit_keys = self._resolve_new_units(existing_module_keys, modules_by_key.keys())
        remove_unit_keys = self._resolve_remove_units(existing_module_keys, modules_by_key.keys())

        # Add new units
        for key in new_unit_keys:
            module = modules_by_key[key]
            try:
                self._add_new_module(downloader, module)
                self.progress_report.modules_finished_count += 1
            except Exception, e:
                self.progress_report.add_failed_module(module, sys.exc_info()[3])

            self._update_progress()

        # Remove missing units if the configuration indicates to do so
        if self._should_remove_missing():
            existing_units_by_key = [Module.generate_unit_key(u.metadata['name'], u.metadata['version'], u.metadata['author']) for u in existing_units]

            for key in remove_unit_keys:
                doomed = existing_units_by_key[key]
                self.sync_conduit.remove_unit(doomed)

    def _add_new_module(self, downloader, module):
        """
        Performs the tasks for downloading and saving a new unit in Pulp.

        :param downloader: downloader instance to use for retrieving the unit
        :param module: module instance to download
        :type  module: Module
        """
        # Initialize the unit in Pulp
        type_id = constants.TYPE_PUPPET_MODULE
        unit_key = module.unit_key()
        unit_metadata = module.unit_metadata()
        relative_path = constants.STORAGE_MODULE_RELATIVE_PATH % module.filename()

        unit = self.sync_conduit.init_unit(type_id, unit_key, unit_metadata, relative_path)

        # Download the bits
        downloader.retrieve_module(self.config, module, unit.storage_path)

        # If the bits downloaded successfully, save the unit in Pulp
        self.sync_conduit.save_unit(unit)

    def _resolve_new_units(self, existing_unit_keys, found_unit_keys):
        """
        Returns a list of unit keys that are new to the repository.

        :return: list of unit keys; empty list if none are new
        :rtype:  list
        """
        return list(set(found_unit_keys) - set(existing_unit_keys))

    def _resolve_remove_units(self, existing_unit_keys, found_unit_keys):
        """
        Returns a list of unit keys that are in the repository but not in
        the current repository metadata.

        :return: list of unit keys; empty list if none have been removed
        :rtype:  list
        """
        return list(set(existing_unit_keys) - set(found_unit_keys))

    def _create_downloader(self):
        """
        Uses the configuratoin to determine which downloader style to use
        for this run.

        :return: one of the *Downloader classes in the downloaders module
        """

        # This will eventually check the config and make a decision. For now,
        # we're only supporting local directory import so simply return that
        # downloader.

        return downloaders.LocalDownloader()

    def _should_remove_missing(self):
        """
        Returns whether or not missing units should be removed.

        :return: true if missing units should be removed; false otherwise
        :rtype:  bool
        """

        if constants.CONFIG_REMOVE_MISSING not in self.config.keys():
            return constants.DEFAULT_REMOVE_MISSING
        else:
            return self.config.get(constants.CONFIG_REMOVE_MISSING).lower() == 'true'

    def _update_progress(self):
        """
        Sends the current state of the progress report to Pulp.
        """
        report = self.progress_report.build_progress_report()
        self.sync_conduit.set_progress(report)

# -- private classes ----------------------------------------------------------

class ProgressReport(object):
    """
    Used to carry the state of the sync run as it proceeds. This object is used
    to update the on going progress in Pulp at appropriate intervals through
    the update_progress call. Once the sync is finished, this object should
    be used to produce the final report to return to Pulp to describe the
    sync.
    """

    def __init__(self, conduit):

        self.conduit = conduit

        # Metadata download & parsing
        self.metadata_state = STATE_NOT_STARTED
        self.metadata_execution_time = None
        self.metadata_error_message = None
        self.metadata_exception = None
        self.metadata_traceback = None

        # Module download
        self.modules_state = STATE_NOT_STARTED
        self.modules_execution_time = None
        self.modules_total_count = None
        self.modules_finished_count = None
        self.modules_error_count = None
        self.modules_individual_errors = None # mapping of module to its error
        self.modules_error_message = None # overall execution error
        self.modules_exception = None
        self.modules_traceback = None

    def build_final_report(self):
        """
        Assembles the final report to return to Pulp at the end of the sync.
        The conduit will include information that it has tracked over the
        course of its usage, therefore this call should only be invoked
        when it is time to return the report.
        """

        # Report fields
        total_execution_time = None
        if self.metadata_execution_time and self.modules_execution_time:
            total_execution_time = self.metadata_execution_time + self.modules_execution_time

        summary = {
            'total_execution_time' : total_execution_time
        }

        details = {
            'total_count' : self.modules_total_count,
            'finished_count' : self.modules_finished_count,
            'error_count' : self.modules_error_count,
        }

        # Determine if the report was successful or failed
        all_step_states = (self.metadata_state, self.modules_state)
        incomplete_steps = [s for s in all_step_states if s in INCOMPLETE_STATES]

        if len(incomplete_steps) == 0:
            report = self.conduit.build_success_report(summary, details)
        else:
            report = self.conduit.build_failure_report(summary, details)

        return report

    def build_progress_report(self):
        """
        Returns the actual report that should be sent to Pulp as the current
        progress of the sync.

        :return: description of the current state of the sync
        :rtype:  dict
        """

        report = {
            'metadata' : self._metadata_section(),
            'modules'  : self._modules_section(),
        }
        return report

    def add_failed_module(self, module, traceback):
        """
        Updates the progress report that a module failed to be imported.
        """
        self.modules_error_count += 1
        ind_errors = self.modules_individual_errors or {}
        ind_errors[module.unit_key()] = self.format_traceback(traceback)

    # -- report creation methods ----------------------------------------------

    def _metadata_section(self):
        metadata_report = {
            'state' : self.metadata_state,
            'error_message' : self.metadata_error_message,
            'error' : self.format_exception(self.metadata_exception),
            'traceback' : self.format_traceback(self.metadata_traceback),
        }
        metadata_report = self.strip_none(metadata_report)
        return metadata_report

    def _modules_section(self):
        modules_report = {
            'state' : self.modules_state,
            'total_count' : self.modules_total_count,
            'finished_count' : self.modules_finished_count,
            'error_count' : self.modules_error_count,
            'individual_errors' : self.modules_individual_errors,
            'error_message' : self.modules_error_message,
            'error' : self.format_exception(self.modules_exception),
            'traceback' : self.format_traceback(self.modules_traceback),
        }
        modules_report = self.strip_none(modules_report)
        return modules_report

    # -- report utility methods -----------------------------------------------

    @staticmethod
    def strip_none(report):
        """
        Removes all keys whose values are None. Returns a new report; does not
        edit the existing report.

        :return: new dictionary without any keys whose value was None
        :rtype:  dict
        """
        clean = dict([(k, v) for k, v in report.items() if v is not None])
        return clean

    @staticmethod
    def format_exception(e):
        """
        Formats the given exception to be included in the report.

        :return: string representtion of the exception
        :rtype:  str
        """
        if e:
            return e[0]
        else:
            return None

    @staticmethod
    def format_traceback(tb):
        """
        Formats the given traceback to be included in the report.

        :return: string representation of the traceback
        :rtype:  str
        """
        if tb:
            return traceback.extract_tb(tb)
        else:
            return None
