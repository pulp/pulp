#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import web

from juicer import controllers, runtime


URLS = (
    '/test', controllers.test.application,
    '/auth', controllers.auth.application,
    '/consumers', controllers.consumers.application,
    '/packages', controllers.packages.application,
    '/repositories', controllers.repositories.application,
)



def _configure_application(application):
    # TODO (2010-05-04 jconnor) add configuration file options to application
    pass


def wsgi_application():
    application = web.subdir_application(URLS)
    _configure_application(application)
    return application.wsgifunc()