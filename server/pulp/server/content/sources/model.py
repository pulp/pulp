# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import os
import re

from urlparse import urljoin
from logging import getLogger
from ConfigParser import ConfigParser

from pulp.common.constants import PRIMARY_ID
from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.plugins.loader import api as plugins
from pulp.server.content.sources import constants
from pulp.server.content.sources.descriptor import is_valid, to_seconds, DEFAULT
from pulp.server.managers import factory as managers


log = getLogger(__name__)


# used to split list of paths
PATHS_REGEX = re.compile(r'\s+')

REFRESHING = 'Refreshing [%s] url:%s'
REFRESH_SUCCEEDED = 'Refresh [%s] succeeded.  Added: %d, Deleted: %d'
REFRESH_FAILED = 'Refresh [%s] url: %s, failed: %s'


class Request(object):
    """
    A download request object is used to request the downloading of a
    file associated to a content unit.  The request collaborates with
    the coordinator and the content catalog to perform the download.
    :ivar type_id: The content unit type ID.
    :type type_id: str
    :ivar unit_key: The content unit key.
    :type unit_key: dict
    :ivar url: The URL used to download the unit from the primary source.
    :type url: str
    :ivar destination: The absolute path used to store the downloaded file.
    :type destination: str
    :ivar sources: An iterator of tuple: (ContentSource, url).
    :type sources: iterator
    :ivar index: Used to iterate the list of sources.
    :type index: int
    :ivar errors: The list of download error messages.
    :type errors: list
    :ivar data: User defined data.
    :ivar data: object
    """

    def __init__(self, type_id, unit_key, url, destination):
        """
        :param type_id: The content unit type ID.
        :type type_id: str
        :param unit_key: The content unit key.
        :type unit_key: dict
        :param url: The URL used to download the unit from the primary source.
        :type url: str
        :param destination: The absolute path used to store the downloaded file.
        :type destination: str
        """
        self.type_id = type_id
        self.unit_key = unit_key
        self.url = url
        self.destination = destination
        self.downloaded = False
        self.sources = iter([])
        self.index = 0
        self.errors = []
        self.data = None

    def find_sources(self, primary, alternates):
        """
        Find and set the list of content sources in the order they are to
        be used to satisfy the request.  The alternate sources are
        ordered by priority.  The primary content source is always last.
        :param primary: The primary content source.
        :type primary: ContentSource
        :param alternates: A list of alternative sources.
        :type list of: ContentSource
        """
        resolved = [(primary, self.url)]
        catalog = managers.content_catalog_manager()
        for entry in catalog.find(self.type_id, self.unit_key):
            source_id = entry[constants.SOURCE_ID]
            source = alternates.get(source_id)
            if source is None:
                continue
            url = entry[constants.URL]
            resolved.append((source, url))
        resolved.sort()
        self.sources = iter(resolved)


class ContentSource(object):
    """
    Represents a content source.
    This object is sortable by priority.
    :ivar id: The source ID.
    :type id: str
    :ivar descriptor: The content source descriptor.
        The descriptor defines the content source and its properties.
    :type descriptor: dict
    :cvar CONF_D: The default location for content source descriptors.
    :type CONF_D: str
    """

    CONF_D = '/etc/pulp/content/sources/conf.d/'

    @staticmethod
    def load_all(conf_d=None):
        """
        Load all enabled content sources.
        :param conf_d: The absolute path to a directory containing
            content source descriptor files.
        :type conf_d: str
        :return: Dictionary of: ContentSource keyed by source_id.
        :rtype: dict
        """
        sources = {}
        _dir = conf_d or ContentSource.CONF_D
        for name in os.listdir(_dir):
            path = os.path.join(_dir, name)
            if not os.path.isfile(path):
                continue
            cfg = ConfigParser()
            cfg.read(path)
            for section in cfg.sections():
                descriptor = {}
                descriptor.update(DEFAULT)
                descriptor.update(dict(cfg.items(section)))
                source = ContentSource(section, descriptor)
                if not source.enabled:
                    continue
                if not source.is_valid():
                    continue
                sources[source.id] = source
        return sources

    def __init__(self, source_id, descriptor):
        """
        :param source_id: The source ID.
        :type source_id: str
        :param descriptor: The content source descriptor.
            The descriptor defines the content source and its properties.
        :type descriptor: dict
        """
        self.id = source_id
        self.descriptor = descriptor

    def is_valid(self):
        """
        Get whether the content source has a valid descriptor,
        references a valid cataloger plugin, and can create a nectar downloader.
        :return: True if valid.
        :rtype: bool
        """
        valid = False
        try:
            if is_valid(self.id, self.descriptor):
                self.get_cataloger()
                self.get_downloader()
                valid = True
        except Exception:
            log.exception('source [%s] not valid', self.id)
        return valid

    @property
    def enabled(self):
        """
        Get whether the content source is enabled.
        :return: True if enabled.
        :rtype: bool
        """
        enabled = self.descriptor[constants.ENABLED]
        return enabled.lower() in ('1', 'true', 'yes')

    @property
    def priority(self):
        """
        Get the content source priority (0=lowest)
        Sources are used to download files in priority order.
        :return: The priority.
        :rtype: int
        """
        return int(self.descriptor[constants.PRIORITY])

    @property
    def expires(self):
        """
        Get the duration in seconds of how long content catalog entries
        may exist in the catalog before expiring.  Expired catalog
        entries are ignored and eventually purged.
        :return: The expiration in seconds.
        :rtype int
        """
        return to_seconds(self.descriptor[constants.EXPIRES])

    @property
    def base_url(self):
        """
        Get the base URL used to inspect the content source
        when populating the content catalog.
        :return: The url defined in the descriptor.
        :rtype: str
        """
        return self.descriptor[constants.BASE_URL]

    @property
    def max_concurrent(self):
        """
        Get the download concurrency specified in the source definition.
        :return: The download concurrency.
        :rtype: int
        """
        return int(self.descriptor[constants.MAX_CONCURRENT])

    @property
    def urls(self):
        """
        Get the (optional) list of URLs specified in the descriptor.
        When specified, paths are joined to the base_url.
        :return: A list of urls.
        :rtype: list
        """
        url_list = []
        paths = self.descriptor.get(constants.PATHS)
        if not paths:
            return [self.base_url]
        base = self.base_url
        if not base.endswith('/'):
            base += '/'
        for path in re.split(PATHS_REGEX, paths):
            if path == '\\':
                continue
            if not path.endswith('/'):
                path += '/'
            url = urljoin(base, path.lstrip('/'))
            url_list.append(url)
        return url_list

    def get_conduit(self):
        """
        Get a plugin conduit.
        :return: A plugin conduit.
        :rtype CatalogerConduit
        """
        return CatalogerConduit(self.id, self.expires)

    def get_cataloger(self):
        """
        Get the cataloger plugin.
        :return: A cataloger plugin.
        :rtype: pulp.server.plugins.cataloger.Cataloger
        """
        plugin_id = self.descriptor[constants.TYPE]
        plugin, cfg = plugins.get_cataloger_by_id(plugin_id)
        return plugin

    def get_downloader(self):
        """
        Get a fully configured nectar downloader.
        The returned downloader is configured using properties defined
        in the descriptor.
        :return: A nectar downloader.
        :rtype: nectar.downloaders.Downloader.
        """
        conduit = self.get_conduit()
        plugin = self.get_cataloger()
        return plugin.get_downloader(conduit, self.descriptor, self.base_url)

    def refresh(self, cancel_event):
        """
        Refresh the content catalog using the cataloger plugin as
        defined by the "type" descriptor property.
        :param cancel_event: An event that indicates the refresh has been canceled.
        :type cancel_event: threading.Event
        :return: The list of refresh reports.
        :rtype: list of: RefreshReport
        """
        reports = []
        conduit = self.get_conduit()
        plugin = self.get_cataloger()
        for url in self.urls:
            if cancel_event.isSet():
                break
            conduit.reset()
            report = RefreshReport(self.id, url)
            log.info(REFRESHING, self.id, url)
            try:
                plugin.refresh(conduit, self.descriptor, url)
                log.info(REFRESH_SUCCEEDED, self.id, conduit.added_count, conduit.deleted_count)
                report.succeeded = True
                report.added_count = conduit.added_count
                report.deleted_count = conduit.deleted_count
            except Exception, e:
                log.error(REFRESH_FAILED, self.id, url, e)
                report.errors.append(str(e))
            finally:
                reports.append(report)
        return reports

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        d = {}
        d.update(self.descriptor)
        d[constants.SOURCE_ID] = self.id
        return d

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __gt__(self, other):
        return self.priority > other.priority

    def __lt__(self, other):
        return self.priority < other.priority


class PrimarySource(ContentSource):
    """
    Specialized content source used to ensure ordering and provides
    a wrapper around the primary downloader.
    :ivar downloader: A nectar downloader.
    :type downloader: nectar.downloaders.base.Downloader
    """

    def __init__(self, downloader):
        """
        :param downloader: A nectar downloader.
        :type downloader: nectar.downloaders.base.Downloader
        """
        ContentSource.__init__(self, PRIMARY_ID, {})
        self._downloader = downloader

    @property
    def priority(self):
        """
        Must be last.
        """
        return sys.maxint

    @property
    def max_concurrent(self):
        """
        Get the download concurrency specified in the source definition.
        :return: The download concurrency.
        :rtype: int
        """
        return int(DEFAULT[constants.MAX_CONCURRENT])

    def get_downloader(self):
        """
        Get the wrapped downloader.
        :return: The wrapped (primary) downloader.
        :rtype: nectar.downloaders.base.Downloader.
        """
        return self._downloader

    def refresh(self, cancel_event):
        """
        Does not support refresh.
        """
        pass


class DownloadDetails(object):
    """
    Download details.
    :ivar total_succeeded: The total number of downloads that succeeded.
    :type total_succeeded: int
    :ivar total_failed: The total number of downloads that failed.
    :type total_failed: int
    """

    def __init__(self):
        self.total_succeeded = 0
        self.total_failed = 0

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return self.__dict__


class DownloadReport(object):
    """
    Download report.
    :ivar total_sources: The total number of loaded sources.
    :type total_sources: int
    :ivar downloads: Dict of: DownloadDetails keyed by source ID.
    :type downloads: dict
    """

    def __init__(self):
        self.total_sources = 0
        self.downloads = {}

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(total_sources=self.total_sources,
                    downloads=dict([(k, v.dict()) for k, v in self.downloads.items()]))


class RefreshReport(object):
    """
    Refresh report.
    :ivar source_id: The content source ID.
    :type source_id: str
    :ivar succeeded: Indicates whether the refresh was successful.
    :type succeeded: bool
    :ivar added_count: The number of entries added to the catalog.
    :type added_count: int
    :ivar deleted_count: The number of entries deleted from the catalog.
    :type deleted_count: int
    :ivar errors: The list of errors.
    :type errors: list
    """

    def __init__(self, source_id, url):
        """
        :param source_id: The content source ID.
        :type source_id: str
        :param url: The URL used to refresh.
        :type url: str
        """
        self.source_id = source_id
        self.url = url
        self.succeeded = False
        self.added_count = 0
        self.deleted_count = 0
        self.errors = []

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(source_id=self.source_id, url=self.url, succeeded=self.succeeded,
                    added_count=self.added_count, deleted_count=self.deleted_count,
                    errors=self.errors)
