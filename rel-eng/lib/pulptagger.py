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

import re
from tito.common import get_latest_tagged_version
from tito.tagger import VersionTagger

MASTER_PACKAGE = 'pulp'
BUGZILLA_REGEX = re.compile('([0-9]+\s+\-\s+)(.+)')
FEATURE_REGEX = re.compile('([\-]\s+)(.+)')


class PulpTagger(VersionTagger):
    """
    Pulp custom tagger.
    """

    def _generate_default_changelog(self, last_tag):
        """
        Generate changelog.
        Strip git log entries not matching:
          "bugzilla - <comment>"
          "- <comment>"
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
        return '\n'.join(entry)
            

class SlavedTagger(PulpTagger):
    """
    Slaved tagger used for sub-projects.
    Used to I{slave} version from the master project.
    """
    
    def run(self, options):
        """
        Tag using the (platform) project as master for the version.
        @param options: tagging options.
        @type options: options
        """
        tag = get_latest_tagged_version(MASTER_PACKAGE)
        options.use_version = tag.split('-', 1)[0]
        PulpTagger.run(self, options)

    def _bump_version(self):
        """
        Force options we need.
        """
        return VersionTagger._bump_version(self, False, False, True)
