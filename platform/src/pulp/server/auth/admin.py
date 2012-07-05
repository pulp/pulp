# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server import config
from pulp.server.auth import authorization

from pulp.server.managers import factory as managers


def ensure_admin():
    """
    This function ensures that there is at least one super user for the system.
    If no super users are found, the default admin user (from the pulp config)
    is looked up or created and added to the super users role.
    """
    super_users = authorization._get_users_belonging_to_role(
        authorization._get_role(authorization.super_user_role))
    if super_users:
        return
    default_login = config.config.get('server', 'default_login')
    user_manager = managers.user_manager()
    admin = user_manager.find_by_login(default_login)
    if admin is None:
        default_password = config.config.get('server', 'default_password')
        admin = user_manager.create_user(login=default_login, password=default_password)
    authorization.add_user_to_role(authorization.super_user_role, default_login)
