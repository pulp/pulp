# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from pulp.server import exceptions as pulp_exceptions


def validate_keys(options, valid_keys, all_required=False):
    """
    Validate the keys of a dictionary using the list of valid keys.
    @param options: dictionary of options to validate
    @type options: dict
    @param valid_keys: list of keys that are valid
    @type valid_keys: list or tuple
    @param all_required: flag whether all the keys in valid_keys must be present
    @type all_required: bool
    """
    invalid_keys = []
    for key in options:
        if key not in valid_keys:
            invalid_keys.append(key)
    if invalid_keys:
        raise pulp_exceptions.InvalidValue(invalid_keys)
    if not all_required:
        return
    missing_keys = []
    for key in valid_keys:
        if key not in options:
            missing_keys.append(key)
    if missing_keys:
        raise pulp_exceptions.MissingValue(missing_keys)

