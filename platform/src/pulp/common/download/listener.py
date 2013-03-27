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

import itertools


class DownloadEventListener(object):
    """
    Downloader event listener class for responding to download events.

    The individual methods are used as callbacks at certain points in batch and
    individual download life-cycles.

    Callers are generally expected to sub-class this class in order to implement
    event-based functionality.

    This class is used as a no-op class in the event that no sub-classed event
    listener is provided to a download backend.
    """

    # TODO (jconnor 2013-01-22) add cancel state callbacks

    # individual download events

    def download_started(self, report):
        pass

    def download_progress(self, report):
        pass

    def download_succeeded(self, report):
        pass

    def download_failed(self, report):
        pass


class AggregatingEventListener(DownloadEventListener):
    """
    Event listener class that collects download reports and stores them in
    lists based on the outcome of the download: success or failure.

    NOTE: do to the ability to associate arbitrary data with the reports, using
    this event listener may consumer a lot of memory.

    :ivar succeeded_reports: list of download reports for downloads that succeeded
    :ivar failed_reports: list of download reports for downloads that failed
    :ivar all_reports: iterator over all reports
    """

    def __init__(self):
        self.succeeded_reports = []
        self.failed_reports = []

    @property
    def all_reports(self):
        return itertools.chain(self.succeeded_reports, self.failed_reports)

    def download_succeeded(self, report):
        self.succeeded_reports.append(report)

    def download_failed(self, report):
        self.failed_reports.append(report)
