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
import os
import pycurl
import shutil

from base import BaseDownloader
import exceptions
from pulp_puppet.common import constants
from pulp_puppet.importer.config import get_boolean

# -- constants ----------------------------------------------------------------

# Relative to the importer working directory
DOWNLOAD_TMP_DIR = 'http-downloads'

# -- downloader implementations -----------------------------------------------

class HttpDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a remote source over HTTP.
    """

    def retrieve_metadata(self, progress_report):
        """

        :param progress_report: used to communicate the progress of this operation
        :type  progress_report: pulp_puppet.importer.sync.ProgressReport
        @return:
        """
        urls = self._create_metadata_download_urls()

        # Update the
        progress_report.metadata_query_finished_count = 0
        progress_report.metadata_query_total_count = len(urls)

        all_metadata_documents = []
        for url in urls:
            progress_report.metadata_current_query = url
            progress_report.update_progress()

            content = InMemoryDownloadedContent()

            # Let any exceptions from this bubble up, the caller will update
            # the progress report as necessary
            self._download_file(url, content)

            all_metadata_documents.append(content.content)

            progress_report.metadata_query_finished_count += 1

        progress_report.update_progress() # to get the final finished count out there
        return all_metadata_documents

    def retrieve_module(self, progress_report, module, destination):
        pass

    def _create_metadata_download_urls(self):
        """
        Uses the plugin configuration to determine a list of URLs for all
        metadata documents that should be used in the sync.

        :return: list of URLs to be downloaded
        :rtype:  list
        """
        feed = self.config.get(constants.CONFIG_FEED)
        base_url = feed + '/' + constants.REPO_METADATA_FILENAME

        all_urls = []

        queries = self.config.get(constants.CONFIG_QUERIES)
        if queries:
            # I think we can get away with a single URL that contains all of the
            # query strings. The behavior appears to be to OR all of them. In
            # the future this may change to return separate URLs per query if
            # that has better behavior. jdob, Aug 14, 2012

            single_url = copy.copy(base_url)
            single_url += '?'
            for query in queries:

                # The config supports either single queries or tuples of them.
                # If it's a single, wrap it in a list so we can handle them the same
                if not isinstance(query, (list, tuple)):
                    query = [query]

                for query_term in query:
                    single_url += 'q=%s&' % query_term

            # Chop off the last & that was added
            single_url = single_url[:-1]
            all_urls.append(single_url)

        return all_urls

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

        curl.setopt(curl.URL, url)
        curl.setopt(curl.WRITEFUNCTION, destination.update)
        curl.perform()
        status = curl.getinfo(curl.HTTP_CODE)
        curl.close()

        if status == 401:
            raise exceptions.Unauthorized(url)
        elif status == 404:
            raise exceptions.MetadataNotFoundException(url)
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
        # - client SSL certificate
        # - proxy support
        # - callback support for resuming partial downloads

        curl.setopt(curl.VERBOSE, 0)

        # TODO: Add in reference to is cancelled hook to be able to abort the download

        # Close out the connection on our end in the event the remote host
        # stops responding. This is interpretted as "If less than 1000 bytes are
        # sent in a 5 minute interval, abort the connection."
        curl.setopt(curl.LOW_SPEED_LIMIT, 1000)
        curl.setopt(curl.LOW_SPEED_TIME, 5 * 60)

        # If a CA certificate is provided to verify the host, configure it now
        host_ssl_cert = self.config.get(constants.CONFIG_HOST_SSL_CA_CERT)
        if host_ssl_cert:
            curl.setopt(curl.CAINFO, host_ssl_cert)

        # Verification of the host's SSL certificate
        verify_flag = get_boolean(self.config, constants.CONFIG_HOST_VERIFY_SSL)
        if verify_flag:
            curl.setopt(curl.SSL_VERIFYPEER, 1)
        else:
            curl.setopt(curl.SSL_VERIFYPEER, 0)

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

# -- utilities ----------------------------------------------------------------

def _create_download_tmp_dir(repo_working_dir):
    tmp_dir = os.path.join(repo_working_dir, DOWNLOAD_TMP_DIR)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    os.mkdir(tmp_dir)
    return tmp_dir
