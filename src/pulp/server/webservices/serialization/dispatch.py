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


def task_href(call_report):
    if call_report.task_id is None:
        return {}
    return {'_href': '/pulp/api/v2/tasks/%s/' % call_report.task_id}


def job_href(call_report):
    if call_report.job_id is None:
        return {}
    return {'_href': '/pulp/api/v2/jobs/%s/' % call_report.job_id}