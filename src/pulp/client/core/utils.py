# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

import os
import sys

# output formatting -----------------------------------------------------------

_header_width = 45
_header_border = '+------------------------------------------+'

def print_header(*lines):
    """
    Print a fancy header to stdout.
    @type lines: list str's
    @param lines: headers, passed in as positional arguments, to be displayed
    """
    padding = 0
    print _header_border
    for line in lines:
        if len(line) < _header_width:
            padding = ((_header_width - len(line)) / 2) - 1
        print ' ' * padding, line
    print _header_border

# system exit -----------------------------------------------------------------

def system_exit(code, msgs=None):
    """
    Exit with a code and optional message(s). Saves a few lines of code.
    @type code: int
    @param code: code to return
    @type msgs: str or list or tuple of str's
    @param msgs: messages to display
    """
    assert msgs is None or isinstance(msgs, (basestring, list, tuple))
    if msgs:
        if isinstance(msgs, basestring):
            msgs = (msgs,)
        if code == os.EX_OK:
            out = sys.stdout
        else:
            out = sys.stderr
        #out = sys.stdout if code == os.EX_OK else sys.stderr
        for msg in msgs:
            print >> out, msg
    sys.exit(code)

