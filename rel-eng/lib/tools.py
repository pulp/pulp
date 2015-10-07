import re
import sys

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
