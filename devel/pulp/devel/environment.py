"""
This module contains utilities that are useful for helping developers to manage their environments.
It is used by pulp-dev.py, and may be useful in other places in the future.
"""
import os
import shutil
import subprocess
import sys


ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..')
WARNING_COLOR = '\033[31m'
WARNING_RESET = '\033[0m'


def copy_files(paths, opts):
    """
    Install developer files by copying the given paths to their destinations. paths should
    be a list of dictionaries of this form:

        {'source': <relative path to source file in git repo>,
         'destination': <absolute path to destination location to copy the source file to>,
         'owner': <user who should own the file>,
         'group': <group who should own the file>,
         'mode': <Unix filesystem mode that should be applied to the installed file>,
         'overwrite': <True if the destination should be overwritten if it exists, False otherwise>}

    :param paths: List of dictionaries of the form described above
    :type  paths: list
    :param opts:  The command line options
    :type  opts:  dict
    """
    for path in paths:
        if not os.path.exists(path['destination']) or path['overwrite']:
            msg = 'copying %(src)s to %(dst)s' % {'src': path['source'], 'dst': path['destination']}
            debug(opts, msg)
            shutil.copy2(path['source'], path['destination'])
            os.system('chown %s:%s %s' % (path['owner'], path['group'], path['destination']))
            os.system('chmod %s %s' % (path['mode'], path['destination']))


def debug(opts, msg):
    """
    Write the given msg to stderr if we are in debug mode.

    :param opts:  The command line options
    :type  opts:  dict
    :param msg:   The message to write
    :type  msg:   basestring
    """
    if not opts.debug:
        return
    sys.stderr.write('%s\n' % msg)


def manage_setup_pys(action, path_to_manage_script=ROOT_DIR):
    """
    This function can install or uninstall the Pulp Python packages in developer mode.

    :param action:                Which action you want to perform. May be "install" or "uninstall".
    :type  action:                basestring
    :param path_to_manage_script: The path to the directory containing a manage_setup_pys.sh that
                                  wish to call.
    :type  path_to_manage_script: basestring
    """
    command = ['./manage_setup_pys.sh', 'develop']
    if action == 'uninstall':
        command.append('--uninstall')

    starting_cwd = os.getcwd()
    os.chdir(path_to_manage_script)
    subprocess.call(command)
    os.chdir(starting_cwd)


def uninstall_files(paths, opts):
    """
    Remove paths that have "overwrite" set to True in paths. paths is the same data structure that
    is documented in the copy_files function.

    :param paths: List of dictionaries of the form described in copy_files()
    :type  paths: list
    :param opts:  The command line options
    :type  opts:  dict
    """
    for path in paths:
        if path['overwrite'] and os.path.exists(path['destination']):
            msg = 'removing %(dst)s' % {'dst': path['destination']}
            debug(opts, msg)
            os.unlink(path['destination'])


def warning(msg):
    """
    Write the given msg to stdout in the WARNING_COLOR.

    :param msg:   The message to write
    :type  msg:   basestring
    """
    print "%s%s%s" % (WARNING_COLOR, msg, WARNING_RESET)
