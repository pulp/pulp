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
import math
import string
import commands
import datetime
import tempfile
from stat import ST_SIZE
from logging import getLogger

log = getLogger(__name__)

VALID_IMAGE_TYPES = {
    'cd' : 630 * 1024 * 1024,
    'dvd': 4380 * 1024 * 1024,
    #add 'bluray'
}

class GenerateIsos(object):
    """
     Generate iso image files for the exported content.
    """
    def __init__(self, target_directory, output_directory, prefix="pulp-repos", progress=None):
        """
        generate isos
        @param target_directory: target content directory to be wrapped into isos
        @type target_directory: str
        @param output_directory: destination directory where isos are written
        @type output_directory: str
        @param prefix: prefix for the iso names; usually includes a repo id
        @type prefix: str
        @param progress: progress info object to report iso generation
        @type progress: dict
        """
        self.target_dir = target_directory
        self.output_dir = output_directory
        self.progress = progress
        self.prefix = prefix

    def get_image_type_size(self, total_size):
        if total_size < VALID_IMAGE_TYPES['cd']:
            return VALID_IMAGE_TYPES['cd']
        else:
            return VALID_IMAGE_TYPES['dvd']

    def run(self, progress_callback=None):
        """
         get the filelists with sizes and perform iso creation
        """
        # get size and filelists of the target directory
        filelist, total_dir_size = list_dir_with_size(self.target_dir)
        log.debug("Total target directory size to create isos %s" % total_dir_size)
        # media size
        img_size = self.get_image_type_size(total_dir_size)
        # compute no.of images it takes per media image size
        imgcount = int(math.ceil(total_dir_size/float(img_size)))
        # get the filelists per image by size
        imgs = self.compute_image_files(filelist, imgcount, img_size)
        for i in range(imgcount):
            msg = "Generating iso images for exported content (%s/%s)" % (i+1, imgcount)
            log.info(msg)
            if progress_callback is not None:
                self.progress["step"] = msg
                progress_callback(self.progress)
            grafts = self.__grafts(imgs[i])
            pathfiles_fd, pathfiles = self.__pathspecs(grafts)
            filename = get_iso_filename(self.output_dir, self.prefix, i+1)
            cmd = self.get_mkisofs_template() % (string.join([pathfiles]), filename)
            status, out = run_command(cmd)
            if status != 0:
                log.error("Error creating iso %s" % filename)
            log.info("successfully created iso %s" % filename) 
	    log.debug("status code: %s; output: %s" % (status, out))
            os.unlink(pathfiles)
        return self.progress

    def compute_image_files(self, filelist, imgcount, imgsize):
        """
        compute file lists to be written to each media image
        by comparing the cumulative size
        @rtype: list
        @return: list of files to be written to an iso image
        """
        imgs = []
        for i in range(imgcount):
            img = []
            sz = 0
            for filepath, size in filelist:
                if sz + size > imgsize:
                    # slice the list to process new
                    filelist = filelist[filelist.index((filepath, size)):]
                    break
                if filepath not in img:
                    img.append(filepath)
                sz += size
            imgs.append(img)
        return imgs

    def get_mkisofs_template(self):
        """
         template mkisofs command to be filled and executed
        """
        return "mkisofs -r -J -D -graft-points -path-list %s -o %s"

    def __grafts(self, img_files):
        grafts = []
        for f in img_files:
            relpath = os.path.dirname(f[len(self.target_dir):])
            grafts.append("%s/=%s" % (relpath, f))
        return grafts

    def __pathspecs(self, grafts):
        pathfiles_fd, pathfiles = tempfile.mkstemp(dir = '/tmp', prefix = 'pulpiso-')
        for graft in grafts:
            os.write(pathfiles_fd, graft)
            os.write(pathfiles_fd, "\n")
        os.close(pathfiles_fd)
        return pathfiles_fd, pathfiles

def get_iso_filename(output_dir, prefix, count):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    ctime = datetime.datetime.now()
    return "%s/%s-%s-%02d.iso" % (output_dir, prefix, ctime.strftime("%Y%m%d"), count)

def run_command(cmd):
    """
    Run a command and log the output
    """
    log.info("executing command %s" % cmd)
    status, out = commands.getstatusoutput(cmd)
    return status, out

def list_dir_with_size(top_directory):
    """
     Get the target directory filepaths and sizes
     with cumulative dir size
    """
    total_size = 0
    top_directory = os.path.abspath(os.path.normpath(top_directory))
    if not os.access(top_directory, os.R_OK | os.X_OK):
        raise Exception("Cannot read from directory %s" % top_directory)
    if not os.path.isdir(top_directory):
        raise Exception("%s not a directory" % top_directory)
    filelist = []
    for root, dirs, files in os.walk(top_directory):
        for file in files:
            fpath = "%s/%s" % (root, file)
            size = os.stat(fpath)[ST_SIZE]
            filelist.append((fpath, size))
            total_size += size
    return filelist, total_size

def generate_checksum_manifest(iso_dir_path):
    pass

if __name__== '__main__':
    import sys
    if not len(sys.argv) == 3:
        print "USAGE: python make_iso.py <target_dir> <output_dir> "
        sys.exit(0)
    target_dir = sys.argv[1]
    output_dir = sys.argv[2]
    print target_dir, output_dir
    isogen = GenerateIsos(target_dir, output_directory=output_dir)
    isogen.run()
