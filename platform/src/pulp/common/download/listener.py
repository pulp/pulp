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


class DownloadEventListener(object):
    """
    Downloader event listener class for responding to download events.

    The individual methods are used as callbacks at certain points in batch and
    individual download life-cycles.

    Callers are generally expected to sub-class this class in order to implement
    event-based functionality.

    This class is used as a stub class in the event that no sub-classed event
    listener is provided to a download backend.
    """

    # TODO (jconnor 2013-01-22) add cancel state callbacks

    # batch downloads events

    def batch_started(self, report_list):
        pass

    def batch_finished(self, report_list):
        pass

    # individual download events

    def download_started(self, report):
        pass

    def download_progress(self, report):
        pass

    def download_succeeded(self, report):
        pass

    def download_failed(self, report):
        pass


