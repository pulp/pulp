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

    def __init__(self, url, destination):
        """
        :param url:         url of the file to be downloaded
        :type  url:         str
        :param destination: specifies where the downloader should store the contents of the URL
                            once they are retrieved. You can provide either a file-system path for
                            this parameter, or an open file-like object. If you provide a file-like
                            object, it is your responsibility to close the file after the download
                            is finished.
        :type  destination: str or file-like object
        """

        self.url         = url
        self.destination = destination
