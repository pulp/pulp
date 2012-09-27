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

from pulp.client.commands import options
from pulp.client.commands.repo.status import status, tasks
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOptionGroup

# -- constants ----------------------------------------------------------------

# Command Descriptions

DESC_SYNC_RUN = _('triggers an immediate sync of a repository')
DESC_SYNC_STATUS = _('displays the status of a repository\'s sync tasks')

DESC_PUBLISH_RUN = _('triggers an immediate publish of a repository')
DESC_PUBLISH_STATUS = _('displays the status of a repository\'s publish tasks')

NAME_BACKGROUND = 'bg'
DESC_BACKGROUND = _('if specified, the CLI process will end but the process will continue on '
                    'the server; the progress can be later displayed using the status command')

# -- hooks --------------------------------------------------------------------

class StatusRenderer(object):

    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

    def display_report(self, progress_report):
        raise NotImplementedError()

# -- commands -----------------------------------------------------------------

class RunSyncRepositoryCommand(PulpCliCommand):
    """
    Requests an immediate sync for a repository. If the sync begins (it is not
    postponed or rejected), the provided renderer will be used to track its
    progress. The user has the option to exit the progress polling or skip it
    entirely through a flag on the run command.
    """

    def __init__(self, context, renderer, name='run', description=DESC_SYNC_RUN, method=None):

        if method is None:
            method = self.run

        super(RunSyncRepositoryCommand, self).__init__(name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer

        self.add_option(options.OPTION_REPO_ID)
        self.create_flag('--' + NAME_BACKGROUND, DESC_BACKGROUND)

    def run(self, **kwargs):
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        background = kwargs[NAME_BACKGROUND]

        self.prompt.render_title(_('Synchronizing Repository [%(r)s]') % {'r' : repo_id})

        # See if an existing sync is running for the repo. If it is, resume
        # progress tracking.
        existing_sync_tasks = self.context.server.tasks.get_repo_sync_tasks(repo_id).response_body
        task_group_id = tasks.relevant_existing_task_group_id(existing_sync_tasks)

        if task_group_id is not None:
            msg = _('A sync task is already in progress for this repository. ')
            if not background:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg, tag='in-progress')

        else:
            # Trigger the actual sync
            response = self.context.server.repo_actions.sync(repo_id, None)
            sync_task = tasks.sync_task_in_sync_task_group(response.response_body)
            task_group_id = sync_task.task_group_id

        if not background:
            status.display_group_status(self.context, self.renderer, task_group_id)
        else:
            msg = _('The status of this sync can be displayed using the status command.')
            self.context.prompt.render_paragraph(msg, 'background')


class SyncStatusCommand(PulpCliCommand):
    def __init__(self, context, renderer, name='status', description=DESC_SYNC_STATUS, method=None):

        if method is None:
            method = self.run

        super(SyncStatusCommand, self).__init__(name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer

        self.add_option(options.OPTION_REPO_ID)

    def run(self, **kwargs):
        pass



class RunPublishRepositoryCommand(PulpCliCommand):
    """
    Base class for rpm repo publish operation. 
    
    Requests an immediate publish for a repository. Specified distributor_id is used 
    for publishing. If the publish begins (it is not postponed or rejected), 
    the provided renderer will be used to track its progress. The user has the option 
    to exit the progress polling or skip it entirely through a flag on the run command.
    List of additional configuration override options can be passed in override_config_options.
    """

    def __init__(self, context, renderer, distributor_id, name='run', description=DESC_PUBLISH_RUN, 
                 method=None, override_config_options=[]):
        """
        :param context: Pulp client context
        :type context: See okaara

        :param renderer: StatusRenderer subclass that will interpret the sync or publish progress report
        :type  renderer: StatusRenderer

        :param distributor_id: Id of a distributor to be used for publishing
        :type distributor_id: str

        :param override_config_options: Additional publish options to be accepted from user. These options will override 
                                        respective options from the default publish config.
        :type override_config_options: List of PulpCliOption and PulpCliFlag instances 
        """
        if method is None:
            method = self.run

        super(RunPublishRepositoryCommand, self).__init__(name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer
        self.distributor_id = distributor_id
        self.override_config_keywords = []

        self.add_option(options.OPTION_REPO_ID)
        self.create_flag('--' + NAME_BACKGROUND, DESC_BACKGROUND)

        # Process and add config override options in their own group and save option keywords
        if override_config_options:
            override_config_group = PulpCliOptionGroup(_("Publish Options"))
            self.add_option_group(override_config_group)

            for option in override_config_options:
                override_config_group.add_option(option)
                self.override_config_keywords.append(option.keyword)

    def run(self, **kwargs):
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        background = kwargs[NAME_BACKGROUND]
        override_config = {}
        
        # Generate override_config if any of the override options are passed.
        if self.override_config_keywords:
            override_config = self.generate_override_config(**kwargs)

        self.prompt.render_title(_('Publishing Repository [%(r)s] using distributor [%(d)s] ') % {'r' : repo_id, 'd' : self.distributor_id})

        # Display override configuration used
        if override_config:
            self.prompt.render_paragraph(_('The following publish configuration options will be used:'))
            self.prompt.render_document(override_config)

        # See if an existing publish is running for the repo. If it is, resume
        # progress tracking.
        existing_publish_tasks = self.context.server.tasks.get_repo_publish_tasks(repo_id).response_body
        task_id = tasks.relevant_existing_task_id(existing_publish_tasks)

        if task_id is not None:
            msg = _('A publish task is already in progress for this repository. ')
            if not background:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg, tag='in-progress')

        else:
            if not override_config:
                override_config = None
            response = self.context.server.repo_actions.publish(repo_id, self.distributor_id, override_config)
            task_id = response.response_body.task_id

        if not background:
            status.display_task_status(self.context, self.renderer, task_id)
        else:
            msg = _('The status of this publish can be displayed using the status command.')
            self.context.prompt.render_paragraph(msg, 'background')

            
    def generate_override_config(self, **kwargs):
        """
        Check if any of the override config options is passed by the user and create override_config
        dictionary

        :param kwargs: all keyword arguments passed in by the user on the command line
        :type kwargs: dict

        :return: config option dictionary consisting of option values passed by user for valid publish config options
                 (stored in override_config_keywords)
        :rtype: dict
        """
        override_config = {}
        for option in self.override_config_keywords:
            if kwargs[option]:
                # Replace hyphens in option keywords to underscores eg. iso-prefix to iso_prefix
                override_config[option.replace('-','_')] = kwargs[option]
        return override_config


class PublishStatusCommand(PulpCliCommand):
    def __init__(self, context, renderer, name='status', description=DESC_PUBLISH_STATUS, method=None):

        if method is None:
            method = self.run

        super(PublishStatusCommand, self).__init__(name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer

        self.add_option(options.OPTION_REPO_ID)


    def run(self, **kwargs):
        pass
