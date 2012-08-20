# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from   datetime import datetime
from   gettext import gettext as _
import logging
import os
import sys
import traceback

from pulp.common.util import encode_unicode
from pulp.plugins.conduits.mixins import UnitAssociationCriteria

from pulp_puppet.common import constants
from pulp_puppet.common.constants import (STATE_FAILED, STATE_NOT_STARTED,
                                          STATE_RUNNING, STATE_SUCCESS, INCOMPLETE_STATES)
from pulp_puppet.common.model import RepositoryMetadata, Module

_LOG = logging.getLogger(__name__)

# -- public classes -----------------------------------------------------------

class PuppetModulePublishRun(object):
    """
    Used to perform a single publish of a puppet repository. This class will
    maintain state relevant to the run and should not be reused across runs.
    """

    def __init__(self, repo, publish_conduit, config, is_cancelled_call):
        self.repo = repo
        self.publish_conduit = publish_conduit
        self.config = config
        self.is_cancelled_call = is_cancelled_call
