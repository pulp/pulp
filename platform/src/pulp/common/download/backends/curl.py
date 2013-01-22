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
import itertools
import signal

import pycurl

from pulp.common.download.backends.base import DownloadBackend
from pulp.common.download.report import DownloadReport


SELECT_TIMEOUT = 1.0


class HTTPCurlDownloadBackend(DownloadBackend):

    def download(self, request_list):

        multi_handle = pycurl.CurlMulti()

        requests = []
        files = []

        for request in request_list:

            file_handle = open(request.file_path, 'wb')

            files.append(request.file_path)

            easy_handle = pycurl.Curl()
            easy_handle.setopt(pycurl.URL, request.url)
            easy_handle.setopt(pycurl.WRITEFUNCTION, file_handle.write)

            req = (request.url, file_handle, easy_handle)
            multi_handle.add_handle(req[2])
            requests.append(req)

        num_handles = len(requests)

        while num_handles:
            ret = multi_handle.select(SELECT_TIMEOUT)
            if ret == -1:
                continue
            while True:
                ret, num_handles = multi_handle.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

        for req in requests:
            req[1].close()

        return files

    def download_prime(self, request_list):

        request_queue = [(r, DownloadReport.from_download_request(r))
                         for r in request_list[::-1]]

        total_requests = len(request_queue)
        processed_requests = 0

        multi_handle = self._build_multi_handle()
        free_handles = multi_handle.handles[:]

        self.event_listener.batch_started(i[1] for i in request_queue)
        self._set_signals()

        while processed_requests < total_requests:

            while request_queue and free_handles:
                request, report = request_queue.pop()
                easy_handle = free_handles.pop()

                self._set_easy_handle_download(easy_handle, request, report)
                multi_handle.add_handle(easy_handle)

                report.start_time = datetime.datetime.now()
                self.event_listener.download_started(report)

            while True:
                ret, num_handles = multi_handle.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

            while True:
                num_q, ok_list, err_list = multi_handle.info_read()

                for easy_handle in itertools.chain(ok_list, err_list):
                    easy_handle.report.finish_time = datetime.datetime.now()

                    if easy_handle in ok_list:
                        self.event_listener.download_succeeded(easy_handle.report)
                    else: # in err_list
                        self.event_listener.download_failed(easy_handle.report)

                    self._clear_easy_handle_download(easy_handle)
                    free_handles.append(easy_handle)

                processed_requests += (len(ok_list) + len(err_list))

                if num_q == 0:
                    break

            multi_handle.select(SELECT_TIMEOUT)

        self._clear_signals()
        self.event_listener.batch_finished(i[1] for i in request_queue)

    # signal utility methods ---------------------------------------------------

    def _set_signals(self):
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    def _clear_signals(self):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # pycurl handle utility methods --------------------------------------------

    def _build_multi_handle(self):
        multi_handle = pycurl.CurlMulti()
        if self.max_concurrent is not None:
            multi_handle.setopt(pycurl.M_MAXCONNECTS, self.max_concurrent)
        multi_handle.setopt(pycurl.M_PIPELINING, 1)
        multi_handle.handles = [self._build_easy_handle() for i in range(self.max_concurrent)]
        return multi_handle

    def _build_easy_handle(self):
        easy_handle = pycurl.Curl()
        easy_handle.request = None
        easy_handle.report = None
        easy_handle.fp = None

        # XXX most of this shit should be configurable
        easy_handle.setopt(pycurl.FOLLOWLOCATION, 1)
        easy_handle.setopt(pycurl.MAXREDIRS, 5)
        easy_handle.setopt(pycurl.CONNECTTIMEOUT, 30)
        easy_handle.setopt(pycurl.TIMEOUT, 300)
        # XXX not sure if I should use this or not
        easy_handle.setopt(pycurl.NOSIGNAL, 1)

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
        easy_handle.fp.close()
        easy_handle.fp = None
        return easy_handle


class CurlDownloadProgressFunctor(object):

    def __init__(self, report, progress_callback):
        self.report = report
        self.progress_callback = progress_callback

    def __call__(self, download_t, download_d, upload_t, upload_d):
        if self.report.file_size is None:
            self.report.file_size = download_t
        self.report.bytes_downloaded = download_d
        self.progress_callback(self.report)

