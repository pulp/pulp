# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
import os
import sys
import yum
import time
import shutil
import tempfile

from logging import INFO, basicConfig, getLogger
basicConfig(filename='/tmp/pulp_package_migrate.log', level=INFO)
log = getLogger("pulp_package_migrate")
VERBOSE = False
TEST_RUN = False

def get_repo_packages(path):
    """
    Get a list of packages in the yum repo.
    """
    class Package:
        __slots__ =\
        ('relativepath',
         'checksum',
         'checksum_type',
         'name',
         'epoch',
         'version',
         'release',
         'arch',
            )
        def __init__(self, p):
            for k in self.__slots__:
                v = getattr(p, k)
                setattr(self, k, v)
    temp_path = tempfile.mkdtemp(prefix="temp_pulp_repo")
    try:
        packages = []
        r = yum.yumRepo.YumRepository(temp_path)
        try:
            r.baseurl = "file://%s" % (path.encode("ascii", "ignore"))
        except UnicodeDecodeError:
            r.baseurl = "file://%s" % (path)
        try:
            r.basecachedir = path.encode("ascii", "ignore")
        except UnicodeDecodeError:
            r.basecachedir = path
        r.baseurlSetup()
        if not os.path.exists(os.path.join(path, r.repoMDFile)):
            # check if repomd.xml exists before loading package sack
            return []
        sack = r.getPackageSack()
        sack.populate(r, 'metadata', None, 0)
        for p in sack.returnPackages():
            packages.append(Package(p))
        r.close()
        return packages
    finally:
        try:
            shutil.rmtree(temp_path)
        except Exception, e:
            log.error("Unable to remove temporary directory: %s" % (temp_path))

def _migrate_repo_packages(repo_dir, top_package_location):
    """
    * Lookup packages in a given repo dir by parsing primary xml data
    * migrate the package from old location to new location with full checksum
    """
    global TEST_RUN
    repo_packages = get_repo_packages(repo_dir)
    log.info("* Processing %s packages in repo dir %s" % (len(repo_packages), repo_dir))
    migrated = []
    skipped = []
    for package in repo_packages:
        repo_pkg_path  = os.path.join(repo_dir, package.relativepath)
        pkg_real_path = os.path.realpath(repo_pkg_path)
        new_pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (top_package_location, package.name,
                                                 package.version, package.release, package.arch,
                                                 package.checksum, os.path.basename(package.relativepath))
        if os.path.exists(new_pkg_path):
            if new_pkg_path == pkg_real_path:
                log.info("pakage symlink %s already pointing to new package path %s; skipping" %\
                                        (repo_pkg_path, new_pkg_path))
                skipped.append(package)
                continue
        else:
            # copy package from old to new location
            if os.path.exists(pkg_real_path):
                if not TEST_RUN:
                    if not os.path.isdir(os.path.dirname(new_pkg_path)):
                        os.makedirs(os.path.dirname(new_pkg_path))
                    shutil.copy(pkg_real_path, new_pkg_path)
                    # remove old package path
                    os.remove(pkg_real_path)
                    log.debug("successfully copied package to new location @ %s" % new_pkg_path)
            else:
                # package doesnt exist on filesystem, skip
                log.info("package %s doesnt exist on the file system; skip" % repo_pkg_path)
                skipped.append(package)
                continue
        # remove the old symlink from repo location
        if not TEST_RUN:
            os.unlink(repo_pkg_path)
            # create the new symlink
            os.symlink(new_pkg_path, repo_pkg_path)
        migrated.append(package)
        msg = "migrated package [%s] from old location [%s] to new location [%s] and created a symlink [%s]" %\
                (os.path.basename(package.relativepath), pkg_real_path, new_pkg_path, repo_pkg_path)
        log.info(msg)
    log.info("Finished migrating packages from repo %s" % repo_dir)
    return migrated, skipped

def _discover_yum_repodirs(top_repo_location):
    """
    Discover repo dirs with yum metadata
    """
    log.info("Discovering repo directories for migration @ %s" % top_repo_location)
    repodirs = []
    if not os.path.exists(top_repo_location):
        return repodirs
    for root, dirs, files in os.walk(top_repo_location):
        for dir in dirs:
            fpath = "%s/%s" % (root, dir)
            if fpath.endswith("repodata"):
                if os.path.exists(os.path.join(fpath, "repomd.xml")):
                    if fpath.rfind('/repodata') > 0:
                        result = fpath[:fpath.rfind('/repodata')]
                        repodirs.append(result)
                    else:
                        continue
    return repodirs

def do_migrate(top_level_content_dir):
    """
    Perform the per repo migration for specified top level content directory
    @param top_level_content_dir: top directory location where central repos and packages dirs exist
    @type top_level_content_dir: string
    """
    migrate_summary = {}
    top_repos_location = os.path.join(top_level_content_dir, "repos")
    top_packages_location = os.path.join(top_level_content_dir, "packages")
    if not os.path.exists(top_repos_location):
        msg = "Unable to find top level repos directory @ %s; Cannot continue migrate" % top_repos_location
        log_print_msg(log.error, msg)
        return migrate_summary
    if not os.path.exists(top_packages_location):
        msg = "Unable to find top level packages directory @ %s; Cannot continue migrate" % top_packages_location
        log_print_msg(log.error, msg)
        return migrate_summary
    log_print_msg(log.info,
        "* Starting Migration; this process can take some time depending on the number of repos and packages")
    repodirs = _discover_yum_repodirs(top_repos_location)
    log_print_msg(log.info, "* Number of repo directories discovered for migration: %s\n" % len(repodirs))
    for repodir in repodirs:
        try:
            migrated, skipped = _migrate_repo_packages(repodir, top_packages_location)
            migrate_summary[repodir] = dict(migrated=len(migrated), skipped=len(skipped))
        except Exception,e:
            log.error("Error: %s" % str(e))
            return migrate_summary
    return migrate_summary

def do_validation():
    pass

def log_print_msg(log_fn, msg):
    global VERBOSE
    log_fn(msg)
    if VERBOSE: print msg

def parse_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--dir", dest="top_level_content_dir",
                    help="Top level content directory where repos and packages exist. " \
                         "On a pulp server this is /var/lib/pulp/. On a CDS, please check /etc/pulp/cds.conf")
    parser.add_option("--migrate", dest="migrate", action="store_true", help="Perform migration on specified directory")
    parser.add_option("--test", dest="test", action="store_true", help="Test run the migration on specified directory without committing")

    parser.add_option("--validate", dest="validate", action="store_true", help="validate the migration")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="Verbose output to the console")

    (options, args) = parser.parse_args()
    if not options.migrate and not options.validate:
        print("Error: migrate or validate options required; see --help")
        sys.exit(-1)

    if not options.top_level_content_dir:
        print("Error: A valid directory path is required; see --help")
        sys.exit(-1)

    return options

def prompt_warning():
    print("\nWARNING: To avoid data corruption, please make sure pulp server or cds server is offline before running this script.")
    while 1:
        pulp_check = raw_input("\nContinue?(Y/N/Q):" )
        if pulp_check.strip().lower() == 'n':
            print("Pulp or CDS server is running, abort migration.")
            sys.exit(0)
        elif pulp_check.strip().lower() == 'q':
            print("Operation aborted upon user request.")
            sys.exit(0)
        elif pulp_check.strip().lower() == 'y':
            break
        else:
            continue

def main():
    global VERBOSE, TEST_RUN
    options = parse_args()
    top_level_content_dir = options.top_level_content_dir
    VERBOSE = options.verbose
    TEST_RUN = options.test
    if options.migrate:
        prompt_warning()
        migrate_summary = do_migrate(top_level_content_dir)
        print("Migrate Summary: \n")
        for repodir, summary in migrate_summary.items():
            print "Repo Directory: %s \n Migrated: %s, Skipped: %s\n" % (repodir, summary['migrated'], summary['skipped'])

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)


## TODO:
# - Add a check to see if pulp-server status and warn user or output a scary warning when script is invoked.
# - validation


