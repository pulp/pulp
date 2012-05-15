#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

#
# Handler descriptor:
#
# [main]
# enabled=(0|1)
# types=(type_id,)
#
# [<type_id>]
# class=<str>
# <other>
#

class Handler:
    """
    Content (type) handler.
    """

    def __init__(self, cfg):
        """
        @param cfg: The handler configuration
        @type cfg: dict
        """
        self.cfg = cfg

    def install(self, units, options):
        """
        Install content unit(s).
        @param units: A list of content units.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: An install report.
        @rtype: L{HandlerReport}
        """
        pass

    def update(self, units, options):
        """
        Update content unit(s).
        @param units: A list of content units.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.
        @rtype: L{HandlerReport}
        """
        pass

    def uninstall(self, units, options):
        """
        Uninstall content unit(s).
        @param units: A list of content units.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: An uninstall report.
        @rtype: L{HandlerReport}
        """
        pass

    def profile(self, types):
        """
        Request the installed content profile be sent
        to the pulp server.
        @param types: A list of content type IDs.
        @type types: list
        """
        pass

    def reboot(self, minutes=1):
        """
        Schedule system reboot.
        @param minutes: Delay in minutes.
        @type minutes: int
        """
        pass
