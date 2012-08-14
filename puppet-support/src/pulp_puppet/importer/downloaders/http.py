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

import pycurl

from base import BaseDownloader

# -- constants ----------------------------------------------------------------

# Relative to the importer working directory
DOWNLOAD_TMP_DIR = 'http-downloads'

# -- downloader implementations -----------------------------------------------

class HttpDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a remote source over HTTP.
    """

    def retrieve_metadata(self, progress_report):
        pass

    def retrieve_module(self, progress_report, module, destination):
        pass


class HttpsDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a remote source over HTTPS.
    """

    # To be implemented when support for this is required
    pass

# -----------------------------------------------------------------------------

def create_download_tmp_dir():
