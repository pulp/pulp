# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class Cataloger(object):
    """
    Catalog content provided by content sources.
    """

    def get_downloader(self, conduit, config, url):
        """
        Get an object suitable for downloading content contributed
        in the catalog by this cataloger.
        :param conduit: Access to pulp platform API.
        :type conduit: pulp.server.plugins.conduits.cataloger.CatalogerConduit
        :param config: The content source configuration.
        :type config: dict
        :param url: The URL for the content source.
        :type url: str
        :return: A configured downloader.
        :rtype: nectar.downloaders.base.Downloader
        """
        raise NotImplementedError()

    def refresh(self, conduit, config, url):
        """
        Refresh the content catalog.
        :param conduit: Access to pulp platform API.
        :type conduit: pulp.server.plugins.conduits.cataloger.CatalogerConduit
        :param config: The content source configuration.
        :type config: dict
        :param url: The URL for the content source.
        :type url: str
        """
        raise NotImplementedError()
