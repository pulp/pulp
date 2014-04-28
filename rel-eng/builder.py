#!/usr/bin/env python

import os
import sys
import shutil
import subprocess
import time
import uuid
import argparse

import koji


home_directory = os.path.expanduser('~')
opts = {
    'cert': os.path.join(home_directory, '.katello.cert'),
    'ca': os.path.join(home_directory, '.katello-ca.cert'),
    'serverca': os.path.join(home_directory, '.katello-ca.cert')
}

mysession = koji.ClientSession("http://koji.katello.org/kojihub", opts)
mysession.ssl_login(opts['cert'], opts['ca'], opts['serverca'])

ARCH = 'arch'
REPO_NAME = 'repo_name'
DIST_KOJI_NAME = 'koji_name'
PULP_PACKAGES = 'pulp_packages'

# Mapping for the package keys in the DISTRIBUTION_INFO to the locations on disk
PULP_PACKAGE_LOCATIONS = {
    'pulp': 'pulp',
    'pulp-nodes': 'pulp/nodes',
    'pulp-rpm': 'pulp_rpm',
    'pulp-puppet': 'pulp_puppet'
}

DISTRIBUTION_INFO = {
    'el5': {
        ARCH: ['i386', 'x86_64'],
        REPO_NAME: '5Server',
        DIST_KOJI_NAME: 'rhel5',
        PULP_PACKAGES: ['pulp', 'pulp-rpm', 'pulp-puppet']
    },
    'el6': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: '6Server',
        DIST_KOJI_NAME: 'rhel6',
        PULP_PACKAGES: ['pulp', 'pulp-nodes', 'pulp-rpm', 'pulp-puppet']
    },
    'fc19': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-19',
        DIST_KOJI_NAME: 'fedora19',
        PULP_PACKAGES: ['pulp', 'pulp-nodes', 'pulp-rpm', 'pulp-puppet']
    },
    'fc20': {
        ARCH: ['i686', 'x86_64'],
        REPO_NAME: 'fedora-20',
        DIST_KOJI_NAME: 'fedora20',
        PULP_PACKAGES: ['pulp', 'pulp-nodes', 'pulp-rpm', 'pulp-puppet']
    },
}

DIST_LIST = DISTRIBUTION_INFO.keys()
WORKSPACE = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../'))
MASH_DIR = os.path.join(WORKSPACE, 'mash')
TITO_DIR = os.path.join(WORKSPACE, 'tito')
DEPS_DIR = os.path.join(WORKSPACE, 'pulp', 'deps')

parser = argparse.ArgumentParser()
parser.add_argument("version", help="The version of pulp to run the build for (2.4, 2.5, etc.)")
parser.add_argument("stream", choices=['stable', 'testing', 'beta'],
                    help="The target release stream to build.")
parser.add_argument("--update-tag-package-list", action="store_true", default=False,
                    help="Update the packages associated with the tag. This will verify that the "
                         "dependencies & pulp packages are associated with the tag and that the "
                         "specific versions of each of the dependencies has been associated with "
                         "the appropriate tag. The current logged in user will be the owner for "
                         "any packages that are added to the tag.")
parser.add_argument("--disable-build", action="store_true", default=False,
                    help="Disable koji building.")
parser.add_argument("--disable-repo-build", action="store_true", default=False,
                    help="Do not create repos")
parser.add_argument("--push", action="store_true", default=False,
                    help="Push the created repos to fedorapeople.")
parser.add_argument("--scratch", action="store_true", default=False,
                    help="Use the scratch option for the koji builder.")
parser.add_argument("--build-dependency",
                    help="If specified, only build the specified dependency")
parser.add_argument("--distribution", choices=DIST_LIST, nargs='+',
                    help="If specified, only build for the specified distribution")
parser.add_argument("--tito-tag", help="The specific tito tag that should be built.  "
                                       "If not specified the latest will be used.")

opts = parser.parse_args()

pulp_version = opts.version
build_stream = opts.stream

if build_stream == 'stable':
    build_tag = "pulp-%s" % pulp_version
else:
    build_tag = "pulp-%s-%s" % (pulp_version, build_stream)

# If we are building with a dependency override the global default distribution list
# with the list for that dependency.
if opts.build_dependency:
    dist_list_file = os.path.join(DEPS_DIR, opts.build_dependency, 'dist_list.txt')
    try:
        with open(dist_list_file, 'r') as handle:
            line = handle.readline()
            dists_from_dep = line.split(' ')
            # Verify that all the dists specified are valid
            if not set(dists_from_dep).issubset(DIST_LIST):
                print "The distribution keys specified for %s is not a subset of %s" % \
                      (opts.build_dependency, str(DIST_LIST))
                sys.exit(1)
            DIST_LIST = dists_from_dep
    except IOError:
        print "dist_list.txt file not found for %s." % opts.build_dependency
        sys.exit(1)


# If a specific distribution or list of distributions has been specified on the command line
# use that list
if opts.distribution:
    print "Building for %s only" % opts.distribution
    DIST_LIST = opts.distribution


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
        shutil.rmtree(target_dir, ignore_errors=True)
    try:
        os.makedirs(target_dir)
    except OSError:
        pass


def build_srpm(distributions):
    """
    Build the srpms to feed to koji.

    :param distributions: list of distribution tags that we want to build SRPMs for
    :type distributions: list of str
    """
    for dist in distributions:
        tito_path = os.path.join(TITO_DIR, dist)
        ensure_dir(tito_path)
        spec_list = []
        if opts.build_dependency:
            spec_list = ['pulp/deps/%s' % opts.build_dependency]
        else:
            for pulp_package in DISTRIBUTION_INFO[dist][PULP_PACKAGES]:
                spec_list.append(PULP_PACKAGE_LOCATIONS[pulp_package])

        for spec_location in spec_list:
            working_dir = os.path.join(WORKSPACE, spec_location)
            os.chdir(working_dir)
            distribution = ".%s" % dist
            print "Building Srpm for %s" % distribution
            command = ['tito', 'build', '--offline', '--srpm', '--output', tito_path,
                       '--dist', distribution]
            if opts.scratch:
                command.append('--test')

            if opts.tito_tag:
                command.append('--tag')
                command.append(opts.tito_tag)

            subprocess.check_call(command)


def build_with_koji(build_tag_prefix, target_dists, scratch=False):
    """
    Run builds of all the pulp srpms on koji
    :param build_tag_prefix: The prefix for the build tag to build using koji.  For example
           pulp-2.4-testing
    :type build_tag_prefix: str
    :param target_dists: a list of dist tags to use for the
    :type target_dists: list of dist tags to build for
    :param scratch: Whether or not to run a scratch build with koji
    :type scratch: bool
    :returns: list of task_ids to monitor
    :rtype: list of str
    """
    builds = []
    upload_prefix = 'pulp-build/%s' % str(uuid.uuid4())

    for dist in target_dists:
        srpm_dir = os.path.join(TITO_DIR, dist)
        build_target = "%s-%s" % (build_tag_prefix,
                                  (DISTRIBUTION_INFO.get(dist)).get(DIST_KOJI_NAME))

        # Get all the source RPMs that were built
        # submit each srpm
        for dir_file in os.listdir(srpm_dir):
            if dir_file.endswith(".rpm"):
                full_path = os.path.join(srpm_dir, dir_file)
                # upload the file
                print "Uploading %s" % dir_file
                mysession.uploadWrapper(full_path, upload_prefix)
                # Start the koji build
                source = "%s/%s" % (upload_prefix, dir_file)
                task_id = int(mysession.build(source, build_target, {'scratch': scratch}))
                print "Created Build Task: %i" % task_id
                builds.append(task_id)
    return builds


def wait_for_completion(build_ids):
    """
    For a given list of build ids.  Monitor them and wait for all to complete
    """
    for task_id in build_ids:
        while True:
            info = mysession.getTaskInfo(task_id)
            state = koji.TASK_STATES[info['state']]
            if state in ['FAILED', 'CANCELED']:
                msg = "Task %s: %i" % (state, task_id)
                raise Exception(msg)
            elif state in ['CLOSED']:
                print "Task %s: %i" % (state, task_id)
                break
            time.sleep(5)


def download_rpms_from_tag(tag, output_directory):
    """
    For a given tag download all the latest contents of that tag to the given output directory.
    This will create subdirectories for each arch in the tag (noarch, i686, x86_64,
    src) assuming that the contains packages with that tag.

    :param tag: The koji tag to get the files from
    :type tag: str
    :param output_directory: The directory to save the output into
    :type output_directory: str
    """
    # clean out and ensure the output directory exists
    shutil.rmtree(output_directory, ignore_errors=True)
    os.makedirs(output_directory)

    # arches I care about = src, noarch, i686 and x86_64
    rpms = mysession.getLatestRPMS(tag)

    # Iterate through the packages and pull their output from koji with wget
    os.chdir(output_directory)
    for package in rpms[1]:
        koji_dir = "/packages/%(name)s/%(version)s/%(release)s/" % package
        data_dir = "/packages/%(name)s/%(version)s/%(release)s/data" % package
        koji_url = "http://koji.katello.org"
        location_on_koji = "%s%s" % (koji_url, koji_dir)
        command = "wget -r -np -nH --cut-dirs=4 -R index.htm*  %s -X %s" % \
                  (location_on_koji, data_dir)
        subprocess.check_call(command, shell=True)


def build_repos(output_dir, dist):
    """
    Build the yum repos for each arch
    this method assumes that the directories already exist with each of the arches needed

    :param output_dir: The directory where the files were downloaded from koji
    :type output_dir: str
    :param dist: The key for the distribution map for this repo
    :type dist: str
    """
    noarch_dir = os.path.join(output_dir, 'noarch')
    comps_file = os.path.join(WORKSPACE, 'pulp', 'comps.xml')
    arch_list = (DISTRIBUTION_INFO.get(dist)).get(ARCH)
    for arch in arch_list:
        arch_dir = os.path.join(output_dir, arch)
        ensure_dir(arch_dir, False)

        # Copy the noarch files to the arch_dir
        command = "cp -R %s/* %s" % (noarch_dir, arch_dir)
        subprocess.check_call(command, shell=True)
        # create the repo
        command = "createrepo -g %s %s" % (comps_file, arch_dir)
        subprocess.check_call(command, shell=True)

    # If there is an i686 directory rename it i386 since that is what the distributions expect
    if os.path.exists(os.path.join(output_dir, 'i686')):
        shutil.move(os.path.join(output_dir, 'i686'),
                    os.path.join(output_dir, 'i386'))
    # Remove the noarch directory since it is not needed after repos are created
    shutil.rmtree(noarch_dir, ignore_errors=True)


def run_destination_ssh_step(ssh_command):
    """
    Executes the given command on the destination host.
    """
    command = 'ssh %s@%s \'%s\'' % ('pulpadmin', 'fedorapeople.org', ssh_command)
    subprocess.check_call(command, shell=True)


def upload_and_unpack_binary_repository(target_directory, tar_file):
    """
    Uploads the binary repository tarball to the destination and unzips it to the
    appropriate path for the repository.

    :param target_directory: The location on the hosting server
    :type target_directory: str
    :param tar_file: The fully qualified name & path of the tar file to upload
    :type tar_file: str
    """

    # First make sure the directory exists on the host
    command = 'mkdir -p %s' % target_directory
    run_destination_ssh_step(command)

    # Upload the built repos
    command = 'scp %s %s@%s:%s' % (tar_file, 'pulpadmin', 'fedorapeople.org', target_directory)
    subprocess.check_call(command)

    # Untar the repo
    command = 'cd %s && tar xvf %s' % (target_directory, 'repo.tar')
    run_destination_ssh_step(command)

    # Delete the repo tarball
    command = 'rm %s/repo.tar' % (target_directory)
    run_destination_ssh_step(command)


def get_tag_packages(tag):
    """
    Get the set of packages currently associated with a tag

    :param tag: the tag to search for in koji
    :type tag: str

    :returns: a set of package names
    :rtype: set of str
    """
    dsttag = mysession.getTag(tag)
    pkglist = set([(p['package_name']) for p in mysession.listPackages(tagID=dsttag['id'])])
    return pkglist


def get_supported_dists_for_dep(dep_directory):
    """
    Get a list of the supported distributions for the dependency in the given directory

    :param dep_directory: The full path of the directory where the dependency is stored
    :type dep_directory: str

    :returns: a set of dist keys for the dists that this dep supports
    :rtype: set of str
    """
    dist_list_file = os.path.join(dep_directory, 'dist_list.txt')
    try:
        with open(dist_list_file, 'r') as handle:
            line = handle.readline()
            dists_from_dep = line.split(' ')
    except IOError:
        print "dist_list.txt file not found for %s." % dep_directory
        sys.exit(1)

    return set(dists_from_dep)


def get_deps_for_dist(dist_key):
    """
    Get all the dependency packages that are required for a given distribution

    :param dist_key: The distribution for which to get the deps
    :type dist_key: str
    :returns: a list of packages
    :rtype: set of str
    """
    deps_packages = set([name for name in os.listdir(DEPS_DIR)
                         if os.path.isdir(os.path.join(DEPS_DIR, name))])

    dist_deps = []
    for dep in deps_packages:
        dist_list = get_supported_dists_for_dep(os.path.join(DEPS_DIR, dep))
        if dist_key in dist_list:
            dist_deps.append(dep)

    return set(dist_deps)


def add_packages_to_tag(base_tag):
    """
    Add a set of package to a given tag.  If a package needs to be added to the tag
    the current user will be used as the owner.

    :param base_tag: The distribution independent root of the build tag.  For example:
                     pulp-2.4-testing
    :type base_tag: str
    """
    task_list = []
    current_user = mysession.getLoggedInUser().get('name')
    # For each Distribution
    for dist_key, dist_info in DISTRIBUTION_INFO.iteritems():
        build_tag = "%s-%s" % (base_tag, dist_info.get(DIST_KOJI_NAME))
        # get the current tagged builds for this build_tag
        build_tag_existing_builds = [data.get('nvr') for data in mysession.listTagged(build_tag)]

        dist_deps = get_deps_for_dist(dist_key)
        packages_in_tag = get_tag_packages(build_tag)
        delta = dist_deps.difference(packages_in_tag)
        # add the regular dependencies
        for package in delta:
            # Add the package to the tag
            print "adding %s to %s" % (package, build_tag)
            mysession.packageListAdd(build_tag, package, current_user)

        # verify all of the versions of the packages
        for package in dist_deps:
            # Get the current version of the dep and add it to the tag if it exists in koji
            specfile = os.path.join(DEPS_DIR, package, "%s.spec" % package)
            command = 'rpm --queryformat "%{RPMTAG_VERSION}-%{RPMTAG_RELEASE} "' \
                      ' --specfile ' + specfile + ' | cut -f1 -d" "'
            result = str(subprocess.check_output(command, shell=True))
            version = result.strip()
            # remove the distkey from the version string
            version = version[:version.rfind('.')]
            package_nvr = "%s-%s.%s" % (package, version, dist_key)
            # Verify that this version of the package is not already in the tag
            if package_nvr not in build_tag_existing_builds:
                # verify that the package_nvr exists in koji at all
                existing = mysession.search(package_nvr, 'build', 'glob')
                if existing:
                    print "Adding %s to %s" % (package_nvr, build_tag)
                    task_id = mysession.tagBuild(build_tag, package_nvr)
                    task_list.append(task_id)

        # add the missing pulp packages
        pulp_packages = set(dist_info.get(PULP_PACKAGES))
        delta = pulp_packages.difference(packages_in_tag)
        for package in delta:
            print "adding %s to %s" % (package, build_tag)
            mysession.packageListAdd(build_tag, package, current_user)

    # Monitor the task list until all are completed
    wait_for_completion(task_list)

# clean out and rebuild the mash directory & the target arch directories
ensure_dir(MASH_DIR)
ensure_dir(TITO_DIR)
shutil.rmtree(MASH_DIR, ignore_errors=True)
os.makedirs(MASH_DIR)

# clean out and recreate the tito directory
shutil.rmtree(TITO_DIR, ignore_errors=True)
os.makedirs(TITO_DIR)

# First update package tags if specified
if opts.update_tag_package_list:
    add_packages_to_tag(build_tag)
    print "After updating packages the build target repositories need to rebuild.  Please monitor "\
          "the koji server directly to ensure that those tasks have finished before building new " \
          "dependencies or versions of pulp.  "
    sys.exit(0)

# Build the repos if requested
if not opts.disable_build:
    build_srpm(DIST_LIST)
    builds = build_with_koji(build_tag, DIST_LIST, opts.scratch)
    wait_for_completion(builds)

# Don't build the repos if we are building a dependency
if not opts.disable_repo_build:
    # Download the rpms and create the yum repos
    for distkey, distvalue in DISTRIBUTION_INFO.iteritems():
        build_target = "%s-%s" % (build_tag, distvalue.get(DIST_KOJI_NAME))
        output_dir = os.path.join(MASH_DIR, distvalue.get(REPO_NAME))
        ensure_dir(output_dir)
        for arch in distvalue.get(ARCH):
            os.makedirs(os.path.join(output_dir, arch))
        print "Downloading tag: %s to %s" % (build_target, output_dir)
        download_rpms_from_tag(build_target, output_dir)
        build_repos(output_dir, distkey)

    # Push to hosted location
    if opts.push:
        print "Push has not been implemented yet."
        repos_dir = '/srv/repos/pulp/pulp'
        target_repo_dir = "%s/%s/%s" % (repos_dir, build_stream, pulp_version)
        # tar up all the files
        os.chdir(MASH_DIR)
        subprocess.check_call("tar cvf repo.tar *", shell=True)
        tar_file = os.path.join(MASH_DIR, "repo.tar")
        print "Need to %s to sync to fedorapeople %s " % (tar_file, target_repo_dir)
        # print "Cleaning out previously published repo directory"
        # command = 'rm -rf %s' % target_repo_dir
        # run_destination_ssh_step(command)
        # upload_and_unpack_binary_repository(target_repo_dir, os.path.join(MASH_DIR, 'repo.tar'))
        # print "Finished updating repo"
