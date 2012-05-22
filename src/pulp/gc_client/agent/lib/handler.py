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
#
# [types]
# content=(type_id,)
# distributor=(type_id,)
#
# [<type_id>]
# class=<str>
# <other>
#


def abstract(fn):
    """
    Decorator used to mark abstract methods.
    @param fn: A function.
    @type fn: function
    """
    fn.abstract=1


def implemented(method):
    """
    Verify method is callable and implemented
    @return: True if callable and implemented
    @rtype: bool
    """
    try:
        return callable(method) and (not method.im_func.abstract)
    except AttributeError:
        return 1


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

    @abstract
    def install(self, units, options):
        """
        Install content unit(s).
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: An install report.
        @rtype: L{HandlerReport}
        """
        pass

    @abstract
    def update(self, units, options):
        """
        Update content unit(s).
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.
        @rtype: L{HandlerReport}
        """
        pass

    @abstract
    def uninstall(self, units, options):
        """
        Uninstall content unit(s).
        @param units: A list of content unit (keys).
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: An uninstall report.
        @rtype: L{HandlerReport}
        """
        pass

    @abstract
    def profile(self):
        """
        Request the installed content profile be sent
        to the pulp server.
        @return: A profile report.
        @rtype: L{ProfileReport}
        """
        pass

    @abstract
    def reboot(self, options={}):
        """
        Schedule system reboot.
        @param options: Reboot options.
        @type options: dict
        @return: An reboot report.
        @rtype: L{HandlerReport}
        """
        pass

    @abstract
    def bind(self, details):
        """
        Bind a repository.
        @param binds: A list of bind details.
        @type binds: list
        @return: An bind report.
        @rtype: L{BindReport}
        """
        pass

    @abstract
    def rebind(self, details):
        """
        Bind a repository.
        @param binds: A list of bind details.
        @type binds: list
        @return: An rebind report.
        @rtype: L{BindReport}
        """
        pass

    @abstract
    def unbind(self, repoid):
        """
        Unbind a repository.
        @param repoid: The repo ID.
        @type repoid: str
        @return: An inbind report.
        @rtype: L{BindReport}
        """
        pass

    @abstract
    def clean(self):
        """
        Clean up all artifacts.
        @return: An bind report.
        @rtype: L{CleanReport}
        """
        pass
