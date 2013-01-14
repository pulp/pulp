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


from pulp.citrus.publisher import join, FilePublisher
from pulp.citrus.manifest import Manifest


class HttpPublisher(FilePublisher):
    """
    The HTTP publisher.
    @ivar repo_id: A repository ID.
    @type repo_id: str
    @ivar virtual_host: The virtual host (base_url, directory)
    @type virtual_host: tuple(2)
    """

    def __init__(self, base_url, virtual_host, repo_id):
        """
        @param base_url: The base URL.
        @type base_url: str
        @param virtual_host: The virtual host (base_url, publish_dir)
        @type virtual_host: tuple(2)
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.base_url = base_url
        self.virtual_host = virtual_host
        FilePublisher.__init__(self, virtual_host[1], repo_id)

    def link(self, units):
        #
        # Add the URL to each unit.
        #
        links = FilePublisher.link(self, units)
        for unit, relative_path in links:
            url = join(self.base_url, self.virtual_host[0], relative_path)
            unit['_download'] = dict(details=dict(url=url))
        return links

    def manifest_path(self):
        """
        Get the relative URL path to the manifest.
        @return: The path component of the URL.
        @rtype: str
        """
        return join(self.virtual_host[0], self.repo_id, Manifest.FILE_NAME)