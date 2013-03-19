# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import datetime
import logging
import os
import shutil
import tempfile

import pycurl

from pulp.common.download import report as download_report
from pulp.common.download.downloaders.base import PulpDownloader

# default constants ------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# backend constants
DEFAULT_MAX_CONCURRENT = 5

# multi handle constants
DEFAULT_SELECT_TIMEOUT = 1.0
DEFAULT_MULTI_PIPELINING = 1

# easy handle constants
DEFAULT_FOLLOW_LOCATION = 1
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_REQUEST_TIMEOUT = 300
DEFAULT_NO_PROGRESS = 0

DEFAULT_SSL_VERIFY_PEER = 1
DEFAULT_SSL_VERIFY_HOST = 2

# curl-based http download backend ---------------------------------------------

class HTTPCurlDownloader(PulpDownloader):

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):
        # in case a generator is passed in, cast to a list, which is required by
        # the next statement
        request_list = list(request_list)

        # this list is backwards so we can pop() efficiently and maintain the original order
        request_queue = [(r, download_report.DownloadReport.from_download_request(r))
                         for r in request_list[::-1]]
        request_cache = []

        total_requests = len(request_queue)
        processed_requests = 0

        multi_handle = self._build_multi_handle()
        free_handles = multi_handle.handles[:]

        self.fire_batch_started([i[1] for i in request_queue[::-1]])

        # main request processing loop
        # TODO (jconnor 2013-01-22) add cancellation detection to this loop
        while processed_requests < total_requests:

            try:

                # populate max_concurrent downloads into the pycurl multi handle
                while request_queue and free_handles:
                    request, report = request_queue.pop()
                    request_cache.append((request, report))

                    report.state = download_report.DOWNLOAD_DOWNLOADING
                    report.start_time = datetime.datetime.now()
                    self.fire_download_started(report)

                    easy_handle = free_handles.pop()
                    self._set_easy_handle_download(easy_handle, request, report)
                    multi_handle.add_handle(easy_handle)

                # i/o loop for current set of downloads
                multi_handle.select(DEFAULT_SELECT_TIMEOUT)

                while True:
                    ret, num_handles = multi_handle.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break

                # post-processing loop for current set of downloads
                while True:
                    num_q, ok_list, err_list = multi_handle.info_read()

                    # XXX these loops contain duplicate code; which just pisses me off

                    for easy_handle in ok_list:
                        easy_handle.report.finish_time = datetime.datetime.now()
                        easy_handle.report.state = download_report.DOWNLOAD_SUCCEEDED

                        report = easy_handle.report
                        multi_handle.remove_handle(easy_handle)
                        self._clear_easy_handle_download(easy_handle)
                        free_handles.append(easy_handle)

                        self.fire_download_succeeded(report)

                    for easy_handle, err_code, err_msg in err_list:
                        easy_handle.report.finish_time = datetime.datetime.now()
                        easy_handle.report.state = download_report.DOWNLOAD_FAILED

                        response_code = easy_handle.getinfo(pycurl.HTTP_CODE)
                        easy_handle.report.error_report['response_code'] = response_code
                        easy_handle.report.error_report['error_code'] = err_code
                        easy_handle.report.error_report['error_message'] = err_msg

                        report = easy_handle.report
                        multi_handle.remove_handle(easy_handle)
                        self._clear_easy_handle_download(easy_handle)
                        free_handles.append(easy_handle)

                        self.fire_download_failed(report)

                    processed_requests += (len(ok_list) + len(err_list))

                    if num_q == 0:
                        break

            except Exception, e:
                _LOG.exception(e)
                break

        request_reports = [i[1] for i in request_cache]
        self.fire_batch_finished(request_reports)
        return request_reports

    # pycurl multi handle construction -----------------------------------------

    def _build_multi_handle(self):
        multi_handle = pycurl.CurlMulti()

        multi_handle.setopt(pycurl.M_MAXCONNECTS, self.max_concurrent)
        multi_handle.setopt(pycurl.M_PIPELINING, DEFAULT_MULTI_PIPELINING)

        # track the easy handle pool here too keep us from loosing references to them
        multi_handle.handles = [self._build_easy_handle() for i in range(self.max_concurrent)]

        return multi_handle

    # pycurl easy handle construction ------------------------------------------

    def _build_easy_handle(self):
        easy_handle = pycurl.Curl()
        easy_handle.request = None
        easy_handle.report = None
        easy_handle.fp = None

        self._add_connection_configuration(easy_handle)
        self._add_basic_auth_credentials(easy_handle)

        return easy_handle

    def _add_connection_configuration(self, easy_handle):
        # TODO (jconnor 2013-01-22) make these configurable
        easy_handle.setopt(pycurl.FOLLOWLOCATION, DEFAULT_FOLLOW_LOCATION)
        easy_handle.setopt(pycurl.MAXREDIRS, DEFAULT_MAX_REDIRECTS)
        easy_handle.setopt(pycurl.CONNECTTIMEOUT, DEFAULT_CONNECT_TIMEOUT)
        easy_handle.setopt(pycurl.TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
        easy_handle.setopt(pycurl.NOPROGRESS, DEFAULT_NO_PROGRESS)

    def _add_basic_auth_credentials(self, easy_handle):
        if None in (self.config.basic_auth_username, self.config.basic_auth_password):
            return
        auth_str = ':'.join((self.config.basic_auth_username, self.config.basic_auth_password))
        easy_handle.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
        easy_handle.setopt(pycurl.USERPWD, auth_str)

    # pycurl easy handle download management -----------------------------------

    def _set_easy_handle_download(self, easy_handle, request, report):
        # store this on the handle so that it's easier to track
        easy_handle.request = request
        easy_handle.report = report

        # If the destination is a string, let's interpret it as a filesystem path and open a file
        # there. Otherwise, let's treat destination as an open file-like object
        if isinstance(request.destination, basestring):
            easy_handle.fp = open(request.destination, 'wb')
        else:
            easy_handle.fp = request.destination

        # pycurl complains in un-helpful ways if the url is unicode
        easy_handle.setopt(pycurl.URL, str(request.url))
        easy_handle.setopt(pycurl.WRITEFUNCTION, easy_handle.fp.write)

        progress_functor = CurlDownloadProgressFunctor(report, self.fire_download_progress)
        easy_handle.setopt(pycurl.PROGRESSFUNCTION, progress_functor)

        return easy_handle

    def _clear_easy_handle_download(self, easy_handle):
        # If the request's destination was a string, then the filepointer on the easy_handle was
        # opened by us in _set_easy_handle_download() and we should close it now. Otherwise, we
        # will leave it up to the caller to close their file-like object
        if isinstance(easy_handle.request.destination, basestring):
            easy_handle.fp.close()
        easy_handle.fp = None

        easy_handle.request = None
        easy_handle.report = None

        return easy_handle

# curl-based https download backend --------------------------------------------

class HTTPSCurlDownloader(HTTPCurlDownloader):

    def __init__(self, config, event_listener=None):
        super(self.__class__, self).__init__(config, event_listener)

        prefix = self.__class__.__name__ + '-ssl_working_dir-'
        self.ssl_working_dir = tempfile.mkdtemp(prefix=prefix)

        self.ssl_ca_cert = None
        if config.ssl_ca_cert is not None:
            self.ssl_ca_cert = self._write_tmp_ssl_data(config.ssl_ca_cert, '-ssl_ca_cert.crt')
        elif config.ssl_ca_cert_path is not None:
            self.ssl_ca_cert = config.ssl_ca_cert_path

        self.ssl_client_cert = None
        if config.ssl_client_cert is not None:
            self.ssl_client_cert = self._write_tmp_ssl_data(config.ssl_client_cert, '-ssl_client_cert.crt')
        elif config.ssl_client_cert_path is not None:
            self.ssl_client_cert = config.ssl_client_cert_path

        self.ssl_client_key = None
        if config.ssl_client_key is not None:
            self.ssl_client_key = self._write_tmp_ssl_data(config.ssl_client_key, '-ssl_client_key.key')
        elif config.ssl_client_key_path is not None:
            self.ssl_client_key = config.ssl_client_key_path

    def __del__(self):
        shutil.rmtree(self.ssl_working_dir)

    def _write_tmp_ssl_data(self, data, file_suffix=None):
        if data is None:
            return None
        file_handle, file_path = tempfile.mkstemp(suffix=file_suffix, dir=self.ssl_working_dir)
        os.write(file_handle, data)
        os.close(file_handle)
        return file_path

    # overridden and augmented easy handle construction ------------------------

    def _build_easy_handle(self):
        easy_handle = super(self.__class__, self)._build_easy_handle()

        self._add_ssl_configuration(easy_handle)
        self._add_ssl_ca_cert(easy_handle)
        self._add_ssl_client_cert(easy_handle)
        self._add_ssl_client_key(easy_handle)

        return easy_handle

    def _add_ssl_configuration(self, easy_handle):
        ssl_verify_peer = DEFAULT_SSL_VERIFY_PEER
        if self.config.ssl_verify_peer is not None:
            ssl_verify_peer = self.config.ssl_verify_peer
        easy_handle.setopt(pycurl.SSL_VERIFYPEER, ssl_verify_peer)

        ssl_verify_host = DEFAULT_SSL_VERIFY_HOST
        if self.config.ssl_verify_host is not None:
            ssl_verify_host = self.config.ssl_verify_host
        easy_handle.setopt(pycurl.SSL_VERIFYHOST, ssl_verify_host)

    def _add_ssl_ca_cert(self, easy_handle):
        if self.ssl_ca_cert is None:
            return
        easy_handle.setopt(pycurl.CAINFO, self.ssl_ca_cert)

    def _add_ssl_client_cert(self, easy_handle):
        if self.ssl_client_cert is None:
            return
        easy_handle.setopt(pycurl.SSLCERT, self.ssl_client_cert)

    def _add_ssl_client_key(self, easy_handle):
        if self.ssl_client_key is None:
            return
        easy_handle.setopt(pycurl.SSLKEY, self.ssl_client_key)

# download progress callback functor -------------------------------------------

class CurlDownloadProgressFunctor(object):

    def __init__(self, report, progress_callback):
        self.report = report
        self.progress_callback = progress_callback

    def __call__(self, download_t, download_d, upload_t, upload_d):
        self.report.total_bytes = download_t
        self.report.bytes_downloaded = download_d
        self.progress_callback(self.report)

