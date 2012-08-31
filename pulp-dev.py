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

WARNING_COLOR = '\033[31m'
WARNING_RESET = '\033[0m'

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
    '/etc/pulp/agent/conf.d',
    '/etc/gofer',
    '/etc/gofer/plugins',
    '/etc/pki/pulp',
    '/etc/pki/pulp/consumer',
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
    '/usr/lib/pulp/plugins',
    '/usr/lib/pulp/plugins/distributors',
    '/usr/lib/pulp/plugins/importers',
    '/usr/lib/pulp/plugins/profilers',
    '/usr/lib/pulp/plugins/types',
    '/var/lib/pulp/published',
    '/var/lib/pulp/published/http',
    '/var/lib/pulp/published/https',
    '/var/lib/pulp/uploads',
    '/var/log/pulp',
    '/var/www/.python-eggs', # needed for older versions of mod_wsgi
    '/var/www/pulp_puppet/http/repos',
    '/var/www/pulp_puppet/https/repos',
)

#
# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
# Please keep alphabetized and by subproject

# Standard directories
DIR_ADMIN_EXTENSIONS = '/usr/lib/pulp/admin/extensions/'
DIR_CONSUMER_EXTENSIONS = '/usr/lib/pulp/consumer/extensions/'
DIR_PLUGINS = '/usr/lib/pulp/plugins'

LINKS = (

    # Builtin Admin Extensions
    ('builtins/extensions/admin/pulp_admin_auth', DIR_ADMIN_EXTENSIONS + 'pulp_admin_auth'),
    ('builtins/extensions/admin/pulp_admin_consumer', DIR_ADMIN_EXTENSIONS + 'pulp_admin_consumer'),
    ('builtins/extensions/admin/pulp_event', DIR_ADMIN_EXTENSIONS + 'pulp_event'),
    ('builtins/extensions/admin/pulp_permission', DIR_ADMIN_EXTENSIONS + 'pulp_permission'),
    ('builtins/extensions/admin/pulp_repo', DIR_ADMIN_EXTENSIONS + 'pulp_repo'),
    ('builtins/extensions/admin/pulp_role', DIR_ADMIN_EXTENSIONS + 'pulp_role'),
    ('builtins/extensions/admin/pulp_server_info', DIR_ADMIN_EXTENSIONS + 'pulp_server_info'),
    ('builtins/extensions/admin/pulp_tasks', DIR_ADMIN_EXTENSIONS + 'pulp_tasks'),
    ('builtins/extensions/admin/pulp_upload', DIR_ADMIN_EXTENSIONS + 'pulp_upload'),
    ('builtins/extensions/admin/pulp_user', DIR_ADMIN_EXTENSIONS + 'pulp_user'),

    # Builtin Consumer Extensions
    ('builtins/extensions/consumer/pulp_consumer', DIR_CONSUMER_EXTENSIONS + 'pulp_consumer'),

    # Executables
    ('platform/bin/pulp-admin', '/usr/bin/pulp-admin'),
    ('platform/bin/pulp-consumer', '/usr/bin/pulp-consumer'),
    ('platform/bin/pulp-migrate', '/usr/bin/pulp-migrate'),

    # Server Configuration
    ('platform/etc/bash_completion.d/pulp-admin', '/etc/bash_completion.d/pulp-admin'),
    ('platform/etc/httpd/conf.d/pulp.conf', '/etc/httpd/conf.d/pulp.conf'),
    ('platform/etc/gofer/plugins/pulp.conf', '/etc/gofer/plugins/pulp.conf'),
    ('platform/etc/pki/pulp/ca.key', '/etc/pki/pulp/ca.key'),
    ('platform/etc/pki/pulp/ca.crt', '/etc/pki/pulp/ca.crt'),
    ('platform/etc/pulp/server.conf', '/etc/pulp/server.conf'),
    ('platform/etc/pulp/admin/admin.conf', '/etc/pulp/admin/admin.conf'),
    ('platform/etc/pulp/consumer/consumer.conf', '/etc/pulp/consumer/consumer.conf'),
    ('platform/etc/pulp/logging', '/etc/pulp/logging'),
    ('platform/etc/rc.d/init.d/pulp-server', '/etc/rc.d/init.d/pulp-server'),

    # Server Web Configuration
    ('platform/src/pulp/agent/gofer/pulp.py', '/usr/lib/gofer/plugins/pulp.py'),
    ('platform/srv/pulp/webservices.wsgi', '/srv/pulp/webservices.wsgi'),

    # RPM Support Configuration
    ('rpm-support/etc/httpd/conf.d/pulp_rpm.conf', '/etc/httpd/conf.d/pulp_rpm.conf'),
    ('rpm-support/etc/pulp/repo_auth.conf', '/etc/pulp/repo_auth.conf'),
    ('rpm-support/etc/pulp/agent/conf.d/rpm.conf', '/etc/pulp/agent/conf.d/rpm.conf'),
    ('rpm-support/etc/pulp/agent/conf.d/bind.conf', '/etc/pulp/agent/conf.d/bind.conf'),
    ('rpm-support/etc/pulp/agent/conf.d/linux.conf', '/etc/pulp/agent/conf.d/linux.conf'),
    ('rpm-support/etc/yum/pluginconf.d/pulp-profile-update.conf', '/etc/yum/pluginconf.d/pulp-profile-update.conf'),

    # RPM Support Admin Extensions
    ('rpm-support/extensions/admin/rpm_admin_consumer', DIR_ADMIN_EXTENSIONS + 'rpm_admin_consumer'),
    ('rpm-support/extensions/admin/rpm_repo', DIR_ADMIN_EXTENSIONS + 'rpm_repo'),
    ('rpm-support/extensions/admin/rpm_sync', DIR_ADMIN_EXTENSIONS + 'rpm_sync'),
    ('rpm-support/extensions/admin/rpm_units_copy', DIR_ADMIN_EXTENSIONS + 'rpm_units_copy'),
    ('rpm-support/extensions/admin/rpm_units_remove', DIR_ADMIN_EXTENSIONS + 'rpm_units_remove'),
    ('rpm-support/extensions/admin/rpm_units_search', DIR_ADMIN_EXTENSIONS + 'rpm_units_search'),
    ('rpm-support/extensions/admin/rpm_upload', DIR_ADMIN_EXTENSIONS + 'rpm_upload'),
    ('rpm-support/extensions/admin/rpm_package_group_upload', DIR_ADMIN_EXTENSIONS + 'rpm_package_group_upload'),
    ('rpm-support/extensions/admin/rpm_errata_upload', DIR_ADMIN_EXTENSIONS + 'rpm_errata_upload'),

    # RPM Support Consumer Extensions
    ('rpm-support/extensions/consumer/rpm_consumer', DIR_CONSUMER_EXTENSIONS + 'rpm_consumer'),

    # RPM Support Agent Handlers
    ('rpm-support/handlers/rpm.py', '/usr/lib/pulp/agent/handlers/rpm.py'),
    ('rpm-support/handlers/bind.py', '/usr/lib/pulp/agent/handlers/bind.py'),
    ('rpm-support/handlers/linux.py', '/usr/lib/pulp/agent/handlers/linux.py'),

    # RPM Support Plugins
    ('rpm-support/plugins/types/rpm_support.json', DIR_PLUGINS + '/types/rpm_support.json'),
    ('rpm-support/plugins/importers/yum_importer', DIR_PLUGINS + '/importers/yum_importer'),
    ('rpm-support/plugins/distributors/yum_distributor', DIR_PLUGINS + '/distributors/yum_distributor'),
    ('rpm-support/plugins/distributors/iso_distributor', DIR_PLUGINS + '/distributors/iso_distributor'),
    ('rpm-support/plugins/profilers/rpm_errata_profiler', DIR_PLUGINS + '/profilers/rpm_errata_profiler'),

    # RPM Support Web Configuration
    ('rpm-support/usr/lib/yum-plugins/pulp-profile-update.py', '/usr/lib/yum-plugins/pulp-profile-update.py'),
    ('rpm-support/srv/pulp/repo_auth.wsgi', '/srv/pulp/repo_auth.wsgi'),

    # Citrus Support (all)
    ('citrus-support/etc/httpd/conf.d/pulp_downstream.conf', '/etc/httpd/conf.d/pulp_downstream.conf'),
    ('citrus-support/etc/pulp/agent/conf.d/repository.conf', '/etc/pulp/agent/conf.d/repository.conf'),
    ('citrus-support/extensions/admin/pulp_admin_downstream', DIR_ADMIN_EXTENSIONS + 'pulp_admin_downstream'),
    ('citrus-support/plugins/distributors/pulp_distributor', DIR_PLUGINS + '/distributors/pulp_distributor'),
    ('citrus-support/plugins/importers/pulp_importer', DIR_PLUGINS + '/importers/pulp_importer'),
    ('citrus-support/handlers/repository.py', '/usr/lib/pulp/agent/handlers/repository.py'),

    # Puppet Support Plugins
    ('puppet-support/etc/httpd/conf.d/pulp_puppet.conf', '/etc/httpd/conf.d/pulp_puppet.conf'),
    ('puppet-support/plugins/types/puppet.json', DIR_PLUGINS + '/types/puppet.json'),
    ('puppet-support/plugins/importers/puppet_importer', DIR_PLUGINS + '/importers/puppet_importer'),
    ('puppet-support/plugins/distributors/puppet_distributor', DIR_PLUGINS + '/distributors/puppet_distributor'),

    # Puppet Support Admin Extensions
    ('puppet-support/extensions/admin/puppet_repo', DIR_ADMIN_EXTENSIONS + 'puppet_repo'),

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

def warning(msg):
    print "%s%s%s" % (WARNING_COLOR, msg, WARNING_RESET)

def debug(opts, msg):
    if not opts.debug:
        return
    sys.stderr.write('%s\n' % msg)


def create_dirs(opts):
    for d in DIRS:
        if os.path.exists(d) and os.path.isdir(d):
            debug(opts, 'skipping %s exists' % d)
            continue
        debug(opts, 'creating directory: %s' % d)
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
    warnings = []
    create_dirs(opts)
    currdir = os.path.abspath(os.path.dirname(__file__))
    for src, dst in getlinks():
        warning_msg = create_link(opts, os.path.join(currdir,src), dst)
        if warning_msg:
            warnings.append(warning_msg)

    # Link between pulp and apache
    create_link(opts, '/var/lib/pulp/published', '/var/www/pub')

    # Grant apache write access to the pulp tools log file and pulp
    # packages dir
    os.system('chown -R apache:apache /var/log/pulp')
    os.system('chown -R apache:apache /var/lib/pulp')
    os.system('chown -R apache:apache /var/lib/pulp/published')
    os.system('chown -R apache:apache /var/www/pulp_puppet')

    # Guarantee apache always has write permissions
    os.system('chmod 3775 /var/log/pulp')
    os.system('chmod 3775 /var/www/pub')
    os.system('chmod 3775 /var/lib/pulp')

    # Update for certs
    os.system('chown -R apache:apache /etc/pki/pulp')

    if warnings:
        print "\n***\nPossible problems:  Please read below\n***"
        for w in warnings:
            warning(w)
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


def create_link(opts, src, dst):
    if not os.path.lexists(dst):
        return _create_link(opts, src, dst)

    if not os.path.islink(dst):
        return "[%s] is not a symbolic link as we expected, please adjust if this is not what you intended." % (dst)

    if not os.path.exists(os.readlink(dst)):
        warning('BROKEN LINK: [%s] attempting to delete and fix it to point to %s.' % (dst, src))
        try:
            os.unlink(dst)
            return _create_link(opts, src, dst)
        except:
            msg = "[%s] was a broken symlink, failed to delete and relink to [%s], please fix this manually" % (dst, src)
            return msg

    debug(opts, 'verifying link: %s points to %s' % (dst, src))
    dst_stat = os.stat(dst)
    src_stat = os.stat(src)
    if dst_stat.st_ino != src_stat.st_ino:
        msg = "[%s] is pointing to [%s] which is different than the intended target [%s]" % (dst, os.readlink(dst), src)
        return msg

def _create_link(opts, src, dst):
        debug(opts, 'creating link: %s pointing to %s' % (dst, src))
        try:
            os.symlink(src, dst)
        except OSError, e:
            msg = "Unable to create symlink for [%s] pointing to [%s], received error: <%s>" % (dst, src, e)
            return msg

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
