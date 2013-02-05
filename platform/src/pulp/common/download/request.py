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


class DownloadRequest(object):
    """
    Representation of a request for a file download.
    """

    def __init__(self, url, file_path):
        """
        :param url: url of the file to be downloaded
        :type url: str
        :param file_path: local path to the downloaded file
        :type file_path: str
        """

        self.url = url
        self.file_path = file_path
