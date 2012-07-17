# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import csv
import logging
import os
from gettext import gettext as _

from   pulp.client.extensions.extensions import PulpCliCommand
from   pulp_upload.pulp_cli import _upload_manager, _perform_upload

_LOG = logging.getLogger(__name__)

# -- constants ----------------------------------------------------------------
ERRATA_TYPE_ID="erratum"

# -- framework hook -----------------------------------------------------------

def initialize(context):

    repo_section = context.cli.find_section('repo')
    uploads_section = repo_section.find_subsection('uploads')

    d = 'create an erratum in a repository'
    uploads_section.add_command(CreateErratumCommand(context, 'errata', _(d)))

# -- commands -----------------------------------------------------------------

class CreateErratumCommand(PulpCliCommand):
    """
    Handles creation of an erratum
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.create)
        self.context = context
        self.prompt = context.prompt

        d = 'identifies the repository the erratum will be created in'
        self.create_option('--repo-id', _(d), required=True)

        d = 'id of this erratum'
        self.create_option('--erratum-id', _(d), aliases=['-i'], required=True)

        d = 'title of this erratum'
        self.create_option('--title', _(d), aliases=['-n'], required=True)

        d = 'description of this erratum'
        self.create_option('--description', _(d), aliases=['-d'], required=True)

        d = 'version of this erratum'
        self.create_option('--version', _(d), required=True)

        d = 'release of this erratum'
        self.create_option('--release', _(d), required=True)

        d = 'type of this erratum; examples: "bugzilla", "security", "enhancement"'
        self.create_option('--type', _(d), aliases=['-t'], required=True)

        d = 'status of this erratum; example "final"'
        self.create_option('--status', _(d), aliases=['-s'], required=True)

        d = 'when was this erratum last updated; expected format "YYYY-MM-DD HH:MM:SS"'
        self.create_option('--updated', _(d), aliases=['-u'], required=True)

        d = 'when was this erratum issued; expected format "YYYY-MM-DD HH:MM:SS"'
        self.create_option('--issued', _(d), required=True)

        d = 'path to a file containing reference information in comma separated value format. '\
            'An example of a reference would be information of a bugzilla issue. '\
            'Format for each entry is: "href,type,id,title"'
        self.create_option('--reference-csv', _(d), aliases=['-r'], required=False)

        d = 'path to a file containing package list information in comma separated value format. '\
            'Format for each entry is: "name,version,release,epoch,arch,filename,checksum,checksum_type,sourceurl"'
        self.create_option('--pkglist-csv', _(d), aliases=['-p'], required=True)

        d = 'who issued this erratum, sets \'from_str\' for this erratum; typically an email address'
        self.create_option('--from', _(d), required=True)

        d = 'pushcount for this erratum; an integer, defaults to 1'
        self.create_option('--pushcount', _(d), required=True, default=1)

        d = 'reboot-suggested for this erratum will be true if this flag is specified'
        self.create_flag('--reboot-suggested', _(d))

        d = 'severity of this erratum'
        self.create_option('--severity', _(d), required=False)

        d = 'rights for this erratum'
        self.create_option('--rights', _(d), required=False)

        d = 'summary for this erratum'
        self.create_option('--summary', _(d), required=False)

        d = 'solution for this erratum'
        self.create_option('--solution', _(d), required=False)

        d = 'display extra information about the creation process'
        self.create_flag('-v', _(d))

    def create(self, **kwargs):
        self.prompt.render_title(_('Erratum Creation'))

        repo_id = kwargs['repo-id']
        erratum_id = kwargs['erratum-id']
        title = kwargs['title']
        description = kwargs['description']
        version = kwargs['version']
        release = kwargs['release']
        errata_type = kwargs['type']
        status = kwargs['status']
        updated = kwargs['updated']
        issued = kwargs['issued']
        severity = kwargs['severity']
        rights = kwargs['rights']
        summary = kwargs['summary']
        solution = kwargs['solution']
        from_str = kwargs['from']
        try:
            pkglist = self.parse_package_csv(kwargs['pkglist-csv'], release)
            references = self.parse_reference_csv(kwargs['reference-csv'])
        except ParseException, e:
            self.context.prompt.render_failure_message(e.msg)
            return e.code
        try:
            pushcount = int(kwargs['pushcount'])
        except:
            msg = _("Error: Invalid pushcount [%s]; should be an integer ") % kwargs['pushcount']
            self.context.prompt.render_failure_message(msg)
            return os.EX_DATAERR
        reboot_suggested = kwargs['reboot-suggested']

        unit_key = {"id":erratum_id}
        metadata = {
                "title":title,
                "description":description,
                "version":version,
                "release":release,
                "type":errata_type,
                "status":status,
                "updated":updated,
                "issued":issued,
                "severity":severity,
                "references":references,
                "pkglist":pkglist,
                "rights":rights,
                "summary":summary,
                "solution":solution,
                "from_str":from_str,
                "pushcount":pushcount,
                "reboot_suggested":reboot_suggested,
                }

        if kwargs['v']:
            self.prompt.write(_('Erratum Details:'))

            combined = dict()
            combined.update(unit_key)
            combined.update(metadata)

            self.prompt.render_document(combined, order=['id', 'title', 'type', 'severity', 'status', 'solution', 'issued', 
                'updated', 'from_str', 'version', 'release', 'description', 'summary',], indent=2)
            self.prompt.render_spacer()

        # Initialize all uploads
        upload_manager = _upload_manager(self.context)
        upload_id = upload_manager.initialize_upload(None, repo_id, ERRATA_TYPE_ID, unit_key, metadata)
        _perform_upload(self.context, upload_manager, [upload_id])

    def parse_package_csv(self, csvfile, errata_release):
        if not os.path.exists(csvfile):
            msg = _("Package list CSV file [%s] not found") % (csvfile)
            raise ParseException(msg, os.EX_IOERR)
        plist = parse_csv(csvfile)
        pkgs = []
        for p in plist:
            if not len(p) == 9:
                msg = _("Bad format [%s] in csv [%s], %s arguments, expected 9") % (p, csvfile, len(p))
                raise ParseException(msg, os.EX_DATAERR)
            name,version,release,epoch,arch,filename,sums,type,sourceurl = p
            pdict = dict(name=name, version=version, release=release, 
                        epoch=epoch, arch=arch, filename=filename, sums=sums, type=type, src=sourceurl)
            pkgs.append(pdict)
        plistdict = {'packages' : pkgs,
                    'name'     : errata_release,
                    'short'    : ""}
                    #TODO:  Revist good way to specify name/short with CLI options/CSV
        return [plistdict]

    def parse_reference_csv(self, csvfile):
        if not os.path.exists(csvfile):
            msg = _("References CSV file [%s] not found") % (csvfile)
            raise ParseException(msg, os.EX_IOERR)
        references = []
        reflist = parse_csv(csvfile)
        for ref in reflist:
            if not len(ref) == 4:
                msg = _("Bad format [%s] in csv [%s], %s arguments, expected 4") % (ref, csvfile, len(ref))
                raise ParseException(msg, os.EX_DATAERR)
            href,type,id,title = ref
            refdict = dict(href=href,type=type,id=id,title=title)
            references.append(refdict)
        return references

# TODO:  Consider moving this to a common utility module
def parse_csv(filepath):
    in_file  = open(filepath, "rb")
    reader = csv.reader(in_file)
    lines = []
    for line in reader:
        if not len(line):
            continue
        line = [l.strip() for l in line]
        lines.append(line)
    in_file.close()
    return lines

class ParseException(Exception):
    def __init__(self, msg, code):
        super(Exception, self).__init__()
        self.msg = msg
        self.code = code

