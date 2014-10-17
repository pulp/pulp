# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import celery
import logging
import threading
from gettext import gettext as _

from pulp.common import error_codes
from pulp.common.plugins import reporting_constants
from pulp.plugins.conduits.mixins import (ContentSourcesConduitException, StatusMixin,
                                          PublishReportMixin)
from pulp.plugins.util.publish_step import Step
from pulp.server.async.tasks import Task
from pulp.server.content.sources.container import ContentContainer
from pulp.server.exceptions import PulpCodedTaskException


logger = logging.getLogger(__name__)


class ContentSourcesConduit(StatusMixin, PublishReportMixin):
    """
    Used to communicate back into the Pulp server while content sources are
    are being cataloged. Instances of this call should *not* be cached between
    catalog refreshes. Each refresh task will be issued its own conduit
    instance that is scoped to that run alone.

    Instances of this class are thread-safe. Calls into this instance do not
    have to be coordinated for thread safety, the instance will take care of it itself.
    """

    def __init__(self, task_id):
        """
        :param task_id: identifies the task being performed
        :type  task_id: str
        """
        StatusMixin.__init__(self, task_id, ContentSourcesConduitException)
        PublishReportMixin.__init__(self)

    def __str__(self):
        return 'ContentSourcesConduit'


class ContentSourcesRefreshStep(Step):
    """
    Content sources refresh step class that is responsible for refreshing all the content sources
    """

    def __init__(self, refresh_conduit, content_source_id=None):
        """
        :param refresh_conduit: Conduit providing access to relative Pulp functionality
        :type  refresh_conduit: pulp.server.content.sources.steps.ContentSourceConduit
        :param content_source_id: Id of content source to refresh
        :type  str:
        """

        super(ContentSourcesRefreshStep, self).__init__(
            step_type=reporting_constants.REFRESH_STEP_CONTENT_SOURCE,
            status_conduit=refresh_conduit, non_halting_exceptions=[PulpCodedTaskException])

        self.container = ContentContainer()
        if content_source_id:
            self.sources = [self.container.sources[content_source_id]]
        else:
            self.sources = [source for name, source in self.container.sources.iteritems()]
        self.description = _("Refreshing content sources")

    def get_iterator(self):
        return self.sources

    def process_main(self, item=None):
        if item:
            self.progress_description = item.descriptor['name']
            e = threading.Event()
            report = item.refresh(e)[0]
            self.details.append(report.dict())
            self.progress_details = self.details
            if not report.succeeded:
                raise PulpCodedTaskException(error_code=error_codes.PLP0031, id=report.source_id,
                                             url=report.url)

    def initialize(self):
        self.details = []

    def finalize(self):
        self.progress_details = self.details

    def _get_total(self):
        return len(self.sources)


@celery.task(base=Task)
def refresh_content_sources():
    """
    Refresh the content catalog using available content sources.
    """
    conduit = ContentSourcesConduit('Refresh Content Sources')
    step = ContentSourcesRefreshStep(conduit)
    step.process_lifecycle()


@celery.task(base=Task)
def refresh_content_source(content_source_id=None):
    """
    Refresh the content catalog from a specific content source.
    """
    conduit = ContentSourcesConduit('Refresh Content Source')
    step = ContentSourcesRefreshStep(conduit, content_source_id=content_source_id)
    step.process_lifecycle()

