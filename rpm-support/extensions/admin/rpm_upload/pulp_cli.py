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

from gettext import gettext as _
import hashlib
import os
import rpm

from   pulp.client.extensions.extensions import PulpCliCommand
from   pulp_upload.pulp_cli import _upload_manager, _perform_upload

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'

RPMTAG_NOSOURCE = 1051

# -- framework hook -----------------------------------------------------------

def initialize(context):

    repo_section = context.cli.find_section('repo')
    uploads_section = repo_section.find_subsection('uploads')

    d = 'uploads one or more RPMs into a repository'
    uploads_section.add_command(CreateRpmCommand(context, 'rpm', _(d)))

# -- commands -----------------------------------------------------------------

class CreateRpmCommand(PulpCliCommand):
    """
    Handles initializing and uploading one or more RPMs.
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.create)
        self.context = context
        self.prompt = context.prompt

        d = 'identifies the repository the packages will be uploaded into'
        self.create_option('--repo-id', _(d), required=True)

        d = 'full path to the package to upload; may be specified multiple times ' \
            'for multiple files'
        self.create_option('--file', _(d), aliases=['-f'], allow_multiple=True, required=False)

        d = 'full path to a directory containing RPMs, all of which will be uploaded; ' \
            'may be specified multiple times for multiple directories'
        self.create_option('--dir', _(d), aliases=['-d'], allow_multiple=True, required=False)

        d = 'display extra information about the upload process'
        self.create_flag('-v', _(d))

    def create(self, **kwargs):
        self.prompt.render_title(_('RPM Upload'))

        repo_id = kwargs['repo-id']

        # Resolve the total list of RPMs to upload
        all_rpm_filenames = kwargs['file'] or []

        for d in kwargs['dir'] or []:
            # Sanity check
            if not os.path.exists(d):
                self.context.prompt.render_failure_message(_('Directory %(d)s does not exist') % {'d' : d})
                return os.EX_IOERR

            # Find all RPMs
            dir_rpms = [f for f in os.listdir(d) if f.endswith('.rpm')]
            for f in dir_rpms:
                full_filename = os.path.join(d, f)
                all_rpm_filenames.append(full_filename)

        # Make sure at least one RPM was found
        if len(all_rpm_filenames) is 0:
            self.context.prompt.render_failure_message(_('No RPMs selected for upload'))
            return os.EX_DATAERR

        # Integrity check on the total list of RPM files
        for f in all_rpm_filenames:
            if not os.path.exists(f) or not os.access(f, os.R_OK):
                self.context.prompt.render_failure_message(_('File %(f)s does not exist or could not be read') % {'f' : f})
                return os.EX_IOERR
            if not os.path.isfile(f):
                self.context.prompt.render_failure_message(_('%(f)s is not a file') % {'f' : f})
                return os.EX_IOERR

        # Display the list of found RPMs
        if kwargs['v']:
            self.prompt.write(_('RPMs to be uploaded:'))
            for r in all_rpm_filenames:
                self.prompt.write('  %s' % os.path.basename(r))
            self.prompt.render_spacer()

        # Extract the required metadata for each RPM
        self.prompt.write(_('Extracting necessary metdata for each RPM...'))
        bar = self.prompt.create_progress_bar()

        rpm_tuples = []
        for i, f in enumerate(all_rpm_filenames):
            bar.render(i+1, len(all_rpm_filenames), message=_('Analyzing: %(n)s') % {'n' : os.path.basename(f)})
            unit_key, metadata = _generate_rpm_data(f)
            rpm_tuples.append( (f, unit_key, metadata))

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Initialize all uploads
        upload_manager = _upload_manager(self.context)

        self.prompt.write(_('Creating upload requests on the server...'))
        bar = self.prompt.create_progress_bar()

        upload_ids = []
        for i, job in enumerate(rpm_tuples):
            bar.render(i+1, len(rpm_tuples), message=_('Initializing: %(n)s') % {'n' : os.path.basename(job[0])})
            upload_id = upload_manager.initialize_upload(job[0], repo_id, TYPE_RPM, job[1], job[2])
            upload_ids.append(upload_id)

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Start the upload process
        _perform_upload(self.context, upload_manager, upload_ids)

def _generate_rpm_data(rpm_filename):
    """
    For the given RPM, analyzes its metadata to generate the appropriate unit
    key and metadata fields, returning both to the caller.

    This is performed client side instead of in the importer to get around
    differences in RPMs between RHEL 5 and later versions of Fedora. We can't
    guarantee the server will be able to properly read the RPM so it is
    read client-side and the metadata passed in.

    The obvious caveat is that the format of the returned values must match
    what the importer would produce had this RPM been synchronized from an
    external source.

    @param rpm_filename: full path to the RPM to analyze
    @type  rpm_filename: str

    @return: tuple of unit key and unit metadata for the RPM
    @rtype:  tuple
    """

    # Expected metadata fields:
    # "vendor", "description", "buildhost", "license", "vendor", "requires", "provides", "relativepath", "filename"
    #
    # Expected unit key fields:
    # "name", "epoch", "version", "release", "arch", "checksumtype", "checksum"

    unit_key = dict()
    metadata = dict()

    # Read the RPM header attributes for use later
    ts = rpm.TransactionSet()
    ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
    fd = os.open(rpm_filename, os.O_RDONLY)
    headers = ts.hdrFromFdno(fd)
    os.close(fd)

    # -- Unit Key -----------------------

    # Checksum
    unit_key['checksumtype'] = 'sha256' # hardcoded to this in v1 so leaving this way for now

    m = hashlib.new(unit_key['checksumtype'])
    f = open(rpm_filename, 'r')
    while 1:
        buffer = f.read(65536)
        if not buffer:
            break
        m.update(buffer)
    f.close()

    unit_key['checksum'] = m.hexdigest()

    # Name, Version, Release, Epoch
    for k in ['name', 'version', 'release', 'epoch']:
        unit_key[k] = headers[k]

    #   Epoch munging
    if unit_key['epoch'] is None:
        unit_key['epoch'] = str(0)
    else:
        unit_key['epoch'] = str(unit_key['epoch'])

    # Arch
    if headers['sourcepackage']:
        if RPMTAG_NOSOURCE in headers.keys():
            unit_key['arch'] = 'nosrc'
        else:
            unit_key['arch'] = 'src'
    else:
        unit_key['arch'] = headers['arch']

    # -- Unit Metadata ------------------

    metadata['relativepath'] = os.path.basename(rpm_filename)
    metadata['filename'] = os.path.basename(rpm_filename)

    metadata['requires'] = [(r,) for r in headers['requires']]
    metadata['provides'] = [(p,) for p in headers['provides']]

    metadata['buildhost'] = headers['buildhost']
    metadata['license'] = headers['license']
    metadata['vendor'] = headers['vendor']
    metadata['description'] = headers['description']

    return unit_key, metadata
