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

import copy
import shutil

from pulp_puppet.common import constants
from pulp_puppet.common.model import Module

def handle_uploaded_unit(type_id, unit_key, metadata, file_path, conduit):

    if type_id != constants.TYPE_PUPPET_MODULE:
        raise NotImplementedError()

    # Create a module out of the uploaded metadata
    combined = copy.copy(unit_key)
    combined.update(metadata)
    module = Module.from_dict(combined)

    # Create the Pulp unit
    type_id = constants.TYPE_PUPPET_MODULE
    unit_key = module.unit_key()
    unit_metadata = module.unit_metadata()
    relative_path = constants.STORAGE_MODULE_RELATIVE_PATH % module.filename()

    unit = conduit.init_unit(type_id, unit_key, unit_metadata, relative_path)

    # Copy from the upload temporary location into where Pulp wants it to live
    shutil.copy(file_path, unit)

    # Save the unit into the destination repository
    conduit.save_unit(unit)

    