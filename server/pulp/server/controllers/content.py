# -*- coding: utf-8 -*-
from gettext import gettext as _
from logging import getLogger
import os
import threading

import celery
from nectar.request import DownloadRequest
from nectar.listener import AggregatingEventListener

from pulp.common import error_codes
from pulp.common.plugins import reporting_constants
from pulp.common.tags import resource_tag, action_tag, RESOURCE_CONTENT_UNIT_TYPE
from pulp.plugins.conduits.mixins import (ContentSourcesConduitException, StatusMixin,
                                          PublishReportMixin)
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader.exceptions import PluginNotFound
from pulp.plugins.util.publish_step import Step
from pulp.server.async.tasks import Task
from pulp.server.controllers import repository
from pulp.server.content.sources.container import ContentContainer
from pulp.server.exceptions import PulpCodedTaskException
from pulp.server.managers.repo._common import get_working_directory


_logger = getLogger(__name__)


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
            self.progress_details = self.progress_description
            report = item.refresh(e)[0]
            if not report.succeeded:
                raise PulpCodedTaskException(error_code=error_codes.PLP0031, id=report.source_id,
                                             url=report.url)

    def _get_total(self):
        return len(self.sources)


@celery.task(base=Task, name='pulp.server.tasks.content.refresh_content_sources')
def refresh_content_sources():
    """
    Refresh the content catalog using available content sources.
    """
    conduit = ContentSourcesConduit('Refresh Content Sources')
    step = ContentSourcesRefreshStep(conduit)
    step.process_lifecycle()


@celery.task(base=Task, name='pulp.server.tasks.content.refresh_content_source')
def refresh_content_source(content_source_id=None):
    """
    Refresh the content catalog from a specific content source.
    """
    conduit = ContentSourcesConduit('Refresh Content Source')
    step = ContentSourcesRefreshStep(conduit, content_source_id=content_source_id)
    step.process_lifecycle()


@celery.task(base=Task)
def _download(plugin_id, unit_locator, url, options):
    """
    Download the specified content unit.

    :param plugin_id: A repository-importer database object ID.
    :type plugin_id: str
    :param unit_locator: A unit locator.
    :type unit_locator: pulp.server.db.model.UnitLocator
    :param url: The download URL.
    :type url: str
    :param options: Passed to the Importer.get_downloader().
    :type options: dict
    """
    _logger.info(_('Downloading: {url}').format(url=url))

    # Find the plugin
    try:
        importer, cfg = repository.get_importer_by_id(plugin_id)
    except PluginNotFound:
        _logger.info(_('Download {url}, failed - plugin not found').format(url=url))
        return

    # Find the model
    model = plugin_api.get_unit_model_by_id(unit_locator.type_id)
    if model is None:
        _logger.info(_('Download {url}, failed - model not found').format(url=url))
        return

    # Fetch the unit
    unit = model.objects(id=unit_locator.unit_id).get()
    if unit is None:
        _logger.info(_('Download {url}, failed - unit not found').format(url=url))
        return

    if os.path.exists(unit.storage_path):
        # Already downloaded
        return

    # Prepare the download
    working_dir = get_working_directory()
    destination = os.path.join(working_dir, unit_locator.unit_id)
    request = DownloadRequest(url, destination)
    listener = AggregatingEventListener()
    downloader = importer.get_downloader(cfg, url, **options)
    downloader.event_listener = listener

    # Download and store the unit
    downloader.download_one(request, events=True)
    if listener.succeeded_reports:
        _logger.info(_('Download {url}, succeeded').format(url=url))
        unit.set_content(destination)
        unit.save()
    else:
        report = listener.failed_reports[0]
        _logger.info(
            _('Download {url}, failed: {reason}').format(url=url, reason=report.error_msg))


def queue_download(plugin_id, unit_locator, url, options):
    """
    Queue task to download the specified content unit.

    :param plugin_id: A repository-importer database object ID.
    :type plugin_id: str
    :param unit_locator: A unit locator.
    :type unit_locator: pulp.server.db.model.UnitLocator
    :param url: The download URL.
    :type url: str
    :param options: Passed to the Importer.get_downloader().
    :type options: dict
    """
    tags = [
        resource_tag(RESOURCE_CONTENT_UNIT_TYPE, unit_locator.unit_id),
        action_tag('download')
    ]
    _download.apply_async_with_reservation(
        RESOURCE_CONTENT_UNIT_TYPE,
        unit_locator.unit_id,
        [plugin_id, unit_locator, url, options],
        tags=tags)
