# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Generic transport classes.
"""


class Transport:

    def download(self, requests):
        """
        Process the specified download requests.
        @param requests: A list of L{DownloadRequest} objects.
        @type requests: list
        @return: The list of downloaded units.
            Each unit is: L{pulp.plugins.model.Unit}
        @rtype: list
        """
        pass


class DownloadRequest:
    """
    The download request provides integration between the importer
    and the transport layer.  It's used to request the download of
    the file referenced by a content unit.
    @ivar importer: The importer making the request.
    @type importer: L{Importer}
    @ivar unit: The upstream content unit.
    @type unit: dict
    @ivar local_unit: A local content unit that is in the process of
        being added.  The request is to download the file referenced
        in the unit.
    @type local_unit: L{Unit}
    """

    def __init__(self, importer, unit, local_unit):
        """
        @param importer: The importer making the request.
        @type importer: L{Importer}
        @param unit: The upstream content unit.
        @type unit: dict
        @param local_unit: A local content unit that is in the process of
            being added.  The request is to download the file referenced
            in the unit.
        @type local_unit: L{Unit}
        """
        self.importer = importer
        self.unit = unit
        self.local_unit = local_unit

    def protocol(self):
        """
        Get the protocol specified by the upstream unit to be used for
        the download.  A value of 'None' indicates that there is no file
        to be downloaded.
        @return: The protocol name.
        @rtype: str
        """
        download = self.unit.get('_download')
        if download:
            return download.get('protocol')

    def details(self):
        """
        Get the details specified by the upstream unit to be used for
        the download.  A value of 'None' indicates that there is no file
        to be downloaded.  Contains information such as URL for http transports.
        @return: The download specification.
        @rtype: dict
        """
        download = self.unit.get('_download')
        if download:
            return download.get('details')

    def succeeded(self):
        """
        Called by the transport to indicate the requested download succeeded.
        """
        self.importer._add_unit(self.local_unit)

    def failed(self, exception):
        """
        Called by the transport to indicate the requested download failed.
        @param exception: The exception raised.
        @type exception: Exception
        """
        log.exception('download failed: %s', self.details())