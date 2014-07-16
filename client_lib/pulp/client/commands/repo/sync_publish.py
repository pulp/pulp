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
"""
Commands and hooks for creating and using sync, publish, and progress status
commands.
"""
from gettext import gettext as _

from datetime import datetime

from pulp.bindings import responses
from pulp.client.commands import options, polling
from pulp.client.extensions.extensions import PulpCliOptionGroup
from pulp.common import tags
from pulp.common.plugins.progress import SyncProgressReport


# Command Descriptions
DESC_SYNC_RUN = _('triggers an immediate sync of a repository')
DESC_SYNC_STATUS = _('displays the status of a repository\'s sync tasks')

DESC_PUBLISH_RUN = _('triggers an immediate publish of a repository')
DESC_PUBLISH_STATUS = _('displays the status of a repository\'s publish tasks')


class StatusRenderer(object):

    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

    def display_report(self, progress_report):
        raise NotImplementedError()

class SyncStatusRenderer(StatusRenderer):

    def __init__(self, context):
        """
        Initialize status renderer.

        :param context:     The CLI context from Okaara
        :type  context:     pulp.client.extensions.core.ClientContext
        """
        super(SyncStatusRenderer, self).__init__(context)
        self._sync_files_bar = self.prompt.create_progress_bar()
        self._sync_state = SyncProgressReport.STATE_NOT_STARTED

    def _display_sync_report(self, sync_report, unit_noun):
        """
        Display the retrieval step.

        :param sync_report: sync report
        :type  sync_report: pulp.common.plugins.progress.SyncProgressReport
        :param unit_noun: the word to use for whatever's being synced. Examples are "images",
                          "files", etc.
        :type  unit_noun: str
        """
        if (self._sync_state == sync_report.STATE_MANIFEST_IN_PROGRESS and
                sync_report.state != sync_report.STATE_MANIFEST_IN_PROGRESS):
            if sync_report.num_files:
                self.prompt.write(_('Downloading %(num)s %(noun)s...') %
                                  {'num': sync_report.num_files,
                                   'noun': unit_noun},
                                  tag='download_starting')
                self._sync_state = sync_report.STATE_FILES_IN_PROGRESS
            else:
                self.prompt.render_success_message(
                    _('There are no %s that need to be downloaded.') % unit_noun,
                    tag='none_to_download')
                self._sync_state = sync_report.STATE_COMPLETE

        if self._sync_state == sync_report.STATE_FILES_IN_PROGRESS:
            if sync_report.total_bytes:
                runtime = (datetime.utcnow() -
                           sync_report.state_times[sync_report.STATE_MANIFEST_IN_PROGRESS])
                runtime = (runtime.days * 3600 * 24) + runtime.seconds
                if runtime:
                    average_speed = self.human_readable_bytes(sync_report.finished_bytes / runtime)
                else:
                    average_speed = 0
                bar_message = _("%(noun)s: %(num_complete)s/%(num_total)s\tData: "
                                "%(bytes_complete)s/%(bytes_total)s\tAvg: %(speed)s/s")
                bar_message = bar_message % {
                    'noun': unit_noun,
                    'num_complete': sync_report.num_files_finished,
                    'num_total': sync_report.num_files,
                    'speed': average_speed,
                    'bytes_complete': self.human_readable_bytes(sync_report.finished_bytes),
                    'bytes_total': self.human_readable_bytes(sync_report.total_bytes)}
                self._sync_files_bar.render(sync_report.finished_bytes, sync_report.total_bytes,
                                            message=bar_message)
            if sync_report.state != sync_report.STATE_FILES_IN_PROGRESS:
                self.prompt.write('\n')
                if sync_report.state == sync_report.STATE_COMPLETE:
                    msg = _('Successfully downloaded %(num)s %(noun)s.') % {
                        'num': sync_report.num_files,
                        'noun': unit_noun}
                    self.prompt.render_success_message(msg, tag='download_success')
                else:
                    msg = _('Failed to retrieve %(num)s %(noun)s.')
                    msg = msg % {'num': sync_report.num_files - sync_report.num_files_finished,
                                 'noun': unit_noun}
                    self.prompt.render_failure_message(msg, tag='download_failed')
                    for failed_file in sync_report.files_error_messages:
                        self.prompt.render_failure_message('\t%(name)s: %(msg)s' %
                                                           {'name': failed_file['name'],
                                                            'msg': failed_file['error']},
                                                           tag='file_error_msg')
                self._sync_state = sync_report.state

    def human_readable_bytes(self, num):
        """
        This handy snippet was retrieved from
        http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        It takes a size in Bytes, and converts it to a nice human readable form.
        :param num: number to convert
        :type  num: int
        :return: bytes in human-readable format
        :rtype: string
        """
        for x in ['B', 'kB', 'MB', 'GB']:
            if num < 1024.0:
                if x == 'B':
                    return '%s %s' % (num, x)
                else:
                    return "%3.1f %s" % (num, x)
            num /= 1024.0
        return "%3.1f %s" % (num, 'TB')

    def _display_manifest_sync_report(self, sync_report, manifest_noun):
        """
        Display the manifest retrieval step.

        :param sync_report: sync report
        :type  sync_report: pulp.common.plugins.progress.SyncProgressReport
        :param manifest_noun: name of the manifest ("image manifest", "yum metadata", etc)
        :type  manifest_noun: str
        """
        # We should skip this step if the sync hasn't begun
        if sync_report.state == sync_report.STATE_NOT_STARTED:
            return

        if (sync_report.state == sync_report.STATE_MANIFEST_FAILED and
                self._sync_state != sync_report.STATE_MANIFEST_FAILED):
            self.prompt.render_failure_message(_('Downloading the %s failed:') % manifest_noun,
                                               tag='manifest_failed')
            self.prompt.render_failure_message('\t%s' % sync_report.error_message,
                                               tag='manifest_error_message')
            self._sync_state = sync_report.STATE_MANIFEST_FAILED
            return

        if self._sync_state == sync_report.STATE_NOT_STARTED:
            # The sync_report has moved on, so let's respond
            self._sync_state = sync_report.STATE_MANIFEST_IN_PROGRESS

            if sync_report.state == sync_report.STATE_MANIFEST_IN_PROGRESS:
                self.prompt.write(_('Downloading the %s...') % manifest_noun,
                                  tag='downloading_manifest')

        if (self._sync_state == sync_report.STATE_MANIFEST_IN_PROGRESS and
                sync_report.state != sync_report.STATE_MANIFEST_IN_PROGRESS):
            self.prompt.render_success_message(_('The %s was downloaded successfully.')
                                               % manifest_noun,
                                               tag='manifest_downloaded')


class SyncPublishCommand(polling.PollingCommand):
    """
    This class contains common behaviors found in the sync and publish commands in this module. It is not
    intended to be used by itself. It is intended to be used as a common superclass.
    """
    def __init__(self, name, description, method, context, renderer):
        """
        Initialize the command, and call the superclass __init__().

        :param name:        The name of the command
        :type  name:        basestring
        :param description: The description of the command
        :type  description: basestring
        :param method:      The method to be run if the command is used
        :type  method:      callable
        :param context:     The CLI context from Okaara
        :type  context:     pulp.client.extensions.core.ClientContext
        :param renderer:    The renderer to be used to print progress reports
        :type  renderer:    StatusRenderer
        """
        if method is None:
            method = self.run

        super(SyncPublishCommand, self).__init__(name, description, method, context)

        self.renderer = renderer
        self.add_option(options.OPTION_REPO_ID)
        self.context = context
        self.prompt = context.prompt

    def progress(self, task, spinner):
        """
        Render the progress report, if it is available on the given task.

        :param task:    The Task that we wish to render progress about
        :type  task:    pulp.bindings.responses.Task
        :param spinner: Not used by this method, but the superclass will give it to us
        :type  spinner: okaara.progress.Spinner
        """
        if task.progress_report is not None:
            self.renderer.display_report(task.progress_report)

    def task_header(self, task):
        """
        We don't want any task header printed for this task, so we need to override the superclass behavior.

        :param task: The Task that we don't want to do anything with. Unused.
        :type  task: pulp.bindings.responses.Task
        """
        pass


class RunSyncRepositoryCommand(SyncPublishCommand):
    """
    Requests an immediate sync for a repository. If the sync begins (it is not
    postponed or rejected), the provided renderer will be used to track its
    progress. The user has the option to exit the progress polling or skip it
    entirely through a flag on the run command.
    """

    def __init__(self, context, renderer, name='run', description=DESC_SYNC_RUN, method=None):
        """
        :type renderer: pulp.client.commands.repo.sync_publish.StatusRenderer
        """
        super(RunSyncRepositoryCommand, self).__init__(name, description, method, context, renderer)

    def run(self, **kwargs):
        """
        If there are existing sync tasks running, attach to them and display their progress reports. Else,
        queue a new sync task and display its progress report.

        :param kwargs: The user input
        :type  kwargs: dict
        """
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        background = kwargs[polling.FLAG_BACKGROUND.keyword]

        self.prompt.render_title(_('Synchronizing Repository [%(r)s]') % {'r' : repo_id})

        # See if an existing sync is running for the repo. If it is, resume
        # progress tracking.
        existing_sync_tasks = _get_repo_tasks(self.context, repo_id, 'sync')

        if existing_sync_tasks:
            msg = _('A sync task is already in progress for this repository. ')
            if not background:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg, tag='in-progress')
            self.poll(existing_sync_tasks, kwargs)

        else:
            # Trigger the actual sync
            response = self.context.server.repo_actions.sync(repo_id, None)
            sync_task = response.response_body
            self.poll([sync_task], kwargs)


class SyncStatusCommand(SyncPublishCommand):
    def __init__(self, context, renderer, name='status', description=DESC_SYNC_STATUS, method=None):
        super(SyncStatusCommand, self).__init__(name, description, method, context, renderer)

    def run(self, **kwargs):
        """
        Query the server to find any existing and incomplete sync Tasks. If found, attach to them and display
        their progress. If not, display and error and return.

        :param kwargs: The user input
        :type  kwargs: dict
        """
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        self.prompt.render_title(_('Repository Status [%(r)s]') % {'r' : repo_id})

        # Load the relevant task group
        existing_sync_tasks = _get_repo_tasks(self.context, repo_id, 'sync')

        if not existing_sync_tasks:
            msg = _('The repository is not performing any operations')
            self.prompt.render_paragraph(msg, tag='no-tasks')
        else:
            self.poll(existing_sync_tasks, kwargs)


class RunPublishRepositoryCommand(SyncPublishCommand):
    """
    Base class for repo publish operation.

    Requests an immediate publish for a repository. Specified distributor_id is used
    for publishing. If the publish begins (it is not postponed or rejected),
    the provided renderer will be used to track its progress. The user has the option
    to exit the progress polling or skip it entirely through a flag on the run command.
    List of additional configuration override options can be passed in override_config_options.
    """

    def __init__(self, context, renderer, distributor_id, name='run', description=DESC_PUBLISH_RUN,
                 method=None, override_config_options=()):
        """
        :param context: Pulp client context
        :type context: See okaara

        :param renderer: StatusRenderer subclass that will interpret the sync or publish progress report
        :type  renderer: StatusRenderer

        :param distributor_id: Id of a distributor to be used for publishing
        :type distributor_id: str

        :param override_config_options: Additional publish options to be accepted from user. These options will override
            respective options from the default publish config. Each entry should be
            either a PulpCliOption or PulpCliFlag instance
        :type override_config_options: list
        """
        super(RunPublishRepositoryCommand, self).__init__(name, description, method, context, renderer)

        self.distributor_id = distributor_id
        self.override_config_keywords = []

        # Process and add config override options in their own group and save option keywords
        if override_config_options:
            override_config_group = PulpCliOptionGroup(_("Publish Options"))
            self.add_option_group(override_config_group)

            for option in override_config_options:
                override_config_group.add_option(option)
                self.override_config_keywords.append(option.keyword)

    def run(self, **kwargs):
        """
        Run the publish operation on the server, or if one is already running, attach to it.

        :param kwargs: The user inputs
        :type  kwargs: dict
        """
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        background = kwargs[polling.FLAG_BACKGROUND.keyword]
        override_config = {}

        # Generate override_config if any of the override options are passed.
        if self.override_config_keywords:
            override_config = self.generate_override_config(**kwargs)

        self.prompt.render_title(_('Publishing Repository [%(r)s]') % {'r' : repo_id})

        # Display override configuration used
        if override_config:
            self.prompt.render_paragraph(_('The following publish configuration options will be used:'))
            self.prompt.render_document(override_config)

        # See if an existing publish is running for the repo. If it is, resume
        # progress tracking.
        existing_publish_tasks = _get_repo_tasks(self.context, repo_id, 'publish')

        if existing_publish_tasks:
            msg = _('A publish task is already in progress for this repository. ')
            if not background:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg, tag='in-progress')
            self.poll(existing_publish_tasks, kwargs)
        else:
            if not override_config:
                override_config = None
            response = self.context.server.repo_actions.publish(repo_id, self.distributor_id, override_config)
            task_id = response.response_body
            self.poll([task_id], kwargs)

    def generate_override_config(self, **kwargs):
        """
        Check if any of the override config options is passed by the user and create override_config
        dictionary

        :param kwargs: all keyword arguments passed in by the user on the command line
        :type kwargs:  dict
        :return:       config option dictionary consisting of option values passed by user for valid publish
                       config options (stored in override_config_keywords)
        :rtype:        dict
        """
        override_config = {}
        for option in self.override_config_keywords:
            if kwargs[option]:
                # Replace hyphens in option keywords to underscores eg. iso-prefix to iso_prefix
                override_config[option.replace('-','_')] = kwargs[option]
        return override_config


class PublishStatusCommand(SyncPublishCommand):
    def __init__(self, context, renderer, name='status', description=DESC_PUBLISH_STATUS, method=None):
        super(PublishStatusCommand, self).__init__(name, description, method, context, renderer)

    def run(self, **kwargs):
        """
        Query the server for any incomplete publish operations for the repo given in kwargs. If found, display
        their progress reports. If not, display and error message and return.

        :param kwargs: The user input
        :type  kwargs: dict
        """
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        self.prompt.render_title(_('Repository Status [%(r)s]') % {'r' : repo_id})

        existing_publish_tasks = _get_repo_tasks(self.context, repo_id, 'publish')

        if not existing_publish_tasks:
            msg = _('The repository is not performing any operations')
            self.prompt.render_paragraph(msg, tag='no-tasks')
        else:
            self.poll(existing_publish_tasks, kwargs)


def _get_repo_tasks(context, repo_id, action):
    """
    Retrieve a list of incomplete Task objects for the given repo_id and action. action must be one
    of 'sync' or 'publish'.

    :param context: The CLI context from Okaara
    :type  context: pulp.client.extensions.core.ClientContext
    :param repo_id: The primary key of the repository you wish to limit the Task query to
    :type  repo_id: basestring
    :param action:  One of "sync" or "publish"
    :type  action:  basestring
    :return:        A list of Task objects
    :rtype:         list
    """
    repo_tag = tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id)
    if action == 'publish':
        action_tag = tags.action_tag(tags.ACTION_PUBLISH_TYPE)
    elif action == 'sync':
        action_tag = tags.action_tag(tags.ACTION_SYNC_TYPE)
    else:
        raise ValueError('_get_repo_tasks() does not support %(action)s as an action.' % {'action': action})
    repo_search_criteria = {'filters': {'state': {'$nin': responses.COMPLETED_STATES},
                                        'tags': {'$all': [repo_tag, action_tag]}}}
    return context.server.tasks_search.search(**repo_search_criteria)
