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

from pulp.common.download.requests.base import DownloadRequest


class FTPDownloadRequest(DownloadRequest):

    protocol = 'ftp'

    def __init__(self, url, file_path, event_listener=None):
        super(self.__class__, self).__init__(url, file_path, event_listener)

    # request credentials

    def set_user_password_credentials(self):
        pass
