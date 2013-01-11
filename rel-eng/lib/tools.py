# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import re

from tito.common import get_latest_tagged_version, increase_version

ALPHA_BETA_REGEX = re.compile('(alpha|beta)', re.IGNORECASE)


def next(project='pulp'):
    """
    Get the next (incremented) version or release.
    @param project: A pulp project name.
    @type project: str
    @return: The version-release
    @rtype: str
    """
    last_version = get_latest_tagged_version(project)
    return increment(last_version)


def increment(version):
    """
    Increment the specified version.
    @param version: A version: <version>-<release>
    @return: The incremented version
    """
    version, release = version.rsplit('-', 1)
    if re.search(ALPHA_BETA_REGEX, release):
        release = increase_version(release)
    else:
        version = increase_version(version)
    return '-'.join((version, release))


def main():
    if sys.argv[1] == 'next':
        print next()
        return
    if sys.argv[1] == 'increment':
        print increment(sys.argv[2])
        return

if __name__ == '__main__':
    main()