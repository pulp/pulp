# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import datetime

from pulp.server.db.model.base import Model
from pulp.server.pexceptions import PulpException
from pulp.server.tasking.scheduler import IntervalScheduler

# consumer models -------------------------------------------------------------

class Consumer(Model):

    collection_name = 'consumers'
    unique_indicies = ('id',)
    other_indicies = ('package_profile.name', 'repoids', 'key_value_pairs',
                      'consumer_id', 'type_name', 'timestamp')

    def __init__(self, id, description, key_value_pairs={}):
        self._id = id
        self.id = id
        self.credentials = None
        self.description = description
        self.package_profile = []
        self.repoids = []
        self.key_value_pairs = key_value_pairs


class ConsumerGroup(Model):

    collection_name = 'consumergroups'
    other_indicies = ('consumerids',)

    def __init__(self, id, description, consumerids=[], key_value_pairs={}):
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
        self.timestamp = datetime.datetime.now().strftime("%s")

# distribution model ----------------------------------------------------------

class Distribution(Model):
    '''
     Distribution Model to represent kickstart trees
    '''

    collection_name = 'distribution'
    other_indicies = ('files', 'relativepath')

    def __init__(self, id, description, relativepath, files=[]):
        self._id = id
        self.id = id
        self.description = description
        self.files = files
        self.relativepath = relativepath

# errata model ----------------------------------------------------------------

class Errata(Model):
    """
    Errata model to represent software updates
    maps to yum.update_md.UpdateNotice fields
    """

    collection_name = 'errata'
    other_indicies = ('title', 'description', 'version', 'release', 'type',
                      'status', 'updated', 'issued', 'pushcount', 'from_str',
                      'reboot_suggested')

    def __init__(self, id, title, description, version, release, type, status=u"",
            updated=u"", issued=u"", pushcount=u"", from_str=u"",
            reboot_suggested=False, references=[], pkglist=[], severity=u"",
            rights=u"", summary=u"", solution=u"", repo_defined=False, immutable=False):
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
        self.pushcount = pushcount
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

# package models --------------------------------------------------------------

class Package(Model):

    collection_name = 'packages'
    unique_indicies = (('name', 'epoch', 'version', 'release', 'arch',
                        'filename', 'checksum'),)
    other_indicies = ('name', 'filename', 'checksum', 'epoch', 'version',
                      'release', 'arch', 'description')

    def __init__(self, name, epoch, version, release, arch, description,
            checksum_type, checksum, filename, vendor=None, repo_defined=False):
        Model.__init__(self)
        # ID is initialized in Model.__init__()
        self.name = name
        self.epoch = epoch
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
    unique_indicies = (('filename', 'checksum'),)

    def __init__(self, filename, checksum_type,
                 checksum, size, description=None, repo_defined=False):
        Model.__init__(self)
        # ID is initialized in Model.__init__()
        self.filename = filename
        self.description = description
        self.checksum = {checksum_type: checksum}
        self.size = size
        self.download_url = None
        self.repo_defined = repo_defined

class Filter(Model):
    """
    Class represents a blacklist or whitelist filter that can be applied when syncing a local repository
    """
    collection_name = 'filters'
    unique_indicies = ('id',)
    other_indicies = ('type')

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

    SUPPORTED_ARCHS = ['noarch', 'i386', 'i686', 'ppc64', 's390x', 'x86_64']
    SUPPORTED_CHECKSUMS = ['sha256', 'sha', 'sha1', 'md5']

    collection_name = 'repos'
    other_indicies = ('packages', 'packagegroups', 'packagegroupcategories')

    def __init__(self, id, name, arch, source=None, notes=None):
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
        self.last_sync = None
        self.use_symlinks = None
        self.feed_ca = None
        self.feed_cert = None
        self.feed_key = None
        self.consumer_ca = None
        self.consumer_cert = None
        self.consumer_key = None
        self.errata = {}
        self.groupid = []
        self.relative_path = None
        self.files = []
        self.publish = False
        self.clone_ids = []
        self.distributionid = []
        self.checksum_type = u"sha256"
        self.filters = []
        if not notes:
            self.notes = {}
        self.notes = notes
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

class RepoSource(Model):

    def __init__(self, url):
        self.supported_types = ['yum', 'local', 'rhn']
        self.type = None
        self.url = None
        self.parse_feed(url)

    def parse_feed(self, source):
        parts = source.split(':')
        if len(parts) < 2:
            msg = "Invalid feed url.  Must be <type>:<path> where types are: %s"
            raise PulpException(msg % self.supported_types)
        if self.supported_types.count(parts[0]) < 1:
            raise PulpException("Invalid type.  valid types are %s"
                                % self.supported_types)
        self.type = parts[0]
        self.url = source.replace((self.type + ":"), "")


class RepoSyncSchedule(Model):
    """
    Class representing a serialized repository sync schedule.
    """

    def __init__(self, interval, start_time=None, runs=None):
        self.interval = interval
        self.start_time = start_time
        self.runs = runs
