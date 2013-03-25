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

import os
import sys
import tempfile

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.downloaders.curl import HTTPCurlDownloader
from pulp.common.download.listener import DownloadEventListener
from pulp.common.download.request import DownloadRequest

import urls


TESTS = {
    'abrt': urls.abrt_file_urls,
    'epel': urls.epel_6_file_urls,
    'iso': urls.fedora_18_iso_url,
}


class TestDownloadEventListener(DownloadEventListener):

    def batch_started(self, report_list):
        print 'Yay! started downloading %d files' % len(report_list)

    def batch_finished(self, report_list):
        print 'Yay! finished downloading %d files' % len(report_list)

    def download_started(self, report):
        print 'Downloading %s to %s' % (report.url, report.file_path)

    def download_progress(self, report):
        print '\tdownloaded %d of %d bytes' % (report.bytes_downloaded, report.total_bytes)

    def download_succeeded(self, report):
        print 'SUCCEEDED: %s' % report.file_path

    def download_failed(self, report):
        print 'FAILED: %s' % report.file_path


def _get_test_names():
    available_tests = set(TESTS.keys())
    requested_tests = set(sys.argv[1:]) or available_tests.copy()
    return available_tests.intersection(requested_tests)


def _filename_from_url(url):
    return url.rsplit('/', 1)[1]


def main():
    test_names = _get_test_names()

    for name in test_names:
        url_list = TESTS[name]()

        print '%s: download %d files from %s' % (name.upper(), len(url_list), url_list[0].rsplit('/', 1)[0])

        config = DownloaderConfig()
        download_dir = tempfile.mkdtemp(prefix=name+'-')
        request_list = [DownloadRequest(url, os.path.join(download_dir, _filename_from_url(url))) for url in url_list]

        downloader = HTTPCurlDownloader(config, TestDownloadEventListener())
        downloader.download(request_list)

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
