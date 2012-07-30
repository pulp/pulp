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
Module for profile serialization.
"""

import link


def consumer(consumer):
    serialized = dict(consumer)
    link.current_link_obj()
    return serialized

def profile(profile):
    serialized = dict(profile)
    href = link.child_link_obj(
        profile['consumer_id'],
        profile['content_type'])
    serialized.update(href)
    return serialized

def applicability_report(report):
    return dict(
        unit=report.unit,
        applicable=report.applicable,
        summary=report.summary,
        details=report.details)
