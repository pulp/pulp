# Copyright (c) 2011 Red Hat, Inc.
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
import re

import shutil

from tito.tagger import VersionTagger
from tito.common import error_out

# changelog
BUGZILLA_REGEX = re.compile('([0-9]+\s+\-\s+)(.+)')
FEATURE_REGEX = re.compile('([\-]\s+)(.+)')
EMBEDDED_REGEX = re.compile('(\[\[)([^$]+)(\]\])')

# version and release
VERSION_REGEX = re.compile("^(version:\s*)(.+)$", re.IGNORECASE)
RELEASE_REGEX = re.compile("^(release:\s*)(.+)$", re.IGNORECASE)
VERSION_AND_RELEASE = 'PULP_VERSION_AND_RELEASE'
NL = '\n'


class PulpTagger(VersionTagger):
    """
    Pulp custom tagger.
    """

    def _bump_version(self):
        """
        Bump the version unless VERSION_AND_RELEASE specified
        in the environment.  When specified, both the version and
        release are forced as specified.
        VERSION_AND_RELEASE must be VR part of NEVRA
          Eg: 2.0.1-0.1.alpha
        """
        version = os.environ.get(VERSION_AND_RELEASE)
        if version:
            parts = version.rsplit('-', 1)
            if len(parts) != 2:
                error_out('"%s" not valid' % version)
            self.__update_spec(*parts)
            return version
        else:
            return VersionTagger._bump_version(self)

    def __update_spec(self, version, release):
        """
        Update the .spec file with specified version and release.
        @param version: The version
        @type version: str
        @param release: The release
        @type release: str
        """
        old = self.spec_file
        tmp = '.'.join((old, 'new'))
        r_fp = open(old)
        w_fp = open(tmp, 'w+')
        for line in r_fp.readlines():
            match = re.match(VERSION_REGEX, line)
            if match:
                line = ''.join((match.group(1), version, NL))
                w_fp.write(line)
                continue
            match = re.match(RELEASE_REGEX, line)
            if match:
                line = ''.join((match.group(1), release, NL))
                w_fp.write(line)
                continue
            w_fp.write(line)
        r_fp.close()
        w_fp.close()
        shutil.move(tmp, old)

    def _generate_default_changelog(self, last_tag):
        """
        Generate changelog.
        Strip git log entries not matching:
          "bugzilla - <comment>"
          "- <comment>"
          "[[ comment ]]"
        @param last_tag: Last git tag.
        @type last_tag: str
        @return: The generated changelog.
        @rtype: str
        """
        entry = []
        generated = VersionTagger._generate_default_changelog(self, last_tag)
        for line in generated.split('\n'):
            match = re.match(BUGZILLA_REGEX, line)
            if match:
                entry.append(line)
                continue
            match = re.match(FEATURE_REGEX, line)
            if match:
                entry.append(match.group(2))
                continue
            match = re.search(EMBEDDED_REGEX, line)
            if match:
                entry.append(match.group(2).strip())
                continue
        return '\n'.join(entry)
