#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# -- imports ------------------------------------------------------------------

import fnmatch
import optparse
import os
import shutil
import subprocess

# -- constants/defaults -------------------------------------------------------

GUIDE_URL = 'https://fedorahosted.org/pulp/wiki/UserGuide'
TMP_DIR = '/tmp/pulp-ug-tmp'

# -- exceptions ---------------------------------------------------------------

class DownloadError(Exception):
    pass

# -- private ------------------------------------------------------------------

def _download_user_guide(dest_dir=TMP_DIR):
    '''
    Downloads the user guide from the wiki into the destination directory. If the directory
    does not exist it will be created. If it contains files, they will be erased.

    @param dest_dir: directory into which to save the user guide
    @type  dest_dir: string
    '''

    # Make sure the destination directory exists
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
            
    # Download the guide
    cmd = 'wget -r -np --convert-links --html-extension -e robots=off --domains fedorahosted.org -A \'UG*,UserGuide*\' %s' % GUIDE_URL

    p = subprocess.Popen(cmd, shell=True, cwd=dest_dir)
    p.wait()
#    if p.returncode != 0:
#        raise DownloadError('Error while downloading guide [%d]' % p.returncode)

    # For each file downloaded, do one of two things:
    # 1. Delete files with parameters; those are wiki links that are followed, we only want
    # normal HTML files
    # 2. Collapse the hierarchy into a single directory (dest_dir)
    html_dir = os.path.join(dest_dir, 'fedorahosted.org', 'pulp', 'wiki')
    for file in os.listdir(html_dir):
        if fnmatch.fnmatch(file, '*=*'):
            print('Deleting [%s]' % file)
            os.remove(os.path.join(html_dir, file))
        else:
            print('Moving [%s]' % file)
            os.rename(os.path.join(html_dir, file), os.path.join(dest_dir, file))

    # Last cleanup of the downloaded directory structure
    doomed = os.path.join(dest_dir, 'fedorahosted.org')
    print('Deleting [%s]' % doomed)
    shutil.rmtree(doomed)

def _rebrand_file(filename, use_php_imports=False):
    '''
    Strips the wiki header/footer off the downloaded HTML file and replaces it with
    a simple PHP import for the standard user guide.

    @param filename: full path name to the file to rebrand
    @type  filename: string
    '''

    # Read in the file
    fin = open(filename, 'r')
    contents = fin.read()
    fin.close()

    # Strip out the header fluff. The best approach I could find it to look for the
    # <div id="content" class="wiki"> tag and take everything after it.
    content_start = contents.index('<div id="wikipage">')

    # Strip out the footer fluff. This one is a bit trickier. I think we can rely on the tag:
    #   <script type="text/javascript">searchHighlight()</script>
    # Ya, so we can't rely on that anymore. Trying this on Dec 15, 2011, it looks
    # like something changed on trac's end and that string is no longer present.
    # Let's try:
    #
    content_end = contents.index('<div id="altlinks">')

    # They screwed with the wiki format adding that "Last modified to the top.
    # We want to strip that out but still need a header <div> tag for the wiki
    # content itself, so we add it back here. I feel like I'm unleashing a great
    # evil upon the codebase with this hack.
    clean_contents = '<div id="content" class="wiki">' + contents[content_start:content_end]

    # Overwrite the dirty ones, inserting the PHP imports
    fout = open(filename, 'w')

    if use_php_imports:
        fout.write('<?php @ require_once (\'header.inc\'); ?>\n')
        fout.write(clean_contents)
        fout.write('<?php @ require_once (\'footer.inc\'); ?>\n')
    else:
        header_file = open('../pulpproject.org/ug/header.inc')
        header = header_file.read()
        header_file.close()

        footer_file = open('../pulpproject.org/ug/footer.inc')
        footer = footer_file.read()
        footer_file.close()

        fout.write(header)
        fout.write('\n')
        fout.write(clean_contents)
        fout.write('\n')
        fout.write(footer)

    fout.close()

def _rebrand_all(source_dir):
    '''
    Rebrands all downloaded user guide files in the given directory.

    @param source_dir: directory in which the user guide files were downloaded
    @type  source_dir: string
    '''

    for file in os.listdir(source_dir):
        if fnmatch.fnmatch(file, 'UG*.html') or fnmatch.fnmatch(file, 'UserGuide*.html'):
            print('Rebranding [%s]' % file)
            _rebrand_file(os.path.join(source_dir, file))

def _make_index(source_dir):
    '''
    Creates index.php for the user guide.

    @param source_dir: directory in which the user guide files were downloaded
    @type  source_dir: string
    '''

    user_guide = os.path.join(source_dir, 'UserGuide.html')
    index = os.path.join(source_dir, 'index.html')

    # Delete the index.html if it already exists
    if os.path.exists(index):
        os.remove(index)

    shutil.copy(user_guide, index)

if __name__ == '__main__':

    parser = optparse.OptionParser()
    parser.add_option('-d', dest='dest_dir', action='store',
                      help='full path to save the generated HTML files')

    options, args = parser.parse_args()

    dest_dir = options.dest_dir or TMP_DIR
    print(options.dest_dir)
    
    _download_user_guide(dest_dir)
    _rebrand_all(dest_dir)
    _make_index(dest_dir)

    print('HTML User Guide can be found at [%s]' % dest_dir)
    