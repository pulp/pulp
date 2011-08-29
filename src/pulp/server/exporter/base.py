# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
import os
import sys
import logging
import shutil
import string
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server.db import connection
from pulp.server.api.repo import RepoApi

log = logging.getLogger(__name__)

class BaseExporter(object):
    """
     Base Exporter module with common methods
    """
    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None, force=False):
        """
        initialize exporter
        @param repoid: repository Id
        @type repoid: string
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        @param force: force certain operations while exporting content
        @type force: boolean
        """
        self.repoid = repoid
        self.target_dir = target_dir
        self.start_date = start_date
        self.end_date = end_date
        self.force = force
        self.progress = {
            'status': 'running',
            'count_total': 0,
            'count_remaining': 0,
            'num_error': 0,
            'num_success': 0,
            'errors': [],
        }
        self.init_pulp()
        
    def init_pulp(self):
        """
         Setup pulp server and DB connection and initialize content apis
        """
        # initialize DB
        connection.initialize()
        # initialize pulp components
        self.errata_api = ErrataApi()
        self.repo_api = RepoApi()
        self.package_api = PackageApi()
        self.distribution_api = DistributionApi()

    def get_repository(self):
        """
        Lookup repository id and get the repo object from pulp
        @rtype: object
        @return: Repository object
        """
        repo = self.repo_api.repository(self.repoid)
        if not repo:
            raise Exception("Repository id %s not found" % self.repoid)
        if repo['sync_in_progress']:
            raise Exception("Repository [%s] sync is in progress; cannot perform export" % self.repoid)
        return repo
    
    def export(self):
        """
         Implemented in the subclass
        """
        raise NotImplementedError()

    def validate_target_path(self):
        """
        Validate target directory path:
          * If path doesn't exists, create one
          * If path exists and not empty; if forced remove and create a fresh one.
        """
        if not os.path.exists(self.target_dir):
            log.info("Path %s does not exists; creating" % self.target_dir)
            os.mkdir(self.target_dir)
        if os.listdir(self.target_dir) and self.force:
            log.info("Target directory has content and force is set; cleaning up the directory for new export.")
            shutil.rmtree(self.target_dir)
            os.mkdir(self.target_dir)

    def get_report(self):
        raise NotImplementedError()

    def write(self, current, prev=None):
        """ Use information of number of columns to guess if the terminal
        will wrap the text, at which point we need to add an extra 'backup line'
        """
        lines = 0
        if prev:
            lines = prev.count('\n')
            if prev.rstrip(' ')[-1] != '\n':
                lines += 1 # Compensate for the newline we inject in this method at end
            lines += self.count_linewraps(prev)
        # Move up 'lines' lines and move cursor to left
        sys.stdout.write('\033[%sF' % (lines))
        sys.stdout.write('\033[J')  # Clear screen cursor down
        sys.stdout.write(current)
        # In order for this to work in various situations
        # We are requiring a new line to be entered at the end of
        # the current string being printed.
        if current.rstrip(' ')[-1] != '\n':
            sys.stdout.write("\n")
        sys.stdout.flush()

    def terminal_size(self):
        import fcntl, termios, struct
        h, w, hp, wp = struct.unpack('HHHH',
            fcntl.ioctl(0, termios.TIOCGWINSZ,
                struct.pack('HHHH', 0, 0, 0, 0)))
        return w, h

    def count_linewraps(self, data):
        linewraps = 0
        width = height = 0
        try:
            width, height = self.terminal_size()
        except:
            # Unable to query terminal for size
            # so default to 0 and skip this
            # functionality
            return 0
        for line in data.split('\n'):
            count = 0
            for d in line:
                if d in string.printable:
                    count += 1
            linewraps += count / width
        return linewraps