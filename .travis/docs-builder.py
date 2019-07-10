#!/usr/bin/env python

import argparse
import subprocess
import os
import sys
from shutil import copyfile, rmtree
import tempfile
import yaml

WORKING_DIR = os.path.join(os.environ['TRAVIS_BUILD_DIR'], '../working')

VERSION_REGEX = "(\s*)(version)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)"
RELEASE_REGEX = "(\s*)(release)(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)"

LATEST = '2.20'

USERNAME = 'doc_builder'
HOSTNAME = '8.43.85.236'

SITE_ROOT = '/var/www/docs.pulpproject.org/'


def make_directory_with_rsync(remote_paths_list):
    """
    Ensure the remote directory path exists

    :param remote_paths_list: The list of parameters. e.g. ['en', 'latest'] to be en/latest on the
        remote.
    :type remote_paths_list: a list of strings, with each string representing a directory.
    """
    try:
        tempdir_path = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(tempdir_path)
        os.makedirs(os.sep.join(remote_paths_list))
        remote_path_arg = '%s@%s:%s%s' % (USERNAME, HOSTNAME, SITE_ROOT, remote_paths_list[0])
        local_path_arg = tempdir_path + os.sep + remote_paths_list[0] + os.sep
        rsync_command = ['rsync', '-avzh', local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command)
        if exit_code != 0:
            raise RuntimeError('An error occurred while creating remote directories.')
    finally:
        rmtree(tempdir_path)
        os.chdir(cwd)


def load_config(config_name):
    # Get the config
    config_file = os.path.join(os.path.dirname(__file__), '%s.yaml' % config_name)
    if not os.path.exists(config_file):
        print("Error: %s not found. " % config_file)
        sys.exit(1)
    with open(config_file, 'r') as config_handle:
        config = yaml.safe_load(config_handle)
    return config


def components(configuration):
    return configuration['repositories']


def ensure_dir(target_dir, clean=True):
    """
    Ensure that the directory specified exists and is empty.  By default this will delete
    the directory if it already exists

    :param target_dir: The directory to process
    :type target_dir: str
    :param clean: Whether or not the directory should be removed and recreated
    :type clean: bool
    """
    if clean:
        rmtree(target_dir, ignore_errors=True)
    try:
        os.makedirs(target_dir)
    except OSError:
        pass


def clone_branch(component):
    """
    Clone a git repository component into the working dir.

    Assumes the working dir has already been created and cleaned, if needed, before cloning.

    Returns the directory into which the branch was cloned.
    """
    print("Cloning from github: %s" % component['git_url'])
    # --branch will let you check out tags as a detached head
    command = ['git', 'clone', '--depth', '1', component['git_url'], '--branch',
               component['git_branch'], component['name']]
    subprocess.call(command, cwd=WORKING_DIR)
    return os.path.join(WORKING_DIR, component['name'])


def main():
    # Parse the args
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="Build the docs for a given release.")
    opts = parser.parse_args()
    is_pulp3 = opts.release.startswith('3')

    configuration = load_config(opts.release)

    # Get platform build version
    repo_list = components(configuration)
    try:
        pulp_dict = list(filter(lambda x: x['name'] == 'pulp', repo_list))[0]
    except IndexError:
        raise RuntimeError("config file does not have an entry for 'pulp'")
    version = pulp_dict['version']

    if version.endswith('alpha') or is_pulp3:
        build_type = 'nightly'
    elif version.endswith('beta'):
        build_type = 'testing'
    elif version.endswith('rc'):
        build_type = 'testing'
    else:
        build_type = 'ga'

    x_y_version = '.'.join(version.split('.')[:2])

    ensure_dir(WORKING_DIR, clean=True)

    # use the version update scripts to check out git repos and ensure correct versions
    for component in repo_list:
        clone_branch(component)

    plugins_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'plugins'])
    ensure_dir(plugins_dir, clean=False)

    for component in repo_list:
        if component['name'] in ['pulp', 'pulp_deb']:
            continue

        src = os.sep.join([WORKING_DIR, component['name'], 'docs'])
        dst = os.sep.join([plugins_dir, component['name']])
        os.symlink(src, dst)

    src_index_path = 'docs/pulp_index.rst'
    src_all_content_path = 'docs/all_content_index.rst'

    # copy in the plugin_index.rst file for Pulp 2 only
    # (currently Pulp 3 has its own plugins/index.rst without a need of managing it here,
    # outside of platform code)
    plugin_index_rst = os.sep.join([plugins_dir, 'index.rst'])
    copyfile('docs/plugin_index.rst', plugin_index_rst)

    # copy in the pulp_index.rst file
    pulp_index_rst = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'index.rst'])
    copyfile(src_index_path, pulp_index_rst)

    # copy in the all_content_index.rst file
    all_content_index_rst = os.sep.join([WORKING_DIR, 'pulp', 'docs', 'all_content_index.rst'])
    copyfile(src_all_content_path, all_content_index_rst)

    # make the _templates dir
    layout_dir = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates'])
    os.makedirs(layout_dir)

    # copy in the layout.html file for analytics
    layout_html_path = os.sep.join([WORKING_DIR, 'pulp', 'docs', '_templates', 'layout.html'])
    copyfile('docs/layout.html', layout_html_path)

    # build the docs via the Pulp project itself
    print("Building the docs")
    docs_directory = os.sep.join([WORKING_DIR, 'pulp', 'docs'])

    make_command = ['make', 'html']
    exit_code = subprocess.call(make_command, cwd=docs_directory)
    if exit_code != 0:
        raise RuntimeError('An error occurred while building the docs.')

    # rsync the docs to the root if it's GA of latest
    if build_type == 'ga' and x_y_version == LATEST:
        local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
        remote_path_arg = '%s@%s:%s' % (USERNAME, HOSTNAME, SITE_ROOT)
        rsync_command = ['rsync', '-avzh', '--delete', '--exclude', 'en',
                         '--omit-dir-times', local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command, cwd=docs_directory)
        if exit_code != 0:
            raise RuntimeError('An error occurred while pushing latest docs.')

        # Also publish to the /en/latest/ directory
        make_directory_with_rsync(['en', 'latest'])
        local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
        remote_path_arg = '%s@%s:%sen/latest/' % (USERNAME, HOSTNAME, SITE_ROOT)
        rsync_command = ['rsync', '-avzh', '--delete', local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command, cwd=docs_directory)
        if exit_code != 0:
            raise RuntimeError("An error occurred while pushing the 'latest' directory.")

    # rsync the nightly "2-master" docs to an unversioned "nightly" dir for
    # easy linking to in-development docs: /en/nightly/
    if build_type == 'nightly' and opts.release == '2-master':
        local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
        remote_path_arg = '%s@%s:%sen/%s/' % (USERNAME, HOSTNAME, SITE_ROOT, build_type)
        make_directory_with_rsync(['en', build_type])
        rsync_command = ['rsync', '-avzh', '--delete', local_path_arg, remote_path_arg]
        exit_code = subprocess.call(rsync_command, cwd=docs_directory)
        if exit_code != 0:
            raise RuntimeError('An error occurred while pushing nightly docs.')

    # rsync the docs
    local_path_arg = os.sep.join([docs_directory, '_build', 'html']) + os.sep
    remote_path_arg = '%s@%s:%sen/%s/' % (USERNAME, HOSTNAME, SITE_ROOT, x_y_version)
    if build_type != 'ga':
        remote_path_arg += build_type + '/'

        make_directory_with_rsync(['en', x_y_version, build_type])
        rsync_command = ['rsync', '-avzh', '--delete', local_path_arg, remote_path_arg]
    else:
        make_directory_with_rsync(['en', x_y_version])
        rsync_command = ['rsync', '-avzh', '--delete', '--exclude', 'nightly', '--exclude',
                         'testing', local_path_arg, remote_path_arg]
    exit_code = subprocess.call(rsync_command, cwd=docs_directory)
    if exit_code != 0:
        raise RuntimeError('An error occurred while pushing docs.')


if __name__ == "__main__":
    main()
