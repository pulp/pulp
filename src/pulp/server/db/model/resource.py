# -*- coding: utf-8 -*-

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

import datetime
import urlparse

from pulp.common import dateutils
from pulp.common.util import encode_unicode
from pulp.server.db.model.base import Model
from pulp.server.exceptions import PulpException
from pulp.server.tasking.scheduler import IntervalScheduler

# consumer models -------------------------------------------------------------

class Consumer(Model):

    collection_name = 'consumers'
    unique_indices = ('id',)
    search_indices = ('package_profile.name', 'repoids', 'key_value_pairs',
                      'consumer_id', 'type_name', 'timestamp')

    def __init__(self, id, description, key_value_pairs={}):
        self._id = id
        self.id = id
        self.description = description
        self.capabilities = {}
        self.certificate = None
        self.package_profile = []
        self.repoids = []
        self.key_value_pairs = key_value_pairs


class ConsumerGroup(Model):

    collection_name = 'consumergroups'
    search_indices = ('consumerids',)

    def __init__(self, id, description=None, consumerids=[], key_value_pairs={}):
        self._id = id
        self.id = id
        self.description = description
        self.consumerids = consumerids
        self.key_value_pairs = key_value_pairs


class ConsumerHistoryEvent(Model):

    collection_name = 'consumer_history'

    def __init__(self, consumer_id, originator, type_name, details):
        Model.__init__(self)
        self.consumer_id = consumer_id
        self.originator = originator
        self.type_name = type_name
        self.details = details
        now = datetime.datetime.now(dateutils.utc_tz())
        self.timestamp = dateutils.format_iso8601_datetime(now)

# distribution model ----------------------------------------------------------

class Distribution(Model):
    """
     Distribution Model to represent kickstart trees
    """
    collection_name = 'distribution'
    search_indices = ('files', 'family', 'variant', 'version', 'arch', 'relativepath', 'repoids')

    def __init__(self, id, description, relativepath, family=None, variant=None, version=None, timestamp=None, files=[], arch=None, repoids=[]):
        Model.__init__(self)
        self._id = id
        self.id = id
        self.description = description
        self.files = files
        self.arch = arch
        self.relativepath = relativepath
        self.family = family
        self.variant = variant
        self.version = version
        self.repoids = repoids
        if timestamp:
            self.timestamp = dateutils.format_iso8601_datetime(timestamp)
        else:
            self.timestamp = dateutils.format_iso8601_datetime(datetime.datetime.now(dateutils.utc_tz()))


# errata model ----------------------------------------------------------------

class Errata(Model):
    """
    Errata model to represent software updates
    maps to yum.update_md.UpdateNotice fields
    """

    collection_name = 'errata'
    search_indices = ('title', 'version', 'release', 'type',
                      'status', 'updated', 'issued', 'pushcount', 'from_str',
                      'reboot_suggested')

    def __init__(self, id, title, description, version, release, type, status=u"",
            updated=u"", issued=u"", pushcount=1, from_str=u"",
            reboot_suggested=False, references=[], pkglist=[], severity=u"",
            rights=u"", summary=u"", solution=u"", repo_defined=False, immutable=False, repoids=[]):
        self._id = id
        self.id = id
        self.title = title
        self.description = description
        self.version = version
        self.release = release
        self.type = type
        self.status = status
        self.updated = updated
        self.issued = issued
        if pushcount:
            self.pushcount = int(pushcount)
        else:
            self.pushcount = 1
        self.from_str = from_str
        self.reboot_suggested = reboot_suggested
        self.references = references
        self.pkglist = pkglist
        self.rights = rights
        self.severity = severity
        self.repo_defined = repo_defined
        self.summary = summary
        self.solution = solution
        self.immutable = immutable
        self.repoids = repoids

# package models --------------------------------------------------------------

class Package(Model):

    collection_name = 'packages'
    unique_indices = (('name', 'epoch', 'version', 'release', 'arch',
                        'filename', 'checksum'),)
    search_indices = ('name', 'filename', 'checksum', 'epoch', 'version',
                      'release', 'arch', 'repoids')

    def __init__(self, name, epoch, version, release, arch, description,
            checksum_type, checksum, filename, vendor=None, size=None,
            buildhost=u"", license=u"", group=u"", repo_defined=False, repoids=[]):
        Model.__init__(self)
        # ID is initialized in Model.__init__()
        self.name = name
        self.epoch = str(epoch)
        self.version = version
        self.release = release
        self.arch = arch
        self.description = description
        self.vendor = vendor
        self.filename = filename
        self.checksum = {checksum_type: checksum}
        self.download_url = None
        self.repo_defined = repo_defined
        # Add gpg keys
        self.requires = []
        self.provides = []
        self.size = size # payload size
        self.buildhost = buildhost
        self.license = license
        self.group = group
        self.repoids = repoids


class PackageGroup(Model):
    """
    Class represents a yum.comps.Group
    """
    def __init__(self, id, name, description, user_visible=True,
            display_order=1024, default=True, langonly=None,
            immutable=False, repo_defined=False):
        self._id = id
        self.id = id
        self.name = name
        self.description = description
        self.user_visible = user_visible
        self.display_order = display_order
        self.default = default
        self.langonly = langonly
        self.mandatory_package_names = []
        self.optional_package_names = []
        self.default_package_names = []
        self.conditional_package_names = {}
        self.translated_name = {}
        self.translated_description = {}
        self.immutable = immutable
        self.repo_defined = repo_defined


class PackageGroupCategory(Model):

    def __init__(self, id, name, description, display_order=99,
            immutable=False, repo_defined=False):
        self._id = id
        self.id = id
        self.name = name
        self.description = description
        self.display_order = display_order
        self.translated_name = {}
        self.translated_description = {}
        self.packagegroupids = []
        self.immutable = immutable
        self.repo_defined = repo_defined

class File(Model):
    """
    Class represents a file types other than rpm. Eg: *.iso *.txt
    """

    collection_name = 'file'
    unique_indices = (('filename', 'checksum'),)

    def __init__(self, filename, checksum_type,
                 checksum, size, description=None, repo_defined=False):
        Model.__init__(self)
        # ID is initialized in Model.__init__()
        self.filename = filename
        self.description = description
        self.checksum = {checksum_type: checksum}
        self.size = None
        if size:
            self.size = int(size)
        self.download_url = None
        self.repo_defined = repo_defined

class Filter(Model):
    """
    Class represents a blacklist or whitelist filter that can be applied when syncing a local repository
    """
    collection_name = 'filters'
    unique_indices = ('id',)
    search_indices = ('type')

    def __init__(self, id, type, description=None, package_list=None):
        self._id = id
        self.id = id
        self.description = description
        self.type = type
        if not package_list:
            package_list = []
        self.package_list = package_list

# repository models -----------------------------------------------------------

class Repo(Model):

    SUPPORTED_ARCHS = ['noarch', 'i386', 'i686', 'ppc64', 'ppc', 's390x', 'x86_64', 'ia64']
    SUPPORTED_CHECKSUMS = ['sha256', 'sha', 'sha1', 'md5']
    SUPPORTED_CONTENT_TYPES = ['yum', 'file']

    collection_name = 'repos'
    search_indices = ('packages', 'errata')
    unique_indices = ('relative_path',)

    def __init__(self, id, name, arch, relative_path, source=None, notes=None, content_types=None):
        self._id = id
        self.id = id
        if source:
            self.source = RepoSource(source)
        else:
            self.source = None
        self.name = name
        self.arch = arch
        self.release = None
        self.packages = []
        self.package_count = 0
        self.packagegroups = dict()
        self.packagegroupcategories = dict()
        self.repomd_xml_path = u""
        self.group_xml_path = u""
        self.group_gz_xml_path = u""
        self.sync_schedule = None
        self.sync_options = {}
        self.last_sync = None
        self.feed_ca = None
        self.feed_cert = None
        self.consumer_ca = None
        self.consumer_cert = None
        self.errata = {}
        self.groupid = []
        self.relative_path = relative_path
        self.files = []
        self.publish = False
        self.clone_ids = []
        self.distributionid = []
        self.checksum_type = u"sha256"
        self.filters = []
        self.sync_in_progress = False
        if notes:
            self.notes = notes
        else:
            self.notes = {}
        self.preserve_metadata = False
        self.content_types = content_types

#        self.size = None

    def get_repo_source(self):
        if not self.source:
            return None
        return RepoSource(self.source)

    @classmethod
    def is_supported_arch(cls, arch):
        return arch in cls.SUPPORTED_ARCHS

    @classmethod
    def is_supported_checksum(cls, checksum_type):
        return checksum_type in cls.SUPPORTED_CHECKSUMS

    @classmethod
    def is_supported_content_type(cls, content_type):
        return content_type in cls.SUPPORTED_CONTENT_TYPES

class RepoSource(Model):

    def __init__(self, url):
        self.url = None
        self.type = None
        self.set_type(url)

    def set_type(self, url):
        proto, netloc, path, params, query, frag = urlparse.urlparse(encode_unicode(url))
        self.url = url
        if proto in ['http', 'https', 'ftp']:
            self.type = u"remote"
        elif proto in ['file']:
            self.type = u"local"
        else:
            raise PulpException("Invalid url [%s]; please provide a valid url" % url)


class RepoSyncSchedule(Model):
    """
    Class representing a serialized repository sync schedule.
    """

    def __init__(self, interval, start_time=None, runs=None):
        self.interval = interval
        self.start_time = start_time
        self.runs = runs


class RepoStatus(Model):
    """
    Repsitory synchronization status.  Represents the status of a current sync
    task on a repository.
    """

    def __init__(self, repoid, state=None, progress=None, exception=None,
                 traceback=None, next_sync_time=None):
        self.repoid = repoid
        self.state = state
        self.progress = progress
        self.exception = exception
        self.traceback = traceback
        self.next_sync_time = next_sync_time

