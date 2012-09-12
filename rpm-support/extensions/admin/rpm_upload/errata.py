# Copyright (c) 2012 Red Hat, Inc.
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
from gettext import gettext as _
import os

from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliOption, PulpCliFlag
from pulp_rpm.common.ids import TYPE_ID_ERRATA


NAME = 'erratum'
DESC = _('creates a new erratum')

d = _('id of the erratum to create')
OPT_ERRATUM_ID = PulpCliOption('--erratum_id', d, aliases=['-i'], required=True)

d = _('title of the erratum')
OPT_TITLE = PulpCliOption('--title', d, aliases=['-n'], required=True)

d = _('description of the erratum')
OPT_DESC = PulpCliOption('--description', d, aliases=['-d'], required=True)

d = _('version of the erratum')
OPT_VERSION = PulpCliOption('--version', d, required=True)

d = _('release of the erratum')
OPT_RELEASE = PulpCliOption('--release', d, required=True)

d = _('type of the erratum; examples: "bugzilla", "security", "enhancement"')
OPT_TYPE = PulpCliOption('--type', d, aliases=['-t'], required=True)

d = _('status of the erratum; examples: "final"')
OPT_STATUS = PulpCliOption('--status', d, aliases=['-s'], required=True)

d = _('timestamp the erratum was last updated; expected format "YYYY-MM-DD HH:MM:SS"')
OPT_UPDATED = PulpCliOption('--updated', d, aliases=['-u'], required=True)

d = _('timestamp the erratum was issued; expected format "YYYY-MM-DD HH:MM:SS"')
OPT_ISSUED = PulpCliOption('--issued', d, required=True)

d = _('path to a CSV file containing reference information. '
      'An example of a reference would be information of a bugzilla issue. '
      'Format for each entry is: "href,type,id,title"')
OPT_REFERENCE = PulpCliOption('--reference-csv', d, aliases=['-r'], required=False)

d = _('path to a CSV file containing package list information. '
      'Format for each entry is: "name,version,release,epoch,arch,filename,checksum,checksum_type,sourceurl"')
OPT_PKG_LIST = PulpCliOption('--pkglist-csv', d, aliases=['-p'], required=True)

d = _('erratum issuer, used in the \'from_str\' for the erratum; typically an email address')
OPT_FROM = PulpCliOption('--from', d, required=True)

d = _('pushcount for the erratum; an integer, defaults to 1 if unspecified')
OPT_PUSHCOUNT = PulpCliOption('--pushcount', d, required=False, default=1)

d = _('if specified, the erratum will be marked as \'reboot-suggested\'')
OPT_REBOOT = PulpCliFlag('--reboot-suggested', d)

d = _('severity of the erratum')
OPT_SEVERITY = PulpCliOption('--severity', d, required=False)

d = _('rights for the erratum')
OPT_RIGHTS = PulpCliOption('--rights', d, required=False)

d = _('summary for the erratum')
OPT_SUMMARY = PulpCliOption('--summary', d, required=False)

d = _('solution for the erratum')
OPT_SOLUTION = PulpCliOption('--solution', d, required=False)


class CreateErratumCommand(UploadCommand):
    """
    Handles creation of an erratum.
    """

    def __init__(self, context, upload_manager, name=NAME, description=DESC):
        super(CreateErratumCommand, self).__init__(context, upload_manager,
                                                   name=name, description=description,
                                                   upload_files=False)

        self.add_option(OPT_ERRATUM_ID)
        self.add_option(OPT_TITLE)
        self.add_option(OPT_DESC)
        self.add_option(OPT_VERSION)
        self.add_option(OPT_RELEASE)
        self.add_option(OPT_TYPE)
        self.add_option(OPT_STATUS)
        self.add_option(OPT_UPDATED)
        self.add_option(OPT_ISSUED)
        self.add_option(OPT_REFERENCE)
        self.add_option(OPT_PKG_LIST)
        self.add_option(OPT_FROM)
        self.add_option(OPT_PUSHCOUNT)
        self.add_option(OPT_REBOOT)
        self.add_option(OPT_SEVERITY)
        self.add_option(OPT_RIGHTS)
        self.add_option(OPT_SUMMARY)
        self.add_option(OPT_SOLUTION)

    def determine_type_id(self, filename, **kwargs):
        return TYPE_ID_ERRATA

    def generate_unit_key(self, filename, **kwargs):
        erratum_id = kwargs[OPT_ERRATUM_ID.keyword]
        unit_key = {'id' : erratum_id}
        return unit_key

    def generate_metadata(self, filename, **kwargs):
        title = kwargs[OPT_TITLE.keyword]
        description = kwargs[OPT_DESC.keyword]
        version = kwargs[OPT_VERSION.keyword]
        release = kwargs[OPT_RELEASE.keyword]
        errata_type = kwargs[OPT_TYPE.keyword]
        status = kwargs[OPT_STATUS.keyword]
        updated = kwargs[OPT_UPDATED.keyword]
        issued = kwargs[OPT_ISSUED.keyword]
        severity = kwargs[OPT_SEVERITY.keyword]
        rights = kwargs[OPT_RIGHTS.keyword]
        summary = kwargs[OPT_SUMMARY.keyword]
        solution = kwargs[OPT_SOLUTION.keyword]
        from_str = kwargs[OPT_FROM.keyword]
        reboot_suggested = kwargs[OPT_REBOOT.keyword]

        references = []
        try:
            pkg_csv_file = kwargs[OPT_PKG_LIST.keyword]
            pkglist = self.parse_package_csv(pkg_csv_file, release)
            ref_csv_file = kwargs[OPT_REFERENCE.keyword]
            if ref_csv_file:
                references = self.parse_reference_csv(ref_csv_file)
        except ParseException, e:
            self.context.prompt.render_failure_message(e.msg)
            return e.code
        try:
            pushcount = int(kwargs[OPT_PUSHCOUNT.keyword])
        except Exception:
            msg = _("Error: Invalid pushcount [%(p)s]; should be an integer ") % {'p' : kwargs[OPT_PUSHCOUNT.keyword]}
            self.context.prompt.render_failure_message(msg)
            return os.EX_DATAERR

        metadata = {
            'title' : title,
            'description' : description,
            'version' : version,
            'release' : release,
            'type' : errata_type,
            'status' : status,
            'updated' : updated,
            'issued' : issued,
            'severity' : severity,
            'references' : references,
            'pkglist' : pkglist,
            'rights' : rights,
            'summary' : summary,
            'solution' : solution,
            'from_str' : from_str,
            'pushcount' : pushcount,
            'reboot_suggested' : reboot_suggested,
        }

        return metadata

    def parse_package_csv(self, csvfile, errata_release):
        if not csvfile or not os.path.exists(csvfile):
            msg = _('Package list CSV file [%(f)s] not found') % {'f' : csvfile}
            raise ParseException(msg, os.EX_IOERR)
        plist = parse_csv(csvfile)
        pkgs = []
        for p in plist:
            if not len(p) == 9:
                data = {'f' : p, 'c' : csvfile, 'n' : len(p)}
                msg = _('Bad format [%(f)s] in csv [%(c)s], %(n)s arguments, expected 9') % data
                raise ParseException(msg, os.EX_DATAERR)
            name,version,release,epoch,arch,filename,sums,ptype,sourceurl = p
            pdict = dict(name=name, version=version, release=release,
                         epoch=epoch, arch=arch, filename=filename, sums=sums, type=ptype, src=sourceurl)
            pkgs.append(pdict)
        plistdict = {'packages' : pkgs,
                     'name'     : errata_release,
                     'short'    : ""}
        #TODO:  Revist good way to specify name/short with CLI options/CSV
        return [plistdict]

    def parse_reference_csv(self, csvfile):
        if not csvfile or not os.path.exists(csvfile):
            msg = _('References CSV file [%(f)s] not found') % {'f' : csvfile}
            raise ParseException(msg, os.EX_IOERR)
        references = []
        reflist = parse_csv(csvfile)
        for ref in reflist:
            if not len(ref) == 4:
                data = {'f' : ref, 'c' : csvfile, 'n' : len(ref)}
                msg = _("Bad format [%(f)s] in csv [%(c)s], %(n)s arguments, expected 4") % data
                raise ParseException(msg, os.EX_DATAERR)
            href,csvtype,id,title = ref
            refdict = dict(href=href,type=csvtype,id=id,title=title)
            references.append(refdict)
        return references

# -- utilities ----------------------------------------------------------------

class ParseException(Exception):
    def __init__(self, msg, code):
        super(Exception, self).__init__()
        self.msg = msg
        self.code = code


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
