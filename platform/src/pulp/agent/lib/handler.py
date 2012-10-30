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

"""
Content handler interfaces.
"""

#
# Handler descriptor:
#
# [main]
# enabled=(0|1)
#
# [types]
# system=(type_id,)
# content=(type_id,)
# distributor=(type_id,)
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


class SystemHandler(Handler):
    """
    System (type) handler.
    Defines the interface for handler objects designed
    to implement SYSTEM management requests.
    """

    def reboot(self, conduit, options):
        """
        Schedule system reboot.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param options: Reboot options.
        @type options: dict
        @return: An reboot report.
        @rtype: L{pulp.agent.lib.report.RebootReport}
        """
        raise NotImplementedError()
        
        
class ContentHandler(Handler):
    """
    Content (type) handler.
    Defines the interface for handler objects designed
    to implement CONTENT management requests.
    """

    def install(self, conduit, units, options):
        """
        Install content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: An install report.
        @rtype: L{pulp.agent.lib.report.ContentReport}
        """
        raise NotImplementedError()

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.
        @rtype: L{pulp.agent.lib.report.ContentReport}
        """
        raise NotImplementedError()

    def uninstall(self, conduit, units, options):
        """
        Uninstall content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: An uninstall report.
        @rtype: L{pulp.agent.lib.report.ContentReport}
        """
        raise NotImplementedError()

    def profile(self, conduit):
        """
        Request the installed content profile be sent
        to the pulp server.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @return: A profile report.
        @rtype: L{pulp.agent.lib.report.ProfileReport}
        """
        raise NotImplementedError()


class BindHandler(Handler):
    """
    Bind (type) handler.
    Defines the interface for handler objects designed
    to implement BIND management requests.
    """

    def bind(self, conduit, definitions, options):
        """
        Bind a repository.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param definitions: A list of bind definitions.
            Each definition is:
                {'repository':<repository>, 'details':<details>}
            The <repository> is a pulp repository object.
            The content of <details> is at the discretion of the distributor.
        @type definitions: list
        @param options: Bind options.
        @type options: dict
        @return: An bind report.
        @rtype: L{pulp.agent.lib.report.BindReport}
        """
        raise NotImplementedError()

    def unbind(self, conduit, repo_id, options):
        """
        Unbind a repository.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param repo_id: The repo ID.
        @type repo_id: str
        @param options: Unbind options.
        @type options: dict
        @return: An unbind report.
        @rtype: L{pulp.agent.lib.report.UnbindReport}
        """
        raise NotImplementedError()

    def clean(self, conduit):
        """
        Clean up all bind related artifacts.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @return: An bind report.
        @rtype: L{pulp.agent.lib.report.CleanReport}
        """
        raise NotImplementedError()
