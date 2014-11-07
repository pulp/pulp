#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse
import os
import re
import shutil
import subprocess
import sys


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# In order to import pulp.devel.environment, we will need to add pulp.devel to the syspath
sys.path.append(os.path.join(ROOT_DIR, 'devel', 'pulp', 'devel'))
import environment


DIRS = [
    '/etc',
    '/etc/bash_completion.d',
    '/etc/gofer',
    '/etc/gofer/plugins',
    '/etc/pki/pulp',
    '/etc/pki/pulp/consumer/server',
    '/etc/pulp',
    '/etc/pulp/admin',
    '/etc/pulp/admin/conf.d',
    '/etc/pulp/agent',
    '/etc/pulp/agent/conf.d',
    '/etc/pulp/consumer',
    '/etc/pulp/consumer/conf.d',
    '/usr/lib/gofer',
    '/usr/lib/gofer/plugins',
    '/usr/lib/pulp/',
    '/usr/lib/pulp/agent',
    '/usr/lib/pulp/agent/handlers',
    '/usr/lib/pulp/consumer',
    '/usr/lib/pulp/consumer/extensions',
    '/usr/lib/yum-plugins/',
    '/var/lib/pulp',
    '/var/lib/pulp_client',
    '/var/lib/pulp_client/admin',
    '/var/lib/pulp_client/admin/extensions',
    '/var/lib/pulp_client/consumer',
    '/var/lib/pulp_client/consumer/extensions',
]

# We only support Python >= 2.6 for the server code
if sys.version_info >= (2, 6):
    DIRS.extend([
        '/etc/httpd',
        '/etc/httpd/conf.d',
        '/etc/pki/pulp/content',
        '/etc/pulp/content/sources/conf.d',
        '/etc/pulp/server',
        '/etc/pulp/server/plugins.conf.d',
        '/etc/pulp/server/plugins.conf.d/nodes/importer',
        '/etc/pulp/server/plugins.conf.d/nodes/distributor',
        '/etc/pulp/vhosts80',
        '/srv',
        '/srv/pulp',
        '/usr/lib/pulp/admin',
        '/usr/lib/pulp/admin/extensions',
        '/usr/lib/pulp/plugins',
        '/usr/lib/pulp/plugins/types',
        '/var/lib/pulp/celery',
        '/var/lib/pulp/nodes/published',
        '/var/lib/pulp/published',
        '/var/lib/pulp/static',
        '/var/lib/pulp/uploads',
        '/var/log/pulp',
        '/var/www/pulp',
        '/var/www/.python-eggs',  # needed for older versions of mod_wsgi
    ])

# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
# Please keep alphabetized and by subproject

# Standard directories
DIR_ADMIN_EXTENSIONS = '/usr/lib/pulp/admin/extensions/'
DIR_CONSUMER_EXTENSIONS = '/usr/lib/pulp/consumer/extensions/'
DIR_PLUGINS = '/usr/lib/pulp/plugins'

LINKS = [
    # Consumer Configuration
    ('agent/etc/gofer/plugins/pulpplugin.conf', '/etc/gofer/plugins/pulpplugin.conf'),
    ('agent/pulp/agent/gofer/pulpplugin.py', '/usr/lib/gofer/plugins/pulpplugin.py'),
]

# We only support Python >= 2.6 for the server code
if sys.version_info >= (2, 6):
    LINKS.extend([
        # Server Web Configuration
        ('server/srv/pulp/webservices.wsgi', '/srv/pulp/webservices.wsgi'),

        # Pulp Nodes
        ('/var/lib/pulp/nodes/published', '/var/www/pulp/nodes'),
        ('nodes/parent/etc/httpd/conf.d/pulp_nodes.conf', '/etc/httpd/conf.d/pulp_nodes.conf'),
        ('nodes/child/etc/pulp/server/plugins.conf.d/nodes/importer/http.conf',
         '/etc/pulp/server/plugins.conf.d/nodes/importer/http.conf'),
        ('nodes/parent/etc/pulp/server/plugins.conf.d/nodes/distributor/http.conf',
         '/etc/pulp/server/plugins.conf.d/nodes/distributor/http.conf'),
        ('nodes/child/etc/pulp/agent/conf.d/nodes.conf', '/etc/pulp/agent/conf.d/nodes.conf'),
        ('nodes/child/pulp_node/importers/types/nodes.json', DIR_PLUGINS + '/types/node.json'),

        # Static Content
        ('/etc/pki/pulp/rsa_pub.key', '/var/lib/pulp/static/rsa_pub.key'),
    ])


try:
    LSB_VENDOR = subprocess.Popen(['lsb_release', '-si'],
                                  stdout=subprocess.PIPE).communicate()[0].strip()
except OSError:
    print ('pulp-dev requires lsb_release to detect which operating system you are using. Please '
           'install it and try again. For Red Hat based distributions, the package is called '
           'redhat-lsb-core.')
    sys.exit(1)
# RedHatEnterpriseEverything is what the EL Beta seems to use, or at least the installation rbarlow
# performed. Perhaps we need a better matching algorithm than just a list of strings.
if LSB_VENDOR not in ('CentOS', 'Fedora', 'RedHatEnterpriseEverything', 'RedHatEnterpriseServer'):
    print 'Your Linux vendor is not supported by this script: %s' % LSB_VENDOR
    sys.exit(1)
LSB_VERSION = float(subprocess.Popen(['lsb_release', '-sr'],
                    stdout=subprocess.PIPE).communicate()[0])


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

    return opts, args


def create_dirs(opts):
    for d in DIRS:
        if os.path.exists(d) and os.path.isdir(d):
            environment.debug(opts, 'skipping %s exists' % d)
            continue
        environment.debug(opts, 'creating directory: %s' % d)
        os.makedirs(d, 0777)


def get_paths_to_copy():
    """
    Return a list of dictionaries. Each dictionary contains source, destination, owner, group, mode,
    and overwrite keys. These indicate a source path that should be copied to the given destination,
    and the owner, group, and mode that should be applied to the destination. The overwrite key
    indicates whether the destination should be overwritten if it already exists when copying the
    files to the destination, as well as whether the destination path should be removed when this
    script is called with the uninstall flag.

    :return: List of dictionaries describing copy operations that should be performed.
    :rtype:  list
    """
    paths = [
        {'source': 'client_admin/etc/bash_completion.d/pulp-admin',
         'destination': '/etc/bash_completion.d/pulp-admin', 'owner': 'root', 'group': 'root',
         'mode': '644', 'overwrite': True},
        {'source': 'client_consumer/etc/bash_completion.d/pulp-consumer',
         'destination': '/etc/bash_completion.d/pulp-consumer', 'owner': 'root', 'group': 'root',
         'mode': '644', 'overwrite': True},
        {'source': 'client_consumer/etc/pulp/consumer/consumer.conf',
         'destination': '/etc/pulp/consumer/consumer.conf', 'owner': 'root', 'group': 'root',
         'mode': '644', 'overwrite': False},
    ]
    # We don't support server or pulp-admin code on EL 5.
    if LSB_VERSION >= 6.0:
        paths.extend([
            {'source': 'client_admin/etc/pulp/admin/admin.conf',
             'destination': '/etc/pulp/admin/admin.conf',
             'owner': 'root', 'group': 'root', 'mode': '644', 'overwrite': False},
            # This should really be 640, but the unit tests require the ability to read it. They
            # should mock instead, but until they do we need to keep this world readable
            {'source': 'nodes/common/etc/pulp/nodes.conf', 'destination': '/etc/pulp/nodes.conf',
             'owner': 'root', 'group': 'apache', 'mode': '644', 'overwrite': False},
            # This really should be 640 since that's how the RPM installs it, but the unit tests try
            # to read the settings rather than mocking them. Once we've fixed that, we should fix
            # this to be the same as the spec file.
            {'source': 'server/etc/pulp/server.conf', 'destination': '/etc/pulp/server.conf',
             'owner': 'root', 'group': 'apache', 'mode': '644', 'overwrite': False},
        ])
    if LSB_VERSION >= 6.0 and LSB_VERSION < 7.0:
        paths.append({'source': 'server/etc/default/upstart_pulp_celerybeat',
                      'destination': '/etc/default/pulp_celerybeat', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
        paths.append({'source': 'server/etc/default/upstart_pulp_workers',
                      'destination': '/etc/default/pulp_workers', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
        paths.append({'source': 'server/etc/default/upstart_pulp_resource_manager',
                      'destination': '/etc/default/pulp_resource_manager', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
    elif LSB_VERSION >= 7.0:
        paths.append({'source': 'server/etc/default/systemd_pulp_celerybeat',
                      'destination': '/etc/default/pulp_celerybeat', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
        paths.append({'source': 'server/etc/default/systemd_pulp_workers',
                      'destination': '/etc/default/pulp_workers', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
        paths.append({'source': 'server/etc/default/systemd_pulp_resource_manager',
                      'destination': '/etc/default/pulp_resource_manager', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': False})
        paths.append({'source': 'server/usr/lib/systemd/system/pulp_celerybeat.service',
                      'destination': '/etc/systemd/system/pulp_celerybeat.service', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': True})
        paths.append({'source': 'server/usr/lib/systemd/system/pulp_resource_manager.service',
                      'destination': '/etc/systemd/system/pulp_resource_manager.service',
                      'owner': 'root', 'group': 'root', 'mode': '644', 'overwrite': True})
        paths.append({'source': 'server/usr/lib/systemd/system/pulp_workers.service',
                      'destination': '/etc/systemd/system/pulp_workers.service', 'owner': 'root',
                      'group': 'root', 'mode': '644', 'overwrite': True})

    for path in paths:
        path['source'] = os.path.join(ROOT_DIR, path['source'])

    return paths


def gen_rsa_keys():
    print 'generating RSA keys'
    for key_dir in ('/etc/pki/pulp/', '/etc/pki/pulp/consumer'):
        key_path = os.path.join(key_dir, 'rsa.key')
        key_path_pub = os.path.join(key_dir, 'rsa_pub.key')
        if not os.path.exists(key_path):
            os.system('openssl genrsa -out %s 2048' % key_path)
        if not os.path.exists(key_path_pub):
            os.system('openssl rsa -in %s -pubout > %s' % (key_path, key_path_pub))
        os.system('chmod 640 %s' % key_path)
        # The keys won't be apache owned in EL 5
        if LSB_VERSION >= 6.0:
            os.system('chown root:apache %s' % key_path)
            os.system('chown root:apache %s' % key_path_pub)


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

    if sys.version_info >= (2, 6):
        # Don't try to link apache on RHEL 5 since it is not supported for the server

        # Get links for httpd conf files according to apache version, since things
        # changed substantially between apache 2.2 and 2.4.
        apache_22_conf = (
            'server/etc/httpd/conf.d/pulp_apache_22.conf',
            '/etc/httpd/conf.d/pulp.conf'
        )
        apache_24_conf = (
            'server/etc/httpd/conf.d/pulp_apache_24.conf',
            '/etc/httpd/conf.d/pulp.conf'
        )

        apachectl_output = subprocess.Popen(
            ['apachectl', '-v'], stdout=subprocess.PIPE
        ).communicate()[0]

        search_result = re.search(r'Apache\/([0-9]+)\.([0-9]+)\.([0-9]+)', apachectl_output)
        apache_version = tuple(map(int, search_result.groups()))
        if apache_version >= (2, 4, 0):
            src, dst = apache_24_conf
        else:
            src, dst = apache_22_conf

        links.append((src, dst))

    if LSB_VERSION >= 6.0 and LSB_VERSION < 7.0:
        links.append(('server/etc/rc.d/init.d/pulp_celerybeat', '/etc/rc.d/init.d/pulp_celerybeat'))
        links.append(('server/etc/rc.d/init.d/pulp_workers',
                      '/etc/rc.d/init.d/pulp_workers'))
        links.append(('server/etc/rc.d/init.d/pulp_resource_manager',
                      '/etc/rc.d/init.d/pulp_resource_manager'))

    return links


def install(opts):
    # Install the Python packages
    environment.manage_setup_pys('install')

    warnings = []
    create_dirs(opts)
    gen_rsa_keys()
    for src, dst in getlinks():
        warning_msg = create_link(opts, os.path.join(ROOT_DIR, src), dst)
        if warning_msg:
            warnings.append(warning_msg)

    environment.copy_files(get_paths_to_copy(), opts)

    if LSB_VERSION >= 6.0:
        # Grant apache write access to the pulp tools log file and pulp
        # packages dir
        os.system('chown -R apache:apache /var/log/pulp')
        os.system('chown -R apache:apache /var/lib/pulp')

        # The Celery init script will get angry if /etc/default things aren't root owned
        os.system('chown root:root /etc/default/pulp_celerybeat')
        os.system('chown root:root /etc/default/pulp_workers')
        os.system('chown root:root /etc/default/pulp_resource_manager')

        # Guarantee apache always has write permissions
        os.system('chmod 3775 /var/log/pulp')
        os.system('chmod 3775 /var/lib/pulp')

        # Generate certificates
        print 'generating certificates'
        if not os.path.exists('/etc/pki/pulp/ca.crt'):
            os.system(os.path.join(ROOT_DIR, 'server/bin/pulp-gen-ca-certificate'))
        if not os.path.exists('/etc/pki/pulp/nodes/node.crt'):
            os.system(os.path.join(ROOT_DIR, 'nodes/common/bin/pulp-gen-nodes-certificate'))

        # Unfortunately, our unit tests fail to mock the CA certificate and key, so we need to make
        # those world readable. Until we fix this, we cannot close #1048297
        os.system('chmod 644 /etc/pki/pulp/ca.*')
        os.system('chown apache:apache /etc/pki/pulp/content')

        # Link between pulp and apache
        create_link(opts, '/var/lib/pulp/published', '/var/www/pub')

        # Grant apache write access permissions
        os.system('chmod 3775 /var/www/pub')
        os.system('chown -R apache:apache /var/lib/pulp/published')

    if warnings:
        print "\n***\nPossible problems:  Please read below\n***"
        for w in warnings:
            environment.warning(w)
    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks():
        environment.debug(opts, 'removing link: %s' % dst)
        if not os.path.islink(dst):
            environment.debug(opts, '%s does not exist, skipping' % dst)
            continue
        os.unlink(dst)

    environment.uninstall_files(get_paths_to_copy(), opts)

    # Link between pulp and apache
    if os.path.exists('/var/www/pub'):
        os.unlink('/var/www/pub')

    # Old link between pulp and apache, make sure it's cleaned up
    if os.path.exists('/var/www/html/pub'):
        os.unlink('/var/www/html/pub')

    # Remove generated certificates
    print 'removing certificates'
    os.system('rm -rf /etc/pki/pulp/*')

    # Remove the Python packages
    environment.manage_setup_pys('uninstall')

    return os.EX_OK


def create_link(opts, src, dst):
    if not os.path.lexists(dst):
        return _create_link(opts, src, dst)

    if not os.path.islink(dst):
        return "[%s] is not a symbolic link as we expected, " \
               "please adjust if this is not what you intended." % dst

    if not os.path.exists(os.readlink(dst)):
        environment.warning('BROKEN LINK: [%s] attempting to delete and fix it to point to %s.' % (dst, src))
        try:
            os.unlink(dst)
            return _create_link(opts, src, dst)
        except:
            msg = "[%s] was a broken symlink, failed to delete " \
                  "and relink to [%s], please fix this manually" % (dst, src)
            return msg

    environment.debug(opts, 'verifying link: %s points to %s' % (dst, src))
    dst_stat = os.stat(dst)
    src_stat = os.stat(src)
    if dst_stat.st_ino != src_stat.st_ino:
        msg = "[%s] is pointing to [%s] which is different than " \
              "the intended target [%s]" % (dst, os.readlink(dst), src)
        return msg


def _create_link(opts, src, dst):
    environment.debug(opts, 'creating link: %s pointing to %s' % (dst, src))
    try:
        os.symlink(src, dst)
    except OSError, e:
        msg = "Unable to create symlink for [%s] pointing to [%s], " \
              "received error: <%s>" % (dst, src, e)
        return msg


if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
