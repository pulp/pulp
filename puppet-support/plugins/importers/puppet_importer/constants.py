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

"""
Contains constants that are global across the entire puppet plugin. Eventually,
this will be pulled into a common dependency across all of the puppet
support plugins (importers, distributors, extensions).
"""

# ID used to refer to the puppet importer
IMPORTER_ID_PUPPET = 'puppet_importer'

# ID of the puppet module type definition (must match what's in puppet.json)
TYPE_PUPPET_MODULE = 'puppet_module'

# Configuratoin key for the directory from which to sync modules
CONFIG_DIR = 'dir'
