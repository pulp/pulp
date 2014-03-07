#!/usr/bin/env python

import os
import sys
import shutil
import subprocess
import time
import uuid
from optparse import OptionParser

import koji


home_directory = os.path.expanduser('~')
opts = {
    'cert': os.path.join(home_directory, '.katello.cert'),
    'ca': os.path.join(home_directory, '.katello-ca.cert'),
    'serverca': os.path.join(home_directory, '.katello-ca.cert')
}

mysession = koji.ClientSession("http://koji.katello.org/kojihub", opts)
mysession.ssl_login(opts['cert'], opts['ca'], opts['serverca'])

ARCH_LIST = ('i386', 'x86_64')
DISTRIBUTION_MAP = {
    'el5': 'rhel5',
    'el6': 'rhel6',
    'fc19': 'fedora19',
    'fc20': 'fedora20'
}

DISTRIBUTION_PUBLISH_DIRECTORIES = {
    'el5': '5server',
    'el6': '6server',
    'fc19': 'fedora-18',
    'fc20': 'fedora-19'
}

DIST_LIST = DISTRIBUTION_MAP.keys()
WORKSPACE = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../'))
MASH_DIR = os.path.join(WORKSPACE, 'mash')
TITO_DIR = os.path.join(WORKSPACE, 'tito')

usage = "usage: %prog [options] <pulp-version> <stream-target>\n  The stream target is one of " \
        "(beta, testing, or stable)"
parser = OptionParser(usage)
parser.add_option("--packageonly", action="store_true", default=False,
                  help="Create the repos only.  Do not build with koji.")
parser.add_option("--push", action="store_true", default=False,
                  help="Push the created repos to fedorapeople.")
parser.add_option("--scratch", action="store_true", default=False,
                  help="Use the scratch option for the koji builder.")
(opts, args) = parser.parse_args()

if len(args) < 2:
    print "ERROR: need to specify pulp-version and target\n"
    parser.print_help()
    sys.exit(1)

pulp_version = args[0]
build_stream = args[1]

if build_stream not in ['stable', 'testing', 'beta']:
    print "Error: %s is not a valid build stream.  Value must be one of 'stable', 'testing'," \
          " or 'beta'" % build_stream
    sys.exit(1)

if build_stream == 'stable':
    build_tag = "pulp-%s" % pulp_version
else:
    build_tag = "pulp-%s-%s" % (pulp_version, build_stream)


def ensure_dir(target_dir):
    shutil.rmtree(target_dir, ignore_errors=True)
    try:
        os.makedirs(target_dir)
    except OSError:
        pass


def build_srpm(distributions):
    """
    Build the srpms to feed to koji.
    For now we are only doing real builds.  There is commented out code in here
    to bump the version with a timestamp for when we want to do scratch builds
    """
    for dist in distributions:
        tito_path = os.path.join(TITO_DIR, dist)
        ensure_dir(tito_path)
        spec_list = ['pulp', 'pulp/nodes', 'pulp_rpm', 'pulp_puppet']
        for spec_location in spec_list:
            working_dir = os.path.join(WORKSPACE, spec_location)
            os.chdir(working_dir)
            # Update the spec file
            # sed_command = 'sed -i "/^Release:/ s/%/.${release}%/" *.spec'
            # sed_command = sed_command.replace("${release}", TIMESTAMP)
            # subprocess.call(sed_command, shell=True)
            # Build the SRPM
            # subprocess.call(['tito', 'tag', '--keep-version', '--accept-auto-changelog'])
            distribution = ".%s" % dist
            print "Building Srpm for %s" % distribution
            subprocess.check_call(['tito', 'build', '--offline', '--srpm', '--output', tito_path,
                                  '--dist', distribution])
            # subprocess.call(['tito', 'tag', '-u'])


def build_with_koji(build_tag_prefix, target_dists, scratch=False):
    """
    Run builds of all the pulp srpms on koji
    :param target_dists: a list of dist tags to use for the
    Return list of task_ids to monitor
    """
    builds = []
    upload_prefix = 'pulp-build/%s' % str(uuid.uuid4())

    for dist in target_dists:
        srpm_dir = os.path.join(TITO_DIR, dist)
        build_target = "%s-%s" % (build_tag_prefix, DISTRIBUTION_MAP[distvalue])

        # Get all the source RPMs that were built
        # submit each srpm
        for dir_file in os.listdir(srpm_dir):
            if dir_file.endswith(".rpm"):
                full_path = os.path.join(srpm_dir, file)
                # upload the file
                print "Uploading %s" % file
                mysession.uploadWrapper(full_path, upload_prefix)
                # Start the koji build
                source = "%s/%s" % (upload_prefix, file)
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
            #print "Got State: %s" % state
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
    src) assuming that the contains packages with that tag

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
        #print "%(name)s %(nvr)s %(release)s %(package_name)s %(release)s %(version)s" % package
        koji_dir = "/packages/%(name)s/%(version)s/%(release)s/" % package
        data_dir = "/packages/%(name)s/%(version)s/%(release)s/data" % package
        koji_url = "http://koji.katello.org"
        location_on_koji = "%s%s" % (koji_url, koji_dir)
        command = "wget -r -np -nH --cut-dirs=4 -R index.htm*  %s -X %s" % \
                  (location_on_koji, data_dir)
        print command
        subprocess.check_call(command, shell=True)


def build_repos(output_dir):
    """
    Build the yum repos for each arch
    this method assumes that the directories already exist with each of the arches needed

    :param output_dir: The directory where the files were downloaded from koji
    :type output_dir: str
    """
    noarch_dir = os.path.join(output_dir, 'noarch')
    comps_file = os.path.join(WORKSPACE, 'pulp', 'comps.xml')
    for arch in ARCH_LIST:
        arch_dir = os.path.join(output_dir, arch)
        if os.path.exists(arch_dir):
            # Copy the noarch files to the arch_dir
            command = "cp -R %s/* %s" % (noarch_dir, arch_dir)
            print command
            subprocess.check_call(command, shell=True)
            # create the repo
            command = "createrepo -g %s %s" % (comps_file, arch_dir)
            subprocess.check_call(command, shell=True)


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

# clean out and rebuild the mash directory & the target arch directories
ensure_dir(MASH_DIR)
ensure_dir(TITO_DIR)
shutil.rmtree(MASH_DIR, ignore_errors=True)
os.makedirs(MASH_DIR)

# clean out and recreate the tito directory
shutil.rmtree(TITO_DIR, ignore_errors=True)
os.makedirs(TITO_DIR)

# Build the repos if requested
if not opts.packageonly:
    build_srpm(DIST_LIST)
    builds = build_with_koji(build_tag, DIST_LIST, opts.scratch)

# Download the rpms and create the yum repos
for distkey, distvalue in DISTRIBUTION_MAP.iteritems():
    build_target = "%s-%s" % (build_tag, distvalue)
    output_dir = os.path.join(MASH_DIR, DISTRIBUTION_PUBLISH_DIRECTORIES[distkey])
    ensure_dir(output_dir)
    for arch in ARCH_LIST:
        os.makedirs(os.path.join(output_dir, arch))
    print "Downloading tag: %s to %s" % (build_target, output_dir)
    download_rpms_from_tag(build_target, output_dir)
    build_repos(output_dir)

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
    print "Cleaning out previously published repo directory"
    command = 'rm -rf %s' % target_repo_dir
    run_destination_ssh_step(command)
    upload_and_unpack_binary_repository(target_repo_dir, os.path.join(MASH_DIR, 'repo.tar'))
    print "Finished updating repo"


