# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE. You should have received a copy of GPLv2 along with this
# software; if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class Profiler(object):
    """
    Base class for Pulp consumer profilers. Profilers must subclass this class
    in order for Pulp to identify them during plugin discovery.
    """

    # plugin lifecycle ---------------------------------------------------------

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this profiler. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this profiler. Must be unique
               across all profilers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the profiler.
        * types - List of all content type IDs that may be processed using this
                  profiler.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        @return: description of the profiler's capabilities
        @rtype:  dict
        """
        raise NotImplementedError()
