#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

from pmf.envelope import Envelope


class Mode(Envelope):
    """
    Represents RMI modes.
    @ivar synchronous: Indicates synchronous RMI.
    @type synchronous: bool
    @ivar group: The asynchronous reply group.
        None = No, reply.
    @type group: str
    """

    def __init__(self, synchronous=True, group=None):
        """
        @ivar synchronous: Indicates synchronous RMI.
        @type synchronous: bool
        @ivar group: The asynchronous reply group.
            None = No, reply.
        @type group: str
        """
        self.synchronous = synchronous
        self.group = group
