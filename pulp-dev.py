#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

import optparse
import os
import shutil
import sys

DIRS = (
    '/etc',
    '/etc/bash_completion.d',
    '/etc/httpd',
    '/etc/httpd/conf.d',
    '/etc/pulp',
    '/etc/pulp/admin',
    '/etc/pulp/admin/conf.d',
    '/etc/pulp/consumer',
    '/etc/pulp/consumer/conf.d',
    '/etc/pulp/distributor',
    '/etc/pulp/importer',
    '/etc/pulp/agent',
    '/etc/pulp/agent/handler',
    '/etc/pulp/agent/conf.d',
    '/etc/gofer',
    '/etc/gofer/plugins',
    '/etc/pki/pulp',
    '/etc/pki/pulp/content',
    '/srv',
    '/srv/pulp',
    '/usr/lib/pulp/',
    '/usr/lib/pulp/agent',
    '/usr/lib/pulp/agent/handlers',
    '/usr/lib/pulp/admin',
    '/usr/lib/pulp/admin/extensions',
    '/usr/lib/pulp/consumer',
    '/usr/lib/pulp/consumer/extensions',
    '/usr/lib/gofer',
    '/usr/lib/gofer/plugins',
    '/usr/lib/yum-plugins/',
    '/var/lib/pulp',
    '/var/lib/pulp_client',
    '/var/lib/pulp_client/admin',
    '/var/lib/pulp_client/admin/extensions',
    '/var/lib/pulp_client/consumer',
    '/var/lib/pulp_client/consumer/extensions',
    '/var/lib/pulp/plugins',
    '/var/lib/pulp/plugins/distributors',
    '/var/lib/pulp/plugins/importers',
    '/var/lib/pulp/plugins/profilers',
    '/var/lib/pulp/plugins/types',
    '/var/lib/pulp/published',
    '/var/lib/pulp/published/http',
    '/var/lib/pulp/published/https',
    '/var/lib/pulp/uploads',
    '/var/log/pulp',
    '/var/www/.python-eggs', # needed for older versions of mod_wsgi
)

#
# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
# Please keep alphabetized and by subproject

# Standard directories
DIR_ADMIN_EXTENSIONS = '/usr/lib/pulp/admin/extensions/'
DIR_CONSUMER_EXTENSIONS = '/usr/lib/pulp/consumer/extensions/'

LINKS = (
    ('builtins/extensions/pulp_admin_auth', DIR_ADMIN_EXTENSIONS + 'pulp_admin_auth'),
    ('builtins/extensions/pulp_admin_consumer', DIR_ADMIN_EXTENSIONS + 'pulp_admin_consumer'),
    ('builtins/extensions/pulp_consumer', DIR_CONSUMER_EXTENSIONS + 'pulp_consumer'),
    ('builtins/extensions/pulp_repo', DIR_ADMIN_EXTENSIONS + 'pulp_repo'),
    ('builtins/extensions/pulp_server_info', DIR_ADMIN_EXTENSIONS + 'pulp_server_info'),
    ('builtins/extensions/pulp_tasks', DIR_ADMIN_EXTENSIONS + 'pulp_tasks'),

    ('platform/bin/pulp-admin', '/usr/bin/pulp-admin'),
    ('platform/bin/pulp-consumer', '/usr/bin/pulp-consumer'),
    ('platform/bin/pulp-migrate', '/usr/bin/pulp-migrate'),

    ('platform/etc/bash_completion.d/pulp-admin', '/etc/bash_completion.d/pulp-admin'),
    ('platform/etc/httpd/conf.d/pulp.conf', '/etc/httpd/conf.d/pulp.conf'),
    ('platform/etc/gofer/plugins/pulp.conf', '/etc/gofer/plugins/pulp.conf'),
    ('platform/etc/gofer/plugins/pulpplugin.conf', '/etc/gofer/plugins/pulpplugin.conf'),
    ('platform/etc/gofer/plugins/consumer.conf', '/etc/gofer/plugins/consumer.conf'),
    ('platform/etc/pki/pulp/ca.key', '/etc/pki/pulp/ca.key'),
    ('platform/etc/pki/pulp/ca.crt', '/etc/pki/pulp/ca.crt'),
    ('platform/etc/pulp/server.conf', '/etc/pulp/server.conf'),
    ('platform/etc/pulp/admin/admin.conf', '/etc/pulp/admin/admin.conf'),
    ('platform/etc/pulp/consumer/consumer.conf', '/etc/pulp/consumer/consumer.conf'),
    ('platform/etc/pulp/logging', '/etc/pulp/logging'),
    ('platform/etc/rc.d/init.d/pulp-server', '/etc/rc.d/init.d/pulp-server'),

    ('platform/src/pulp/agent/gofer/pulp.py', '/usr/lib/gofer/plugins/pulp.py'),
    ('platform/srv/pulp/webservices.wsgi', '/srv/pulp/webservices.wsgi'),

    ('rpm-support/etc/httpd/conf.d/pulp_rpm.conf', '/etc/httpd/conf.d/pulp_rpm.conf'),
    ('rpm-support/etc/pulp/repo_auth.conf', '/etc/pulp/repo_auth.conf'),
    ('rpm-support/etc/pulp/agent/handler/rpm.conf', '/etc/pulp/agent/handler/rpm.conf'),
    ('rpm-support/etc/pulp/agent/handler/bind.conf', '/etc/pulp/agent/handler/bind.conf'),
    ('rpm-support/etc/pulp/agent/handler/linux.conf', '/etc/pulp/agent/handler/linux.conf'),
    ('rpm-support/etc/yum/pluginconf.d/pulp-profile-update.conf', '/etc/yum/pluginconf.d/pulp-profile-update.conf'),

    ('rpm-support/extensions/rpm_admin_consumer', DIR_ADMIN_EXTENSIONS + 'rpm_admin_consumer'),
    ('rpm-support/extensions/rpm_repo', DIR_ADMIN_EXTENSIONS + 'rpm_repo'),
    ('rpm-support/extensions/rpm_sync', DIR_ADMIN_EXTENSIONS + 'rpm_sync'),
    ('rpm-support/extensions/rpm_units_copy', DIR_ADMIN_EXTENSIONS + 'rpm_units_copy'),
    ('rpm-support/extensions/rpm_units_search', DIR_ADMIN_EXTENSIONS + 'rpm_units_search'),
    ('rpm-support/extensions/rpm_upload', DIR_ADMIN_EXTENSIONS + 'rpm_upload'),

    ('rpm-support/handlers/rpm.py', '/usr/lib/pulp/agent/handler/rpm.py'),
    ('rpm-support/handlers/bind.py', '/usr/lib/pulp/agent/handler/bind.py'),
    ('rpm-support/handlers/linux.py', '/usr/lib/pulp/agent/handler/linux.py'),

    ('rpm-support/plugins/types/rpm_support.json', '/var/lib/pulp/plugins/types/rpm_support.json'),
    ('rpm-support/plugins/importers/yum_importer', '/var/lib/pulp/plugins/importers/yum_importer'),
    ('rpm-support/plugins/distributors/yum_distributor', '/var/lib/pulp/plugins/distributors/yum_distributor'),

    ('rpm-support/src/pulp/client/consumer/yumplugin/pulp-profile-update.py', '/usr/lib/yum-plugins/pulp-profile-update.py'),
    ('rpm-support/srv/pulp/repo_auth.wsgi', '/srv/pulp/repo_auth.wsgi'),
    )

def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()

    parser.add_option('-I', '--install',
                      action='store_true',
                      help='install pulp development files')
    parser.add_option('-U', '--uninstall',
                      action='store_true',
                      help='uninstall pulp development files')
    parser.add_option('-D', '--debug',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)

    parser.set_defaults(install=False,
                        uninstall=False,
                        debug=True)

    opts, args = parser.parse_args()

    if opts.install and opts.uninstall:
        parser.error('both install and uninstall specified')

    if not (opts.install or opts.uninstall):
        parser.error('neither install or uninstall specified')

    return (opts, args)


def debug(opts, msg):
    if not opts.debug:
        return
    sys.stderr.write('%s\n' % msg)


def create_dirs(opts):
    for d in DIRS:
        debug(opts, 'creating directory: %s' % d)
        if os.path.exists(d) and os.path.isdir(d):
            debug(opts, '%s exists, skipping' % d)
            continue
        os.makedirs(d, 0777)


def getlinks():
    links = []
    for l in LINKS:
        if isinstance(l, (list, tuple)):
            src = l[0]
            dst = l[1]
        else:
            src = l
            dst = os.path.join('/', l)
        links.append((src, dst))
    return links


def install(opts):
    create_dirs(opts)
    currdir = os.path.abspath(os.path.dirname(__file__))
    for src, dst in getlinks():
        debug(opts, 'creating link: %s' % dst)
        target = os.path.join(currdir, src)
        try:
            os.symlink(target, dst)
        except OSError, e:
            if e.errno != 17:
                raise
            debug(opts, '%s exists, skipping' % dst)
            continue

    # Link between pulp and apache
    if not os.path.exists('/var/www/pub'):
        os.symlink('/var/lib/pulp/published', '/var/www/pub')

    # Grant apache write access to the pulp tools log file and pulp
    # packages dir
    os.system('chown -R apache:apache /var/log/pulp')
    os.system('chown -R apache:apache /var/lib/pulp')
    os.system('chown -R apache:apache /var/lib/pulp/published')

    # Guarantee apache always has write permissions
    os.system('chmod 3775 /var/log/pulp')
    os.system('chmod 3775 /var/www/pub')
    os.system('chmod 3775 /var/lib/pulp')
    # Update for certs
    os.system('chown -R apache:apache /etc/pki/pulp')

    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks():
        debug(opts, 'removing link: %s' % dst)
        if not os.path.islink(dst):
            debug(opts, '%s does not exist, skipping' % dst)
            continue
        os.unlink(dst)

    # Link between pulp and apache
    if os.path.exists('/var/www/pub'):
        os.unlink('/var/www/pub')

    # Old link between pulp and apache, make sure it's cleaned up
    if os.path.exists('/var/www/html/pub'):
        os.unlink('/var/www/html/pub')

    return os.EX_OK

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
