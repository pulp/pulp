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
from datetime import datetime
from tempfile import mkdtemp

from pulp.common.download.config import DownloaderConfig
from pulp.common.download.downloaders.curl import HTTPCurlDownloader
from pulp.common.download.listener import DownloadEventListener
from pulp.common.download.request import DownloadRequest

import urls as demo_urls
import utils as demo_utils


URLS_MAP = {'abrt': demo_urls.abrt_file_urls,
            'epel': demo_urls.epel_6_file_urls,
            'iso': demo_urls.fedora_18_iso_url}


class DemoEventListener(DownloadEventListener):

    def __init__(self):
        super(self.__class__, self).__init__()

    def batch_started(self, report_list):
        print 'started %d files downloading' % len(report_list)

    def batch_finished(self, report_list):
        print 'finished %d files downloading' % len(report_list)

    def download_started(self, report):
        pass

    def download_progress(self, report):
        pass

    def download_succeeded(self, report):
        pass

    def download_failed(self, report):
        pass


def demo(demo_name):

    downloader_config = DownloaderConfig(max_concurrent=None)
    downloader = HTTPCurlDownloader(downloader_config, DemoEventListener())

    storage_dir = mkdtemp(prefix=demo_name)
    url_list = URLS_MAP[demo_name]()
    request_list = requests_from_urls(storage_dir, url_list)

    print demo_name.upper(), 'Demo'
    print 'downloading %d files to %s' % (len(url_list), storage_dir)
    print '=' * 80

    start_time = datetime.now()

    report_list = downloader.download(request_list)

    run_time = datetime.now() - start_time
    print '%s downloaded %d files: %s' % (demo_name, len(report_list), str(run_time))


def requests_from_urls(storage_dir, url_list):
    return [DownloadRequest(url, os.path.join(storage_dir, demo_utils.file_name_from_url(url)))
            for url in url_list]

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    demo_name = sys.argv[-1] if sys.argv[-1] in URLS_MAP else 'abrt'
    demo(demo_name)
    sys.exit(os.EX_OK)
