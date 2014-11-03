"""
This module contains utilities that are useful for helping developers to manage their environments.
It is used by pulp-dev.py, and may be useful in other places in the future.
"""
import os
import subprocess


ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..')


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
