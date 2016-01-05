# -*- coding: utf-8 -*-
from gettext import gettext as _
from logging import getLogger
import os
import threading
from urlparse import urlunsplit

import celery
from mongoengine import DoesNotExist
from nectar.config import DownloaderConfig
from nectar.request import DownloadRequest
from nectar.downloaders.threaded import HTTPThreadedDownloader, SkipLocation
from nectar.listener import DownloadEventListener

from pulp.common import error_codes
from pulp.common import tags as pulp_tags
from pulp.common.plugins import reporting_constants
from pulp.common.config import parse_bool, Unparsable
from pulp.plugins.conduits.mixins import (ContentSourcesConduitException,
                                          LazyStatusConduitException, StatusMixin,
                                          PublishReportMixin)
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.util.publish_step import Step
from pulp.plugins.util.verification import (InvalidChecksumType, VerificationException,
                                            verify_checksum)
from pulp.server.async.tasks import Task
from pulp.server.config import config as pulp_conf
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.server.content.sources.container import ContentContainer
from pulp.server.content.sources.constants import MAX_CONCURRENT, HEADERS, SSL_VALIDATION
from pulp.server.content.storage import FileStorage, mkdir
from pulp.server.controllers import repository as repo_controller
from pulp.server.db.model import LazyCatalogEntry, DeferredDownload
from pulp.server.exceptions import PulpCodedTaskException
from pulp.server.lazy import URL, Key
from pulp.server.managers.repo._common import get_working_directory

_logger = getLogger(__name__)

PATH_DOWNLOADED = 'downloaded'
CATALOG_ENTRY = 'catalog_entry'
UNIT_ID = 'unit_id'
TYPE_ID = 'type_id'
UNIT_FILES = 'unit_files'


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

    def get_total(self):
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


def queue_download_deferred():
    """
    Queue a task to download all content units with entries in the DeferredDownload
    collection.
    """
    tags = [pulp_tags.action_tag(pulp_tags.ACTION_DEFERRED_DOWNLOADS_TYPE)]
    download_deferred.apply_async(tags=tags)


def queue_download_repo(repo_id):
    """
    Queue task to download all content units for a given repository
    using the lazy catalog.

    :param repo_id: The ID of repository to download all lazy units for.
    :type  repo_id: str
    """
    tags = [
        pulp_tags.resource_tag(pulp_tags.RESOURCE_REPOSITORY_TYPE, repo_id),
        pulp_tags.action_tag(pulp_tags.ACTION_DOWNLOAD_TYPE)
    ]
    download_repo.apply_async([repo_id], tags=tags)


@celery.task(base=Task)
def download_deferred():
    """
    Downloads all the units with entries in the DeferredDownload collection.
    """
    task_description = _('Download Cached On-Demand Content')
    conduit = LazyStatusConduit(task_description)
    deferred_content_units = _get_deferred_content_units()
    download_requests = _create_download_requests(deferred_content_units)
    download_step = LazyUnitDownloadStep(
        _('on_demand_download'),
        task_description,
        conduit,
        download_requests
    )
    download_step.process_lifecycle()


@celery.task(base=Task)
def download_repo(repo_id):
    """
    Download all content units in the repository that have catalog entries associated
    with them. If a unit is encountered that does not have any catalog entries, it is
    skipped.

    :param repo_id: The ID of the repository to download all lazy units for.
    :type  repo_id: str
    """
    task_description = _('Download Repository Content')
    conduit = LazyStatusConduit(task_description)
    missing_content_units = repo_controller.find_units_not_downloaded(repo_id)
    download_requests = _create_download_requests(missing_content_units)
    download_step = LazyUnitDownloadStep(
        _('background_download'),
        task_description,
        conduit,
        download_requests
    )
    download_step.process_lifecycle()


def _get_deferred_content_units():
    """
    Retrieve a list of units that have been added to the DeferredDownload collection.

    :return: A generator of content units that correspond to DeferredDownload entries.
    :rtype:  generator of pulp.server.db.model.FileContentUnit
    """
    for deferred_download in DeferredDownload.objects.filter():
        try:
            unit_model = plugin_api.get_unit_model_by_id(deferred_download.unit_type_id)
            if unit_model is None:
                _logger.error(_('Unable to find the model object for the {type} type.').format(
                    type=deferred_download.unit_type_id))
            else:
                unit = unit_model.objects.filter(id=deferred_download.unit_id).get()
                yield unit
        except DoesNotExist:
            # This is normal if the content unit in question has been purged during an
            # orphan cleanup.
            _logger.debug(_('Unable to find the {type}:{id} content unit.').format(
                type=deferred_download.unit_type_id, id=deferred_download.unit_id))


def _create_download_requests(content_units):
    """
    Make a list of Nectar DownloadRequests for the given content units using
    the lazy catalog.

    :param content_units: The content units to build a list of DownloadRequests for.
    :type  content_units: list of pulp.server.db.model.FileContentUnit

    :return: A list of DownloadRequests; each request includes a ``data``
             instance variable which is a dict containing the FileContentUnit,
             the list of files in the unit, and the downloaded file's storage
             path.
    :rtype:  list of nectar.request.DownloadRequest
    """
    requests = []
    working_dir = get_working_directory()
    signing_key = Key.load(pulp_conf.get('authentication', 'rsa_key'))

    for content_unit in content_units:
        # All files in the unit; every request for a unit has a reference to this dict.
        unit_files = {}
        unit_working_dir = os.path.join(working_dir, content_unit.id)
        for file_path in content_unit.list_files():
            qs = LazyCatalogEntry.objects.filter(
                unit_id=content_unit.id,
                unit_type_id=content_unit.type_id,
                path=file_path
            )
            catalog_entry = qs.order_by('revision').first()
            signed_url = _get_streamer_url(catalog_entry, signing_key)

            temporary_destination = os.path.join(
                unit_working_dir,
                os.path.basename(catalog_entry.path)
            )
            mkdir(unit_working_dir)
            unit_files[temporary_destination] = {
                CATALOG_ENTRY: catalog_entry,
                PATH_DOWNLOADED: None,
            }

            request = DownloadRequest(signed_url, temporary_destination)
            # For memory reasons, only hold onto the id and type_id so we can reload the unit
            # once it's successfully downloaded.
            request.data = {
                TYPE_ID: content_unit.type_id,
                UNIT_ID: content_unit.id,
                UNIT_FILES: unit_files,
            }
            requests.append(request)

    return requests


def _get_streamer_url(catalog_entry, signing_key):
    """
    Build a URL that can be used to retrieve the file in the catalog entry from
    the lazy streamer.

    :param catalog_entry: The catalog entry to get the URL for.
    :type  catalog_entry: pulp.server.db.model.LazyCatalogEntry
    :param signing_key: The server private RSA key to sign the url with.
    :type  signing_key: M2Crypto.RSA.RSA

    :return: The signed streamer URL which corresponds to the catalog entry.
    :rtype:  str
    """
    try:
        https_retrieval = parse_bool(pulp_conf.get('lazy', 'https_retrieval'))
    except Unparsable:
        raise PulpCodedTaskException(error_codes.PLP1014, section='lazy', key='https_retrieval',
                                     reason=_('The value is not boolean'))
    retrieval_scheme = 'https' if https_retrieval else 'http'
    host = pulp_conf.get('lazy', 'redirect_host')
    port = pulp_conf.get('lazy', 'redirect_port')
    path_prefix = pulp_conf.get('lazy', 'redirect_path')
    netloc = (host + ':' + port) if port else host
    path = os.path.join(path_prefix, catalog_entry.path.lstrip('/'))
    unsigned_url = urlunsplit((retrieval_scheme, netloc, path, None, None))
    # Sign the URL for a year to avoid the URL expiring before the task completes
    return str(URL(unsigned_url).sign(signing_key, expiration=31536000))


class LazyStatusConduit(StatusMixin):
    """
    Used to communicate back into the Pulp server while lazy content units are
    downloaded and imported into permanent storage. Instances of this call should
    *not* be cached between download tasks. Each download task will be issued
    its own conduit instance that is scoped to that run alone.

    Instances of this class are thread-safe. Calls into this instance do not
    have to be coordinated for thread safety, the instance will take care of it itself.
    """

    def __init__(self, report_id):
        """
        :param report_id: identifies the task being performed
        :type  report_id: str
        """
        StatusMixin.__init__(self, report_id, LazyStatusConduitException)

    def __str__(self):
        return 'LazyStatusConduit'


class LazyUnitDownloadStep(Step, DownloadEventListener):
    """
    A Step that downloads all the given requests. The downloader is configured
    to download from the Pulp Streamer components.

    :ivar download_requests: The download requests the step will process.
    :type download_requests: list of nectar.request.DownloadRequest
    :ivar download_config:   The keyword args used to initialize the Nectar
                             downloader configuration.
    :type download_config:   dict
    :ivar downloader:        The Nectar downloader used to fetch the requests.
    :type downloader:        nectar.downloaders.threaded.HTTPThreadedDownloader
    """

    def __init__(self, step_type, step_description, lazy_status_conduit, download_requests):
        """
        Initializes a Step that downloads all the download requests provided.

        :param lazy_status_conduit: Conduit used to update the task status.
        :type  lazy_status_conduit: LazyStatusConduit
        :param download_requests:   List of download requests to process.
        :type  download_requests:   list of nectar.request.DownloadRequest
        """
        super(LazyUnitDownloadStep, self).__init__(
            step_type=step_type,
            status_conduit=lazy_status_conduit,
        )
        self.description = step_description
        self.download_requests = download_requests
        self.download_config = {
            MAX_CONCURRENT: int(pulp_conf.get('lazy', 'download_concurrency')),
            HEADERS: {PULP_STREAM_REQUEST_HEADER: 'true'},
            SSL_VALIDATION: True
        }
        self.downloader = HTTPThreadedDownloader(
            DownloaderConfig(**self.download_config),
            self
        )

    def _process_block(self, item=None):
        """
        This block is called by the `process` loop. This is overridden because
        success and failure is determined during the EventListener callbacks,
        which will handle updating the progress. Since `item` is not used, this
        does not make use of `process_main` and simply calls the downloader.

        Inherited from Step.

        :param item: Unused.
        :type  item: None
        """
        self.downloader.download(self.download_requests)

    def get_total(self):
        """
        The total number of download requests so progress reporting occurs at
        the file level.

        Inherited from Step.

        :return: The number of download requests this step will process.
        :rtype:  int
        """
        return len(self.download_requests)

    def download_started(self, report):
        """
        Checks the filesystem for the file that we are about to download,
        and if it exists, raise an exception which will cause Nectar to
        skip the download.

        Inherited from DownloadEventListener.

        :param report: the report associated with the download request.
        :type  report: nectar.report.DownloadReport

        :raises SkipLocation: if the file is already downloaded and matches
                              the checksum stored in the catalog.
        """
        _logger.debug(_('Starting download of {url}.').format(url=report.url))

        # Remove the deferred entry now that the download has started.
        query_set = DeferredDownload.objects.filter(
            unit_id=report.data[UNIT_ID],
            unit_type_id=report.data[TYPE_ID]
        )
        query_set.delete()

        try:
            # If the file exists and the checksum is valid, don't download it
            path_entry = report.data[UNIT_FILES][report.destination]
            catalog_entry = path_entry[CATALOG_ENTRY]
            self.validate_file(
                catalog_entry.path,
                catalog_entry.checksum_algorithm,
                catalog_entry.checksum
            )
            path_entry[PATH_DOWNLOADED] = True
            self.progress_successes += 1
            self.report_progress()
            msg = _('{path} has already been downloaded.').format(
                path=path_entry[CATALOG_ENTRY].path)
            _logger.debug(msg)
            raise SkipLocation()
        except (InvalidChecksumType, VerificationException, IOError):
            # It's either missing or incorrect, so download it
            pass

    def download_succeeded(self, report):
        """
        Marks the individual file for the unit as downloaded and moves it into
        its final storage location if its checksum value matches the value in
        the catalog entry (if present).

        Inherited from DownloadEventListener.

        :param report: the report associated with the download request.
        :type  report: nectar.report.DownloadReport
        """
        # Reload the content unit
        unit_model = plugin_api.get_unit_model_by_id(report.data[TYPE_ID])
        unit_qs = unit_model.objects.filter(id=report.data[UNIT_ID])
        content_unit = unit_qs.only('_content_type_id', 'id', '_last_updated').get()
        path_entry = report.data[UNIT_FILES][report.destination]

        # Validate the file and update the progress.
        catalog_entry = path_entry[CATALOG_ENTRY]
        try:
            self.validate_file(
                report.destination,
                catalog_entry.checksum_algorithm,
                catalog_entry.checksum
            )

            relative_path = os.path.relpath(
                catalog_entry.path,
                FileStorage.get_path(content_unit)
            )
            if len(report.data[UNIT_FILES]) == 1:
                # If the unit is single-file, update the storage path to point to the file
                content_unit.set_storage_path(relative_path)
                unit_qs.update_one(set___storage_path=content_unit._storage_path)
                content_unit.import_content(report.destination)
            else:
                content_unit.import_content(report.destination, location=relative_path)
            self.progress_successes += 1
            path_entry[PATH_DOWNLOADED] = True
        except (InvalidChecksumType, VerificationException, IOError), e:
            _logger.debug(_('Download of {path} failed: {reason}.').format(
                path=catalog_entry.path, reason=str(e)))
            path_entry[PATH_DOWNLOADED] = False
            self.progress_failures += 1
        self.report_progress()

        # Mark the entire unit as downloaded, if necessary.
        download_flags = [entry[PATH_DOWNLOADED] for entry in
                          report.data[UNIT_FILES].values()]
        if all(download_flags):
            _logger.debug(_('Marking content unit {type}:{id} as downloaded.').format(
                type=content_unit.type_id, id=content_unit.id))
            unit_qs.update_one(set__downloaded=True)

    def download_failed(self, report):
        """
        Marks a file entry as not downloaded.

        Inherited from DownloadEventListener

        :param report: the report associated with the download request.
        :type  report: nectar.report.DownloadReport
        """
        super(LazyUnitDownloadStep, self).download_failed(report)
        path_entry = report.data[UNIT_FILES][report.destination]
        _logger.info('Download of {path} failed: {reason}.'.format(
            path=path_entry[CATALOG_ENTRY].path, reason=report.error_msg))
        path_entry[PATH_DOWNLOADED] = False
        self.progress_failures += 1
        self.report_progress()

    @staticmethod
    def validate_file(file_path, checksum_algorithm, checksum):
        """
        Attempts to validate the checksum of file referenced by the catalog entry. If
        the checksum and checksum algorithm is not available, this method simply checks
        that the file exists.

        :param file_path:          Absolute path to the file to validate.
        :type  file_path:          str
        :param checksum_algorithm: Algorithm used to generate the provided checksum.
        :type  checksum_algorithm: str
        :param checksum:           The expected checksum to verify against.
        :type  checksum:           str

        :raises IOError:               If self.path is not a file.
        :raises InvalidChecksumType:   If the checksum algorithm is not supported by
                                       pulp.plugins.utils.verification.
        :raises VerificationException: If the calculated checksum does not match the
                                       one provided in the report.
        """
        if checksum_algorithm and checksum:
            with open(file_path) as f:
                verify_checksum(f, checksum_algorithm, checksum)
        else:
            if not os.path.isfile(file_path):
                raise IOError(_("The path '{path}' does not exist").format(path=file_path))
