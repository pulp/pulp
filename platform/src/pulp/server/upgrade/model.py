# -*- coding: utf-8 -*-
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
class UpgradeStepReport(object):
    """
    Captures the success/failure of an upgrade step and any messages to
    be displayed to the user. Any messages added to this report should be
    i18n'd before being passed in.
    """

    def __init__(self):
        self.success = None
        self.messages = []
        self.warnings = []
        self.errors = []

    def succeeded(self):
        self.success = True

    def failed(self):
        self.success = False

    def message(self, msg):
        self.messages.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)
