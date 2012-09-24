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

from gettext import gettext as _

from pulp.client.commands.repo.status import status, tasks
from pulp.client.commands.repo.sync_publish import RunPublishRepositoryCommand, PublishStatusCommand

from pulp_rpm.extension.admin.status import RpmStatusRenderer, RpmIsoStatusRenderer

from pulp.client.extensions.extensions import PulpCliCommand

# -- constants ----------------------------------------------------------------

YUM_DISTRIBUTOR_TYPE_ID = 'yum_distributor'
ISO_DISTRIBUTOR_TYPE_ID = 'iso_distributor'

# -- commands -----------------------------------------------------------------


# This is not implemented completely yet. Once we have renderers in place for iso and yum publish, RunPublishCommand
# will call RunYumPublishCommand and RunIsoPublishCommand as per distributor_id passed. 

class RpmRunPublishCommand(RunPublishRepositoryCommand):
    def __init__(self, context):
        super(RpmRunPublishCommand, self).__init__(context=context, method=self.publish)
        
        # In the RPM client, there are 2 distributors associated with a repo now, 
        # so we need to ask user for the distributor ID.
        self.create_option('--distributor-id', _('identifies the distributor to be used to publish repo'), required=True)

    def publish(self, **kwargs):
        self.distributor_id = kwargs['distributor-id']
        
        # Initialize renderer according to distributor type\
        if self.distributor_id == YUM_DISTRIBUTOR_TYPE_ID:
            self.renderer = RpmStatusRenderer(self.context)
        elif self.distributor_id == ISO_DISTRIBUTOR_TYPE_ID:
            self.renderer = RpmIsoStatusRenderer(self.context)
        else:
            self.prompt.render_failure_message(_('Invalid distributor type'))

        super(RpmRunPublishCommand, self).run(**kwargs)


class StatusCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.status)
        self.context = context

        self.create_option('--repo-id', _('identifies the repository'), required=True)

    def status(self, **kwargs):
        repo_id = kwargs['repo-id']
        self.context.prompt.render_title(_('Repository Status [%(r)s]') % {'r' : repo_id})

        # This looks dumb but the task lookup doesn't know if there are no tasks
        # for a repo v. the repo doesn't exist. We call this to let the not found
        # exception bubble if it's not a valid repo.
        self.context.server.repo.repository(repo_id)

        # Load the existing sync tasks
        existing_publish_tasks = self.context.server.tasks.get_repo_publish_tasks(repo_id).response_body
        task_id = tasks.relevant_existing_task_id(existing_publish_tasks)

        if task_id is not None:
            msg = 'A publish task is queued on the server. Its progress will be tracked below.'
            self.context.prompt.render_paragraph(_(msg))
            status.display_task_status(self.context, task_id=task_id)

        else:
            self.context.prompt.render_paragraph(_('There are no publish tasks currently queued in the server.'))
