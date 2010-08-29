#! /usr/bin/env python
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


from threading import local as Local

class EventFlags(Local):
    """
    Thread (local) event flags.
    """
    def __init__(self):
        """
        @ivar suspended: Outbound is suspended.
        @type suspended: bool
        """
        self.suspended = 0
        
    def suspend(self):
        """
        Suspend outbound events.
        """
        self.suspended = 1
        
    def resume(self):
        """
        Resume outbound events.
        """
        self.suspended = 0
