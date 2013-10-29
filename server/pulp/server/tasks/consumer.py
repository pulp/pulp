# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import celery


@celery.task
def bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config):
    pass


@celery.task
def unbind(consumer_id, repo_id, distributor_id, options):
    pass


@celery.task
def force_unbind(consumer_id, repo_id, distributor_id, options):
    pass


@celery.task
def install_content(consumer_id, units, options):
    pass


@celery.task
def update_content(consumer_id, units, options):
    pass


@celery.task
def uninstall_content(consumer_id, units, options):
    pass
