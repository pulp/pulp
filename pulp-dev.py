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
    '/etc/httpd',
    '/etc/httpd/conf.d',
    '/etc/pulp',
    '/etc/gofer',
    '/etc/gofer/plugins',
    '/etc/pki/pulp',
    '/etc/pki/content',
    '/srv',
    '/srv/pulp',
    '/var/lib/pulp',
    '/var/lib/pulp/published',
    '/var/log/pulp',
    '/var/www/.python-eggs', # needed for older versions of mod_wsgi
    '/usr/lib/gofer',
    '/usr/lib/gofer/plugins',
    '/usr/lib/yum-plugins/',
)

#
# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
LINKS = (
    'etc/pulp/pulp.conf',
    'etc/pulp/repo_auth.conf',
    'etc/pulp/client.conf',
    'etc/httpd/conf.d/pulp.conf',
    'etc/pki/pulp/ca.key',
    'etc/pki/pulp/ca.crt',
    'etc/gofer/plugins/pulpplugin.conf',
    'etc/yum/pluginconf.d/pulp-profile-update.conf',
    'etc/rc.d/init.d/pulp-server',
    'srv/pulp/webservices.wsgi',
    ('src/pulp/client/gofer/pulpplugin.py', '/usr/lib/gofer/plugins/pulpplugin.py'),
    ('src/pulp/client/yumplugin/pulp-profile-update.py', '/usr/lib/yum-plugins/pulp-profile-update.py'),
    ('etc/pulp/logging', '/etc/pulp/logging'),
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
                        debug=False)

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
        os.mkdir(d, 0777)


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
        try:
            os.symlink(os.path.join(currdir, src), dst)
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
    os.system('setfacl -m user:apache:rwx /var/log/pulp')
    os.system('setfacl -m user:apache:rwx /var/lib/pulp')
    os.system('setfacl -m user:apache:rwx /var/lib/pulp/published')
    # guarantee apache always has write permissions
    os.system('chmod 3775 /var/log/pulp')
    os.system('chmod 3775 /var/www/pub')
    os.system('chmod 3775 /var/lib/pulp')

    # Disable existing SSL configuration
    #if os.path.exists('/etc/httpd/conf.d/ssl.conf'):
    #    shutil.move('/etc/httpd/conf.d/ssl.conf', '/etc/httpd/conf.d/ssl.off')

    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks():
        debug(opts, 'removing link: %s' % dst)
        if not os.path.exists(dst):
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
