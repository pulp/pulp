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
import re
import subprocess
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
    '/etc/pulp/server',
    '/etc/pulp/server/plugins.conf.d',
    '/etc/pulp/server/plugins.conf.d/nodes/importer',
    '/etc/pulp/server/plugins.conf.d/nodes/distributor',
    '/etc/pulp/agent',
    '/etc/pulp/agent/conf.d',
    '/etc/pulp/vhosts80',
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
DIR_PLUGINS = '/usr/lib/pulp/plugins'

LINKS = (
    # Server Configuration
    ('agent/etc/gofer/plugins/pulpplugin.conf', '/etc/gofer/plugins/pulpplugin.conf'),
    ('server/etc/pulp/server.conf', '/etc/pulp/server.conf'),
    ('client_admin/etc/pulp/admin/admin.conf', '/etc/pulp/admin/admin.conf'),
    ('client_consumer/etc/pulp/consumer/consumer.conf', '/etc/pulp/consumer/consumer.conf'),
    ('server/etc/pulp/logging', '/etc/pulp/logging'),

    # Server Web Configuration
    ('agent/pulp/agent/gofer/pulpplugin.py', '/usr/lib/gofer/plugins/pulpplugin.py'),
    ('server/srv/pulp/webservices.wsgi', '/srv/pulp/webservices.wsgi'),

    # Pulp Nodes
    ('nodes/common/etc/pulp/nodes.conf', '/etc/pulp/nodes.conf'),
    ('nodes/parent/etc/httpd/conf.d/pulp_nodes.conf', '/etc/httpd/conf.d/pulp_nodes.conf'),
    ('nodes/child/etc/pulp/server/plugins.conf.d/nodes/importer/http.conf',
     '/etc/pulp/server/plugins.conf.d/nodes/importer/http.conf'),
    ('nodes/parent/etc/pulp/server/plugins.conf.d/nodes/distributor/http.conf',
     '/etc/pulp/server/plugins.conf.d/nodes/distributor/http.conf'),
    ('nodes/child/etc/pulp/agent/conf.d/nodes.conf', '/etc/pulp/agent/conf.d/nodes.conf'),
    ('nodes/child/pulp_node/importers/types/nodes.json', DIR_PLUGINS + '/types/node.json'),
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
    
    # Get links for httpd conf files according to apache version, since things
    # changed substantially between apache 2.2 and 2.4.
    apache_22_conf = ('server/etc/httpd/conf.d/pulp_apache_22.conf', '/etc/httpd/conf.d/pulp.conf')
    apache_24_conf = ('server/etc/httpd/conf.d/pulp_apache_24.conf', '/etc/httpd/conf.d/pulp.conf')

    apachectl_output = subprocess.Popen(['apachectl', '-v'], stdout=subprocess.PIPE).communicate()[0]
    search_result = re.search(r'Apache\/([0-9]+)\.([0-9]+)\.([0-9]+)', apachectl_output)
    apache_version = tuple(map(int, search_result.groups()))
    if apache_version >= (2, 4, 0):
        src, dst = apache_24_conf
    else:
        src, dst = apache_22_conf

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

    # Grant apache write access to the pulp tools log file and pulp
    # packages dir
    os.system('chown -R apache:apache /var/log/pulp')
    os.system('chown -R apache:apache /var/lib/pulp')

    # Guarantee apache always has write permissions
    os.system('chmod 3775 /var/log/pulp')
    os.system('chmod 3775 /var/lib/pulp')

    # Generate certificates
    print 'generating certificates'
    os.system(os.path.join(os.curdir, 'server/bin/pulp-gen-ca-certificate'))
    os.system(os.path.join(os.curdir, 'nodes/common/bin/pulp-gen-nodes-certificate'))

    # Update for certs
    os.system('chown -R apache:apache /etc/pki/pulp')
    os.system('chmod 644 /etc/pki/pulp/ca.*')

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

    # Remove generated certificates
    print 'removing certificates'
    os.system('rm -rf /etc/pki/pulp/*')

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
