"""
Sync Yum repository content.

Based heavily on action_reposync.py from Cobbler.
See: http://cobbler.et.redhat.com/

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
Devan Goodwin <dgoodwin@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import time
import pulp.sub_process
import sys

#from cexceptions import *

#from rhpl.translate import _, N_, textdomain, utf8

REPOSYNC_PATH = "/usr/bin/reposync"
REPO_STORAGE_DIR = "/tmp/repos/"
HTTP_SERVER = "localhost"
HTTP_PORT = "80"

def remove_yum_olddata(path):
    """
    Delete .olddata files that might be present from a failed run
    of createrepo.
    """
    trythese = [
        ".olddata",
        ".repodata/.olddata",
        "repodata/.oldata",
        "repodata/repodata"
    ]
    for pathseg in trythese:
        olddata = os.path.join(path, pathseg)
        if os.path.exists(olddata):
            print "- removing: %s" % olddata
            shutil.rmtree(olddata, ignore_errors=False, onerror=None)

class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, repos):
        """
        Create a RepoSync action with a list of repositories to be synced.
        """
        self.repos = repos

    def run(self):
        """
        Syncs the current repo configuration file with the filesystem.
        """

        for repo in self.repos:

            repo_path = os.path.join(REPO_STORAGE_DIR, 
                repo.name)
            print "repo_path = %s" % repo_path

            if not os.path.isdir(repo_path):
                os.makedirs(repo_path)                                        
            
            # TODO: Add support for rsync/rhn URLs?
            self.do_reposync(repo)

            self.update_permissions(repo_path)

        return True
    
    # TODO: Resurrect this when the time comes to support rsync URLs.
    #def __is_rsync_url(self, url):
    #    lower = url.lower()
    #    if lower.startswith("http://") or lower.startswith("ftp://") or \
    #        lower.startswith("rhn://"):
    #        return False
    #    else:
    #        return True

    def do_reposync(self, repo):
        """
        Handle copying of http:// and ftp:// repos.
        """

        # warn about not having yum-utils.  We don't want to require it in the 
        # package because RHEL4 and RHEL5U0 don't have it.
        if not os.path.exists(REPOSYNC_PATH):
            raise Exception(
                "no /usr/bin/reposync found, please install yum-utils")

        cmds = []                 # queues up commands to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        store_path = REPO_STORAGE_DIR
        dest_path = os.path.join(REPO_STORAGE_DIR, repo.name)
        # Origin dir stores the source yum repo config files:
        temp_path = os.path.join(REPO_STORAGE_DIR, ".origin") 
        if not os.path.isdir(temp_path):
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # this is the simple non-RHN case.
        # create the config file that yum will use for the copying

        temp_file = self.create_local_file(repo, temp_path, output=False)

        if not has_rpm_list:
            # If we have not requested only certain RPMs, use reposync:
            cmd = "/usr/bin/reposync " + \
                "--config=%s --repoid=%s --download_path=%s" % \
                    (temp_file, repo.name, store_path)
            if repo.arch != "":
                cmd = "%s -a %s" % (cmd, "x86_64")
                
            print _("- %s") % cmd
            cmds.append(cmd)
        
        # NOTE: "else" clause handling syncing of only certain RPMs in the
        # cobbler source was removed here. May need to re-add if this
        # functionality is needed later on.

        for cmd in cmds:
            rc = pulp.sub_process.call(cmd, shell=True)
            if rc !=0:
                raise Exception("reposync failed")

        # now run createrepo to rebuild the index
        os.path.walk(dest_path, self.createrepo_walker, repo)

        # create the config file the hosts will use to access the repository.
        self.create_local_file(repo, dest_path)
 
    def create_local_file(self, repo, dest_path, output=True):
        """
        Two uses:
        (A) output=True, Create local files that can be used with yum on 
        provisioned clients to make use of this mirror.

        (B) output=False, Create a temporary file for yum to feed into yum 
        for mirroring
        """
    
        # the output case will generate repo configuration files which are 
        # usable for the installed systems.  They need to be made compatible 
        # with --server-override which means they are actually templates, 
        # which need to be rendered by a cobbler-sync on per profile/system 
        #basis.

        if output:
            fname = os.path.join(dest_path,"config.repo")
        else:
            fname = os.path.join(dest_path, "%s.repo" % repo.name)
        print _("- creating: %s") % fname
        config_file = open(fname, "w+")
        config_file.write("[%s]\n" % repo.name)
        config_file.write("name=%s\n" % repo.name)
        if output:
            line = "baseurl=http://${server}/cobbler/repo_mirror/%s\n" % \
                (repo.name)
            config_file.write(line)
            # user may have options specific to certain yum plugins
            # add them to the file
            #for x in repo.yumopts:
            #    config_file.write("%s=%s\n" % (x, repo.yumopts[x]))
        else:
            line = "baseurl=%s\n" % repo.url
            http_server = "%s:%s" % (HTTP_SERVER, HTTP_PORT)
            line = line.replace("@@server@@", http_server)
            config_file.write(line)
        config_file.write("enabled=1\n")
        config_file.write("priority=%s\n" % repo.priority)
        config_file.write("gpgcheck=0\n")
        config_file.close()
        return fname 

    def createrepo_walker(self, repo, dirname, fnames):
        """
        Used to run createrepo on a copied mirror.
        """
        remove_yum_olddata(dirname)
        try:
            cmd = "createrepo -c cache %s" % (dirname)
            print "- %s" % cmd
            pulp.sub_process.call(cmd, shell=True)
        except:
            print "- createrepo failed.  Is it installed?"
        del fnames[:] # we're in the right place

    def update_permissions(self, repo_path):
        """
        Verifies that permissions and contexts after an rsync are as expected.
        Sending proper rsync flags should prevent the need for this, though 
        this is largely a safeguard.
        """
        # all_path = os.path.join(repo_path, "*")
        cmd1 = "chown -R root:apache %s" % repo_path
        pulp.sub_process.call(cmd1, shell=True)

        cmd2 = "chmod -R 755 %s" % repo_path
        pulp.sub_process.call(cmd2, shell=True)

        getenforce = "/usr/sbin/getenforce"
        if os.path.exists(getenforce):
            data = pulp.sub_process.Popen(getenforce, shell=True, 
                stdout=pulp.sub_process.PIPE).communicate()[0]
            if data.lower().find("disabled") == -1:
                cmd3 = "chcon --reference /var/www %s" % repo_path
                sub_process.call(cmd3, shell=True)
            
