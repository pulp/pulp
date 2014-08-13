import optparse
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PULP_SERVER_DIR = os.path.join(BASE_DIR, "server")
SELINUX_DIR = os.path.join(PULP_SERVER_DIR, "selinux", "server")
RPM_PLUGIN_DIR = os.path.join(BASE_DIR, "..", "pulp_rpm", "plugins")

LABELS = {
        "httpd_config_t": [
                ("%s(/.*)?", os.path.join(RPM_PLUGIN_DIR, "etc", "httpd")),
        ],
        "pulp_cert_t": [
                ("%s(/.*)?", os.sep + os.path.join("etc", "pki", "pulp")),
        ],
        "httpd_sys_content_t": [
                ("%s(/.*)?", os.path.join(PULP_SERVER_DIR, "etc", "pulp")),
                ("%s(/.*)?", os.path.join(PULP_SERVER_DIR, "etc", "httpd")),
                ("%s(/.*)?", os.path.join(PULP_SERVER_DIR, "srv", "pulp")),
                ("%s(/.*)?", os.path.join(RPM_PLUGIN_DIR, "srv", "pulp")),
                ("%s(/.*)?", os.path.join(RPM_PLUGIN_DIR, "etc", "pulp")),
        ],
        "lib_t": [
                ("%s(/.*)?", os.path.join(PULP_SERVER_DIR, "pulp")),
                ("%s(/.*)?", os.path.join(RPM_PLUGIN_DIR)),
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
