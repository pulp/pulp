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

import base64
import datetime
import urllib
from logging import getLogger

import eventlet
from eventlet.green import urllib2

from pulp.common.download import report as download_report
from pulp.common.download.downloaders.base import PulpDownloader
from pulp.common.download.downloaders.urllib2_utils import HTTPDownloaderHandler

# -- constants -----------------------------------------------------------------

_LOG = getLogger(__name__)

# "optimal" concurrency, based purely on anecdotal evidence
DEFAULT_MAX_CONCURRENT = 7

# taken from python's socket._fileobject wrapper
DEFAULT_BUFFER_SIZE = 8192 # bytes

DEFAULT_PROGRESS_INTERVAL = 5 # seconds

# -- eventlet downloader -------------------------------------------------------

class HTTPEventletDownloader(PulpDownloader):
    """
    Backend that is optimized for downloading large quantities of files.

    This backend does *not* support the event listener batch callbacks.
    Its download method also returns None instead of a list of reports.
    Both of these deviations keep the backend itself from adding the memory
    overhead.
    """

    @property
    def buffer_size(self):
        return self.config.buffer_size or DEFAULT_BUFFER_SIZE

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    @property
    def progress_interval(self):
        seconds = self.config.progress_interval or DEFAULT_PROGRESS_INTERVAL
        return datetime.timedelta(seconds=seconds)

    def download(self, request_list):

        pool = eventlet.GreenPool(size=self.max_concurrent)

        # main i/o loop
        for report in pool.imap(self._fetch, request_list):
            # event callbacks called here to keep them from gumming up the
            # concurrent fetch calls
            if report.state is download_report.DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)
            else:
                self.fire_download_failed(report)

    def _fetch(self, request):
        report = download_report.DownloadReport.from_download_request(request)
        report.download_started()

        # once we're canceled, short-circuit these calls as there's no way
        # to interrupt the imap call's iterations
        if self.is_canceled:
            report.download_canceled()
            return report

        self.fire_download_started(report)

        # make the request to the server and process the response
        try:
            urllib2_request = download_request_to_urllib2_request(self.config, request)
            urllib2_opener = build_urllib2_opener(self.config)

            response = urllib2_opener.open(urllib2_request)

            if response.code != 200:
                report.error_report['response_code'] = response.code
                report.error_report['response_msg'] = response.msg
                raise urllib2.HTTPError(response.url, response.code, response.msg,
                                        response.headers, response.fp)

            info = response.info()
            set_response_info(info, report)

            buffer_size = self.buffer_size
            progress_interval = self.progress_interval
            file_handle = request.initialize_file_handle()

            self.fire_download_progress(report) # fire an initial progress event
            last_update_time = datetime.datetime.now()

            # individual file download i/o loop
            while not self.is_canceled:
                body = response.read(buffer_size)
                if not body:
                    break

                file_handle.write(body)

                bytes_read = len(body)
                report.bytes_downloaded += bytes_read

                now = datetime.datetime.now()

                if now - last_update_time < progress_interval:
                    continue

                self.fire_download_progress(report)
                last_update_time = now

            else:
                # we didn't break out of the i/o loop only if we were cancelled
                report.download_canceled()

        except Exception, e:
            report.download_failed()
            _LOG.exception(e)

        else:
            report.download_succeeded()

        finally:
            request.finalize_file_handle()

        # return the appropriately filled out report
        return report

# utilities --------------------------------------------------------------------

def set_response_info(info, report):
    content_length = info.dict.get('content-length', None)
    if content_length is not None:
        try:
            report.total_bytes = int(content_length)
        # if we can't convert the content length to an int, leave it as None
        except TypeError:
            pass

# urllib2 opener construction --------------------------------------------------

def build_urllib2_opener(config):

    proxy_scheme = None
    proxy_server = None

    if config.proxy_url is not None:
        proxy_scheme, remainder = urllib.splittype(config.proxy_url)
        proxy_server = urllib.splithost(remainder)[0]

    kwargs = {'key_file': config.ssl_client_key_path,
              'cert_file': config.ssl_client_cert_path,
              'ca_cert_file': config.ssl_ca_cert_path,
              'validate_host': config.ssl_validation if config.ssl_validation is not None else True,
              'proxy_scheme': proxy_scheme,
              'proxy_server': proxy_server,
              'proxy_port': config.proxy_port,
              'proxy_user': config.proxy_user,
              'proxy_password': config.proxy_password,}

    handler = HTTPDownloaderHandler(**kwargs)
    return urllib2.build_opener(handler)

# urllib2 request construction -------------------------------------------------

def download_request_to_urllib2_request(config, download_request):
    urllib2_request = urllib2.Request(download_request.url)
    add_basic_auth_support(config, urllib2_request)
    return urllib2_request


def add_basic_auth_support(config, request):
    if None in (config.basic_auth_username, config.basic_auth_password):
        return

    auth_string = '%s:%s' % (config.basic_auth_username, config.basic_auth_password)
    encoded_auth_string = base64.encodestring(auth_string).replace('\n', '')
    request.add_header('Authorization', 'Basic %s' % encoded_auth_string)


