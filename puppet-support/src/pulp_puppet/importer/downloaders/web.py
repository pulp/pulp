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

import copy
import logging
import os
import pycurl

from pulp.common.util import encode_unicode

from   base import BaseDownloader
import exceptions
from   pulp_puppet.common import constants

# -- constants ----------------------------------------------------------------

# Relative to the importer working directory
DOWNLOAD_TMP_DIR = 'http-downloads'

_LOG = logging.getLogger(__name__)

# -- downloader implementations -----------------------------------------------

class HttpDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a remote source over HTTP.
    """

    def retrieve_metadata(self, progress_report):
        """
        Retrieves all metadata documents needed to fulfill the configuration
        set for the repository. The progress report will be updated as the
        downloads take place.

        :param progress_report: used to communicate the progress of this operation
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :return: list of JSON documents describing all modules to import
        :rtype:  list
        """
        urls = self._create_metadata_download_urls()

        # Update the progress report to reflect the number of queries it will take
        progress_report.metadata_query_finished_count = 0
        progress_report.metadata_query_total_count = len(urls)

        all_metadata_documents = []
        for url in urls:
            _LOG.info('Retrieving URL <%s>' % url)
            progress_report.metadata_current_query = url
            progress_report.update_progress()

            # Let any exceptions from this bubble up, the caller will update
            # the progress report as necessary
            content = InMemoryDownloadedContent()
            self._download_file(url, content)
            all_metadata_documents.append(content.content)

            progress_report.metadata_query_finished_count += 1

        progress_report.update_progress() # to get the final finished count out there
        return all_metadata_documents

    def retrieve_module(self, progress_report, module):
        """
        Retrieves the given module and returns where on disk it can be
        found. It is the caller's job to relocate this file to where Pulp
        wants it to live as its final resting place.

        :param progress_report: used if any updates need to be made as the
               download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module: module to download
        :type  module: pulp_puppet.common.model.Module

        :return: full path to the temporary location where the module file is
        :rtype:  str
        """
        url = self._create_module_url(module)

        module_tmp_dir = _create_download_tmp_dir(self.repo.working_dir)
        module_tmp_filename = os.path.join(module_tmp_dir, module.filename())

        content = StoredDownloadedContent(module_tmp_filename)
        content.open()
        try:
            self._download_file(url, content)
            content.close()
        except Exception, e:
            content.close()
            content.delete()
            raise

        return module_tmp_filename

    def cleanup_module(self, module):
        """
        Called once the unit has been copied into Pulp's storage location to
        let the downloader do any post-processing it needs (for instance,
        deleting any temporary copies of the file).

        :param module: module to clean up
        :type  module: pulp_puppet.common.model.Module
        """
        module_tmp_dir = _create_download_tmp_dir(self.repo.working_dir)
        module_tmp_filename = os.path.join(module_tmp_dir, module.filename())
        if os.path.exists(module_tmp_filename):
            os.remove(module_tmp_filename)

    def _create_metadata_download_urls(self):
        """
        Uses the plugin configuration to determine a list of URLs for all
        metadata documents that should be used in the sync.

        :return: list of URLs to be downloaded
        :rtype:  list
        """
        feed = self.config.get(constants.CONFIG_FEED)
        # Puppet forge is sensitive about a double slash, so strip the trailing here
        if feed.endswith('/'):
            feed = feed[:-1]
        base_url = feed + '/' + constants.REPO_METADATA_FILENAME

        all_urls = []

        queries = self.config.get(constants.CONFIG_QUERIES)
        if queries:
            for query in queries:
                query_url = copy.copy(base_url)
                query_url += '?'

                # The config supports either single queries or tuples of them.
                # If it's a single, wrap it in a list so we can handle them the same
                if not isinstance(query, (list, tuple)):
                    query = [query]

                for query_term in query:
                    query_url += 'q=%s&' % query_term

                # Chop off the last & that was added
                query_url = query_url[:-1]
                all_urls.append(query_url)
        else:
            all_urls.append(base_url)

        return all_urls

    def _create_module_url(self, module):
        """
        Generates the URL for a module at the configured source.

        :param module: module instance being downloaded
        :type  module: pulp_puppet.common.model.Module

        :return: full URL to download the module
        :rtype:  str
        """
        url = self.config.get(constants.CONFIG_FEED)
        if not url.endswith('/'):
            url += '/'

        url += constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (module.author[0], module.author)
        url += module.filename()
        return url

    def _download_file(self, url, destination):
        """
        Downloads the content at the given URL into the given destination.
        The object passed into destination must have a method called "update"
        that accepts a single parameter (the buffer that was read).

        :param url: location to download
        :type  url: str

        :param destination: object
        @return:
        """
        curl = self._create_and_configure_curl()
        url = encode_unicode(url) # because of how the config is stored in pulp

        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEFUNCTION, destination.update)
        curl.perform()
        status = curl.getinfo(curl.HTTP_CODE)
        curl.close()

        if status == 401:
            raise exceptions.UnauthorizedException(url)
        elif status == 404:
            raise exceptions.FileNotFoundException(url)
        elif status != 200:
            raise exceptions.FileRetrievalException(url)

    def _create_and_configure_curl(self):
        """
        Instantiates and configures the curl instance. This will drive the
        bulk of the behavior of how the download progresses. The values in
        this call should be tweaked or pulled out as repository-level
        configuration as the download process is enhanced.

        :return: curl instance to use for the download
        :rtype:  pycurl.Curl
        """

        curl = pycurl.Curl()

        # Eventually, add here support for:
        # - callback on bytes downloaded
        # - bandwidth limitations
        # - SSL verification for hosts on SSL
        # - client SSL certificate
        # - proxy support
        # - callback support for resuming partial downloads

        curl.setopt(pycurl.VERBOSE, 0)

        # TODO: Add in reference to is cancelled hook to be able to abort the download

        # Close out the connection on our end in the event the remote host
        # stops responding. This is interpretted as "If less than 1000 bytes are
        # sent in a 5 minute interval, abort the connection."
        curl.setopt(pycurl.LOW_SPEED_LIMIT, 1000)
        curl.setopt(pycurl.LOW_SPEED_TIME, 5 * 60)

        return curl

# -- private classes ----------------------------------------------------------

class InMemoryDownloadedContent(object):
    """
    In memory storage that content will be written to by PyCurl.
    """
    def __init__(self):
        self.content = ''

    def update(self, buffer):
        self.content += buffer

class StoredDownloadedContent(object):
    """
    Stores content on disk as it is retrieved by PyCurl. This currently does
    not support resuming a download and will need to be revisited to add
    that support.
    """
    def __init__(self, filename):
        self.filename = filename

        self.offset = 0
        self.file = None

    def open(self):
        """
        Sets the content object to be able to accept and store data sent to
        its update method.
        """
        self.file = open(self.filename, 'a+')

    def update(self, buffer):
        """
        Callback passed to PyCurl to use to write content as it is read.
        """
        self.file.seek(self.offset)
        self.file.write(buffer)
        self.offset += len(buffer)

    def close(self):
        """
        Closes the underlying file backing this content unit.
        """
        self.file.close()

    def delete(self):
        """
        Deletes the stored file.
        """
        if os.path.exists(self.filename):
            os.remove(self.filename)

# -- utilities ----------------------------------------------------------------

def _create_download_tmp_dir(repo_working_dir):
    tmp_dir = os.path.join(repo_working_dir, DOWNLOAD_TMP_DIR)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    return tmp_dir
