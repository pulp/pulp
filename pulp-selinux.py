#!/usr/bin/env python
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

import optparse
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PLATFORM_DIR = os.path.join(BASE_DIR, "platform")
SELINUX_DIR = os.path.join(PLATFORM_DIR, "selinux", "server")
RPM_SUPPORT_DIR = os.path.join(BASE_DIR, "rpm-support")

LABELS = {
        "httpd_config_t": [
                ("%s(/.*)?", os.path.join(RPM_SUPPORT_DIR, "etc/httpd")),
        ],
        "pulp_cert_t": [
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "etc/pki/pulp")),
        ],
        "httpd_sys_content_t": [
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "etc/pulp")),
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "etc/httpd")),
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "srv/pulp")),
                ("%s(/.*)?", os.path.join(RPM_SUPPORT_DIR, "srv/pulp")),
                ("%s(/.*)?", os.path.join(RPM_SUPPORT_DIR, "etc/pulp")),
        ],
        "lib_t": [
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "src")),
                ("%s(/.*)?", os.path.join(RPM_SUPPORT_DIR, "src")),
                ("%s(/.*)?", os.path.join(RPM_SUPPORT_DIR, "plugins")),
        ],
        "etc_t": [
                ("%s(/.*)?", os.path.join(PLATFORM_DIR, "etc/gofer")),
        ],
}

class SetupException(Exception):
    def __init__(self, error_code):
        super(SetupException, self).__init__()
        self.error_code = error_code

def run_script(script_name):
    # Some of the selinux scripts invoke make and assume they will be run in the target dir
    # Therefore...ensuring we are in SELINUX_DIR prior to execution
    cmd = "cd %s && %s" % (SELINUX_DIR, os.path.join(SELINUX_DIR, script_name))
    return run_command(cmd)

def run_command(cmd):
    if DEBUG:
        print cmd
    if TEST:
        return 0 # 0 is success
    ret_val = os.system(cmd)
    if ret_val:
        print "Failure code <%s> from: %s\n" % (ret_val, cmd)
        raise SetupException(ret_val)
    return ret_val

def restorecon(path):
    run_command("/sbin/restorecon -R %s" % (path))

def add_labels():
    cmd = "/usr/sbin/semanage -i - << _EOF\n"
    paths = []
    for context_type in LABELS:
        for pattern, path in LABELS[context_type]:
            cmd += "fcontext -a -t %s '%s'\n" % (context_type, pattern%path)
            paths.append(path)
    cmd += "_EOF\n"
    run_command(cmd)
    for p in paths:
        restorecon(p)

def remove_labels():
    cmd = "/usr/sbin/semanage -i - << _EOF\n"
    paths = []
    for context_type in LABELS:
        for pattern, path in LABELS[context_type]:
            cmd += "fcontext -d '%s'\n" % (pattern % path)
            paths.append(path)
    cmd += "_EOF\n"
    run_command(cmd)
    for p in paths:
        restorecon(p)

def install(opts):
    try:
        run_script("build.sh")
        run_script("install.sh")
        run_script("enable.sh")
        add_labels()
        run_script("relabel.sh")
        return os.EX_OK
    except Exception, e:
        return e.error_code

def uninstall(opts):
    try:
        remove_labels()
        run_script("uninstall.sh")
        run_script("relabel.sh")
        return os.EX_OK
    except Exception, e:
        if hasattr(e, "error_code"):
            return e.error_code
        raise

def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()

    parser.add_option('-I', '--install',
                      action='store_true',
                      help='install pulp selinux rules')
    parser.add_option('-U', '--uninstall',
                      action='store_true',
                      help='uninstall pulp selinux rules')
    parser.add_option('-D', '--debug',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)
    parser.add_option('-T', '--test',
                      action='store_true',
                      help="display what would have run, but don't make any changes")

    parser.set_defaults(install=False,
                        uninstall=False,
                        debug=True,
                        test=False)

    opts, args = parser.parse_args()

    if opts.install and opts.uninstall:
        parser.error('both install and uninstall specified')

    if not (opts.install or opts.uninstall):
        parser.error('neither install or uninstall specified')

    return (opts, args)

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    global DEBUG
    global TEST
    opts, args = parse_cmdline()
    DEBUG=opts.debug
    TEST=opts.test
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
