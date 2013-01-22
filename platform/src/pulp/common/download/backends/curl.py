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
import signal

import pycurl

from pulp.common.download import report as download_report
from pulp.common.download.backends.base import DownloadBackend

# default constants ------------------------------------------------------------

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
DEFAULT_NO_SIGNAL = 1

# curl-based http download backend ---------------------------------------------

class HTTPCurlDownloadBackend(DownloadBackend):

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):

        # this list is backwards so we can pop() efficiently and maintain the original order
        request_queue = [(r, download_report.DownloadReport.from_download_request(r))
                         for r in request_list[::-1]]
        request_cache = []

        total_requests = len(request_queue)
        processed_requests = 0

        multi_handle = self._build_multi_handle()
        free_handles = multi_handle.handles[:]

        self.fire_event_to_listener(self.event_listener.batch_started,
                                    [i[1] for i in request_queue[::-1]])
        self._set_signals()

        # main request processing loop
        # TODO add cancellation detection to this loop
        while processed_requests < total_requests:

            # populate max_concurrent downloads into the pycurl multi handle
            while request_queue and free_handles:
                request, report = request_queue.pop()
                request_cache.append((request, report))

                easy_handle = free_handles.pop()
                self._set_easy_handle_download(easy_handle, request, report)
                multi_handle.add_handle(easy_handle)

                easy_handle.report.state = download_report.DOWNLOAD_DOWNLOADING
                easy_handle.report.start_time = datetime.datetime.now()
                self.fire_event_to_listener(self.event_listener.download_started, easy_handle.report)

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
                    self.fire_event_to_listener(self.event_listener.download_succeeded, easy_handle.report)

                    multi_handle.remove_handle(easy_handle)
                    self._clear_easy_handle_download(easy_handle)
                    free_handles.append(easy_handle)

                for easy_handle, err_code, err_msg in err_list:
                    easy_handle.report.finish_time = datetime.datetime.now()

                    easy_handle.report.state = download_report.DOWNLOAD_FAILED
                    response_code = easy_handle.getinfo(pycurl.HTTP_CODE)
                    easy_handle.report.error_report['response_code'] = response_code
                    easy_handle.report.error_report['error_code'] = err_code
                    easy_handle.report.error_report['error_message'] = err_msg
                    self.fire_event_to_listener(self.event_listener.download_failed, easy_handle.report)

                    multi_handle.remove_handle(easy_handle)
                    self._clear_easy_handle_download(easy_handle)
                    free_handles.append(easy_handle)

                processed_requests += (len(ok_list) + len(err_list))

                if num_q == 0:
                    break

        self._clear_signals()
        self.fire_event_to_listener(self.event_listener.batch_finished,
                                    [i[1] for i in request_cache])

    # signal utility methods ---------------------------------------------------

    def _set_signals(self):
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    def _clear_signals(self):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # pycurl handle utility methods --------------------------------------------

    def _build_multi_handle(self):
        multi_handle = pycurl.CurlMulti()

        # XXX I don't think that any of this is actually necessary
        multi_handle.setopt(pycurl.M_MAXCONNECTS, self.max_concurrent)
        multi_handle.setopt(pycurl.M_PIPELINING, DEFAULT_MULTI_PIPELINING)

        # track the easy handle pool here too keep us from loosing references to them
        multi_handle.handles = [self._build_easy_handle() for i in range(self.max_concurrent)]

        return multi_handle

    def _build_easy_handle(self):
        easy_handle = pycurl.Curl()
        easy_handle.request = None
        easy_handle.report = None
        easy_handle.fp = None

        # XXX most of this shit should be configurable
        easy_handle.setopt(pycurl.FOLLOWLOCATION, DEFAULT_FOLLOW_LOCATION)
        easy_handle.setopt(pycurl.MAXREDIRS, DEFAULT_MAX_REDIRECTS)
        easy_handle.setopt(pycurl.CONNECTTIMEOUT, DEFAULT_CONNECT_TIMEOUT)
        easy_handle.setopt(pycurl.TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
        # XXX not sure if I should use this or not
        easy_handle.setopt(pycurl.NOSIGNAL, DEFAULT_NO_SIGNAL)

        # TODO set various options here: authentication/authorization, proxy, etc

        return easy_handle

    def _set_easy_handle_download(self, easy_handle, request, report):
        # store this on the handle so that it's easier to track
        easy_handle.request = request
        easy_handle.report = report
        easy_handle.fp = open(request.file_path, 'wb')

        easy_handle.setopt(pycurl.URL, request.url)
        easy_handle.setopt(pycurl.WRITEDATA, easy_handle.fp)

        progress_functor = CurlDownloadProgressFunctor(report, self.event_listener.download_progress)
        easy_handle.setopt(pycurl.NOPROGRESS, 0)
        easy_handle.setopt(pycurl.PROGRESSFUNCTION, progress_functor)

        return easy_handle

    def _clear_easy_handle_download(self, easy_handle):
        easy_handle.request = None
        easy_handle.report = None

        easy_handle.fp.close() # XXX not sure this belongs here, it's really a side-effect
        easy_handle.fp = None

        return easy_handle

# curl-based https download backend --------------------------------------------

class HTTPSCurlDownloadBackend(HTTPCurlDownloadBackend):

    # TODO override __init__ and __del__ to create and cleanup tmp directories

    def __init__(self, config, event_listener=None):
        super(self.__class__, self).__init__(config, event_listener)

    def __del__(self):
        super(self.__class__, self).__del__()

    def _build_easy_handle(self):
        easy_handle = super(self.__class__, self)._build_easy_handle()

        # TODO add all of the ssl options

        return easy_handle

# download progress callback functor -------------------------------------------

class CurlDownloadProgressFunctor(object):

    def __init__(self, report, progress_callback):
        self.report = report
        self.progress_callback = progress_callback

    def __call__(self, download_t, download_d, upload_t, upload_d):
        self.report.total_bytes = download_t
        self.report.bytes_downloaded = download_d
        self.progress_callback(self.report)

