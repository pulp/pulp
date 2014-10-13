"""
This module contains utilities that are useful for helping developers to manage their environments.
It is used by pulp-dev.py, and may be useful in other places in the future.
"""
import os
import subprocess


ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..')


def _manage_setup_pys(action):
    """
    This function can install or uninstall the Pulp Python packages in developer mode.

    :param action: Which action you want to perform. May be "install" or "uninstall".
    :type  action: basestring
    """
    command = ['./manage_setup_pys.sh', 'develop']
    if action == 'uninstall':
        command.append('--uninstall')

    starting_cwd = os.getcwd()
    os.chdir(ROOT_DIR)
    subprocess.call(command)
    os.chdir(starting_cwd)