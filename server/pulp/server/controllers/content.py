# -*- coding: utf-8 -*-
from gettext import gettext as _
from logging import getLogger
import os
import threading

import celery
from mongoengine import DoesNotExist
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
from pulp.server.config import config as pulp_conf
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.server.controllers import repository
from pulp.server.content.sources.container import ContentContainer
from pulp.server.content.web.views import ContentView
from pulp.server.db.model import LazyCatalogEntry
from pulp.server.exceptions import PulpCodedTaskException
from pulp.server.lazy import URL, Key
from pulp.server.managers.repo._common import get_working_directory


_logger = getLogger(__name__)

URL_SIGNING_KEY = Key.load(pulp_conf.get('authentication', 'rsa_pub'))


class ModelNotFound(Exception):
    """
    Raised when a content unit Model was not found.
    """
    def __init__(self, model_type):
        self.model_type = model_type

    def __str__(self):
        return _('Model type "{type}" not found.').format(type=self.model_type)


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
def _download_one(catalog_entry):
    """
    Download the content unit specified by the catalog entry.

    :param catalog_entry: The catalog entry to download content for.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry
    """
    _logger.info(_('Downloading {url} via the Pulp streamer').format(url=catalog_entry.url))
    try:
        if os.path.exists(catalog_entry.path):
            # Already downloaded
            return

        _download_catalog_entry(catalog_entry)
    except PluginNotFound:
        msg = _('Download of {url} failed - plugin not found')
        _logger.info(msg.format(url=catalog_entry.url))
    except DoesNotExist:
        msg = _('Download of {url} failed - unit not found')
        _logger.info(msg.format(url=catalog_entry.url))
    except ModelNotFound, e:
        msg = _('Download {url}, failed - {reason}')
        _logger.info(msg.format(url=catalog_entry.url, reason=str(e)))


def _download_catalog_entry(catalog_entry):
    """
    Download a catalog entry.

    :param catalog_entry: The catalog entry associated with the content unit.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry
    """
    content_unit = _get_content_unit(catalog_entry)
    working_dir = get_working_directory()
    destination = os.path.join(working_dir, content_unit.id)
    streamer_url = _get_streamer_url(catalog_entry)
    pulp_header = {PULP_STREAM_REQUEST_HEADER: 'true'}
    request = DownloadRequest(streamer_url, destination, headers=pulp_header)

    importer, importer_config = repository.get_importer_by_id(catalog_entry.importer_id)
    downloader = importer.get_downloader(importer_config, streamer_url, **catalog_entry.data)
    downloader.event_listener = AggregatingEventListener()

    downloader.download_one(request, events=True)
    if downloader.event_listener.succeeded_reports:
        _logger.info(_('Download {url} via {streamer_url} succeeded').format(
            url=catalog_entry.url, streamer_url=request.url))
        content_unit.set_content(request.destination, downloaded=False)
        content_unit.save()
        _update_content_unit_downloaded(content_unit)
    else:
        report = downloader.event_listener.failed_reports[0]
        _logger.info(_('Download {url} via {streamer_url} failed: {reason}').format(
            url=catalog_entry.url, streamer_url=request.url, reason=report.error_msg))


def _update_content_unit_downloaded(content_unit):
    """
    Handle updating a content unit. This method ensures the 'downloaded' flag is
    set correctly.

    :param content_unit: The content unit to update.
    :type  content_unit: pulp.server.db.model.FileContentUnit
    """
    entries = LazyCatalogEntry.objects(unit_id=content_unit.id).only('path')
    unit_files = set([entry.path for entry in entries])
    if all([os.path.exists(f) for f in unit_files]):
        content_unit.downloaded = True
        content_unit.save()


def _get_content_unit(catalog_entry):
    """
    Given a catalog entry, retrieve the content unit associated with it.

    :param catalog_entry: The catalog entry to download content for.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry

    :return: The content unit referenced in the catalog entry.
    :rtype:  pulp.server.db.model.FileContentUnit
    """
    model = plugin_api.get_unit_model_by_id(catalog_entry.unit_type_id)
    if model is None:
        raise ModelNotFound(catalog_entry.unit_type_id)

    return model.objects(id=catalog_entry.unit_id).get()


def _get_streamer_url(catalog_entry):
    """
    Translate a content unit into a URL where the content unit is cached.

    :param catalog_entry: The catalog entry to get the URL for.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry

    :return: The signed streamer URL which corresponds to the content unit.
    :rtype:  str
    """
    scheme = 'https'
    host = pulp_conf.get('lazy', 'redirect_host')
    port = pulp_conf.get('lazy', 'redirect_port')
    path_prefix = pulp_conf.get('lazy', 'redirect_path')
    unsigned_url = ContentView.urljoin(scheme, host, port, path_prefix,
                                       catalog_entry.path, '')
    # Sign the URL for a year to avoid the URL expiring before the task completes
    return str(URL(unsigned_url).sign(URL_SIGNING_KEY, expiration=31536000))


def queue_download_one(catalog_entry):
    """
    Queue task to download the specified catalog entry.

    :param catalog_entry: The catalog entry to queue a download task for.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry
    """
    tags = [
        resource_tag(RESOURCE_CONTENT_UNIT_TYPE, catalog_entry.unit_id),
        action_tag('download')
    ]
    _download_one.apply_async_with_reservation(
        RESOURCE_CONTENT_UNIT_TYPE,
        catalog_entry.unit_id,
        [catalog_entry],
        tags=tags)
