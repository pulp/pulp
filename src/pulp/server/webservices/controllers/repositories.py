# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Some more comments
[[wiki]]
title: Repositories RESTful Interface
description:
 RESTful interface for the creation, querying, and management of repositories managed by Pulp.
 Repositories are represented as Repo objects.
 Some operations on repositories happen asynchronously, as such, these operations return Task objects.
Repo object fields:
 * id, str, repository identifier
 * source, !RepoSource object, upstream content source
 * name, str, human-friendly name
 * arch, str, hardware architecture that repository is for
 * release, str, release number
 * packages, list of str, list of package ids in the repository [deferred field]
 * package_count, int, number of packages in the repository
 * packagegroups, object, map of package group names to list of package ids in the group [deferred field]
 * packagegroupcategories, object, map of categories to lists of package group names [deferred field]
 * repomd_xml_path, str, path to the repository's repomd xml file
 * group_xml_path, str, path to the repository's group xml file
 * group_gz_xml_path, str, path to the repository's compressed group xml file
 * sync_schedule, iso8601 formated recurring interval
 * last_sync, str or nil, date and time of last successful sync in iso8601 format, nil if has not been synched
 * feed_ca, str, full path on the Pulp server to the certificate authority used to verify SSL connections to the repo's feed
 * feed_cert, str, full path on the Pulp server to the certificate used to authenticate Pulp with the repo's feed server when synchronizing content
 * feed_key, str, full path on the Pulp server to the private key for the feed certificate
 * consumer_ca, str, full path on the Pulp server to the certificate authority used to verify consumer entitlement certificates
 * consumer_cert, str, full path on the Pulp server to the entitlement certificate that will be given to bound consumers to authenticate access to the repository
 * consumer_key, str, full path on the Pulp server to the private key for the consumer's entitlement certificate
 * errata, object, map of errata names to lists of package ids in each errata [deferred field]
 * groupid, list of str, list of repository group ids this repository belongs to
 * relative_path, str, repository's path relative to the configured root
 * files, list of str, list of ids of the non-package files in the repository [deferred field]
 * publish, bool, whether or not the repository is available
 * clone_ids, list of str, list of repository ids that are clones of this repository
 * distributionid, list of str, list of distribution ids this repository belongs to [deferred fields]
 * checksum_type, str, name of the algorithm used for checksums of the repository's content for feedless repos; For feed repos, this gets overwritten by source checksum type from repomd.xml.
 * filters, list of str, list of filter ids associated with the repository
 * content_types, str, content type allowed in this repository; default:yum; supported: [yum, file]
 * notes, dict, custom key-value attributes for this repository
!RepoSource object fields:
 * supported_types, list of str, list of supported types of repositories
 * type, str, repository source type
 * url, str, repository source url
Task object fields:
 * id, str, unique id (usually a uuid) for the task
 * method_name, str, name of the pulp library method that was called
 * state, str, one of several valid states of the tasks lifetime: waiting, running, finished, error, timed_out, canceled, reset, suspended
 * start_time, str or nil, time the task started running in iso8601 format, nil if the task has not yet started
 * finish_time,  or nil, time the task finished running in iso8601 format, nil if the task has not yet finished
 * result, object or nil, the result of the pulp library method upon return, usually nil
 * exception, str or nil, a string representation of an error in the pulp librry call, if any
 * traceback, str or nil, a string print out of the trace back for the exception, if any
 * progress, object or nil, object representing the pulp library call's progress, nill if no information is available
 * scheduled_time, str or nil, time the task is scheduled to run in iso8601 format, applicable only for scheduled tasks
Progress object fields:
 * step, str, name of the step the pulp library call is on
 * items_total, int, the total number of items to be processed by the call
 * items_left, int, the remaining number of items to be processed by the call
 * details, object, object providing further details on the progress
Details object fields:
 * num_success, int, the number of items successfully processed
 * total_count, int, the number of items that were attempted to be processed
!TaskHistory object fields:
 * id, str, uuid of task
 * class_name, str, name of the task was a instance method
 * method_name, str, namd of the task callable
 * args, list, list of arguments passed to the task callable
 * kwargs, dict, dictionary of arguments passed to the task callable
 * state, str, final state of the task
 * progress, object, Progress object for the progress at the end of the task
 * result, object, result returned by the task, most likely null
 * exception, str, error, if one occurred
 * traceback, str, traceback if error occurred
 * consecutive_failures, int, number of failures since last success
 * scheduled_time, str, iso8601 combined date time when task was scheduler to run
 * start_time, str, iso8601 combined date time when task actually ran
 * finished_time, str, iso8601 combined date time when task completed
"""

import itertools
import logging
from gettext import gettext as _
import os

import web

from pulp.common.dateutils import format_iso8601_datetime
from pulp.server import async
from pulp.server.util import encode_unicode
from pulp.server.api import repo_sync, exporter
from pulp.server.api import scheduled_sync
from pulp.server.api import task_history
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.auth.authorization import grant_automatic_permissions_for_created_resource
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE
from pulp.server.exporter.base import ExportException, TargetExistsException
from pulp.server.exceptions import PulpException
from pulp.server.webservices import http
from pulp.server.webservices import mongo
from pulp.server.webservices import serialization
from pulp.server.webservices import validation
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler, collection_query)

# globals ---------------------------------------------------------------------

api = RepoApi()
pkg_api = PackageApi()
errataapi = ErrataApi()
_log = logging.getLogger(__name__)

# default fields for repositories being sent to the client
default_fields = [
    'id',
    'source',
    'name',
    'arch',
    'last_sync',
    'sync_schedule',
    'sync_options',
    'groupid',
    'relative_path',
    'files',
    'publish',
    'clone_ids',
    'distributionid',
    'checksum_type',
    'filters',
    'package_count',
    'feed_cert',
    'feed_ca',
    'feed_key',
    'consumer_cert',
    'consumer_ca',
    'consumer_key',
    'notes',
    'content_types',
    'preserve_metadata',
]

# restful controllers ---------------------------------------------------------

class Repositories(JSONController):

    @error_handler
    @auth_required(READ)
    @collection_query('id', 'name', 'arch', 'groupid', 'relative_path', 'note')
    def GET(self, spec=None):
        """
        [[wiki]]
        title: List Available Repositories
        description: Get a list of all repositories managed by Pulp.
        method: GET
        path: /repositories/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of Repo objects, possibly empty
        example:
        {{{
        #!js
        [
         {'arch': 'noarch',
          'checksum_type': 'sha256',
          'clone_ids': ['0ad-clone', '0ad-clone-again'],
          'comps': '/pulp/api/repositories/0ad/comps/',
          'consumer_ca': None,
          'consumer_cert': None,
          'content_types': 'yum',
          'distribution': '/pulp/api/repositories/0ad/distribution/',
          'distributionid': [],
          'errata': '/pulp/api/repositories/0ad/errata/',
          'feed_ca': None,
          'feed_cert': None,
          'files': '/pulp/api/repositories/0ad/files/',
          'files_count': 0,
          'filters': [],
          'groupid': [],
          'id': '0ad',
          'keys': '/pulp/api/repositories/0ad/keys/',
          'last_sync': '2012-01-04T13:55:11-07:00',
          'name': '0ad',
          'notes': {},
          'package_count': 2,
          'packagegroupcategories': '/pulp/api/repositories/0ad/packagegroupcategories/',
          'packagegroups': '/pulp/api/repositories/0ad/packagegroups/',
          'packages': '/pulp/api/repositories/0ad/packages/',
          'preserve_metadata': False,
          'publish': True,
          'relative_path': 'repos/bioinfornatics/0ad/fedora-16/x86_64',
          'source': {'type': 'remote',
          'url': 'http://repos.fedorapeople.org/repos/bioinfornatics/0ad/fedora-16/x86_64/'},
          'sync_options': {'skip': {}},
          'sync_schedule': '2011-12-13T13:45:00-07:00/PT5M',
          'uri': 'https://localhost/pulp/repos/repos/bioinfornatics/0ad/fedora-16/x86_64/',
          'uri_ref': '/pulp/api/repositories/0ad/'},
        ...
        ]
        }}}
        filters:
         * id, str, repository id
         * name, str, repository name
         * arch, str, repository contect architecture
         * groupid, str, repository group id
         * relative_path, str, repository's on disk path
         * note, str, repository note in the format key:value
        """
        # Query by notes
        if "note" in spec.keys() :
            try:
                note = spec["note"].rsplit(':')
            except:
                return self.bad_request("Invalid note %s; correct format is key:value", note)

            if len(note) != 2:
                return self.bad_request("Invalid note %s; correct format is key:value" % note)

            spec["notes." + note[0]] = note[1]
            del spec["note"]

        repositories = api.repositories(spec, default_fields)

        for repo in repositories:
            repo['uri_ref'] = http.extend_uri_path(repo['id'])
            repo['uri'] = serialization.repo.v1_uri(repo)
            #repo['package_count'] = api.package_count(repo['id'])
            repo['files_count'] = len(repo['files'])
            for field in RepositoryDeferredFields.exposed_fields:
                repo[field] = http.extend_uri_path('/'.join((repo['id'], field)))

        return self.ok(repositories)

    @error_handler
    @auth_required(CREATE)
    def POST(self):
        """
        [[wiki]]
        title: Create a Repository
        description: Create a new repository based on the passed information
        method: POST
        path: /repositories/
        permission: CREATE
        success response: 201 Created
        failure response: 409 Conflict if the parameters matches an existing repository
        return: new Repo object
        example:
        {{{
        #!js
        {'arch': 'noarch',
         'checksum_type': 'sha256',
         'clone_ids': [],
         'consumer_ca': None,
         'consumer_cert': None,
         'content_types': 'yum',
         'distributionid': [],
         'errata': {},
         'feed_ca': None,
         'feed_cert': None,
         'files': [],
         'filters': [],
         'group_gz_xml_path': '',
         'group_xml_path': '',
         'groupid': [],
         'id': 'my-repo',
         'last_sync': None,
         'name': 'my-repo',
         'notes': {},
         'package_count': 0,
         'packagegroupcategories': {},
         'packagegroups': {},
         'packages': [],
         'preserve_metadata': False,
         'publish': True,
         'relative_path': 'yum/repo',
         'release': None,
         'repomd_xml_path': '/var/lib/pulp//repos/yum/repo/repodata/repomd.xml',
         'source': {'type': 'remote', 'url': 'http://example.org/yum/repo/'},
         'sync_in_progress': False,
         'sync_options': {},
         'sync_schedule': None,
         'uri_ref': '/pulp/api/repositories/my-repo/'}
        }}}
        parameters:
         * id, str, the repository's unique id
         * name, str, a human-friendly name for the repsitory
         * arch, str, the main architecture of packages contained in the repository
         * feed, str, repository feed in the form of <type>:<url>
         * feed_cert_data?, dict, certificate information to use when connecting to the feed.  Has fields 'ca':filename, 'crt':filename, 'key':filename
         * consumer_cert_data?, str, certificate information to use when validating consumers of this repo.  Has fields 'ca':filename, 'crt':filename, 'key':filename
         * relative_path?, str, repository on disk path
         * groupid?, list of str, list of repository group ids this repository belongs to
         * gpgkeys?, list of str, list of gpg keys used for signing content
         * checksum_type?, str, name of the algorithm to use for content checksums for feedless repos, defaults to sha256. For feed repos, this gets overwritten by source checksum type from repomd.xml.
         * preserve_metadata?, bool, will not regenerate metadata and treats the repo as a mirror
         * content_types?, str, content type allowed in this repository; default:yum; supported: [yum, file]
         * publish?, bool, sets the publish state on a repository; if not specified uses 'default_to_published' value from pulp.conf
        """
        repo_data = self.params()

        id = repo_data['id']
        if api.repository(id, default_fields) is not None:
            return self.conflict('A repository with the id, %s, already exists' % id)

        repo = api.create(id,
                          repo_data['name'],
                          repo_data['arch'],
                          feed=repo_data.get('feed', None),
                          feed_cert_data=repo_data.get('feed_cert_data', None),
                          consumer_cert_data=repo_data.get('consumer_cert_data', None),
                          relative_path=repo_data.get('relative_path', None),
                          groupid=repo_data.get('groupid', None),
                          gpgkeys=repo_data.get('gpgkeys', None),
                          checksum_type=repo_data.get('checksum_type', 'sha256'),
                          notes=repo_data.get('notes', None),
                          preserve_metadata=repo_data.get('preserve_metadata', False),
                          content_types=repo_data.get('content_types', 'yum'),
                          publish=repo_data.get('publish', None),)

        path = http.extend_uri_path(repo["id"])
        repo['uri_ref'] = path
        grant_automatic_permissions_for_created_resource(http.resource_path(path))
        return self.created(path, repo)

    def PUT(self):
        _log.debug('deprecated Repositories.PUT method called')
        return self.POST()

    @error_handler
    @auth_required(DELETE)
    def DELETE(self):
        """
        [[wiki]]
        title: Delete All Repositories
        description: Delete all repositories managed by Pulp.
        method: DELETE
        path: /repositories/
        permission: DELETE
        success response: 200 OK
        failure response: None
        return: True
        """
        api.clean()
        return self.ok(True)


class Repository(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        [[wiki]]
        title: Get A Repository
        description: Get a Repo object for a specific repository
        method: GET
        path: /repositories/<id>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: a Repo object
        example:
        {{{
        #!js
        {'arch': 'noarch',
         'checksum_type': 'sha256',
         'clone_ids': ['0ad-clone', '0ad-clone-again'],
         'comps': '/pulp/api/repositories/0ad/comps/',
         'consumer_ca': None,
         'consumer_cert': None,
         'content_types': 'yum',
         'distribution': '/pulp/api/repositories/0ad/distribution/',
         'distributionid': [],
         'errata': '/pulp/api/repositories/0ad/errata/',
         'feed_ca': None,
         'feed_cert': None,
         'files': '/pulp/api/repositories/0ad/files/',
         'files_count': 0,
         'filters': [],
         'groupid': [],
         'id': '0ad',
         'keys': '/pulp/api/repositories/0ad/keys/',
         'last_sync': '2012-01-04T13:55:11-07:00',
         'name': '0ad',
         'notes': {},
         'package_count': 2,
         'packagegroupcategories': '/pulp/api/repositories/0ad/packagegroupcategories/',
         'packagegroups': '/pulp/api/repositories/0ad/packagegroups/',
         'packages': '/pulp/api/repositories/0ad/packages/',
         'preserve_metadata': False,
         'publish': True,
         'relative_path': 'repos/bioinfornatics/0ad/fedora-16/x86_64',
         'source': {'type': 'remote',
         'url': 'http://repos.fedorapeople.org/repos/bioinfornatics/0ad/fedora-16/x86_64/'},
         'sync_options': {'skip': {}},
         'sync_schedule': '2011-12-13T13:45:00-07:00/PT5M',
         'uri': 'https://localhost/pulp/repos/repos/bioinfornatics/0ad/fedora-16/x86_64/',
         'uri_ref': '/pulp/api/repositories/0ad/'}
        }}}
        """
        repo = api.repository(id, default_fields)
        if repo is None:
            return self.not_found('No repository %s' % id)
        for field in RepositoryDeferredFields.exposed_fields:
            repo[field] = http.extend_uri_path(field)
        repo['uri_ref'] = http.uri_path()
        repo['uri'] = serialization.repo.v1_uri(repo)
        #repo['package_count'] = api.package_count(id)
        # XXX this was a serious problem with packages
        # why would files be any different
        repo['files_count'] = len(repo['files'])
        # see if the repo is scheduled for sync in the future
        task = scheduled_sync.find_scheduled_task(repo['id'], '_sync')
        repo['next_scheduled_time'] = None
        if task and task.scheduled_time is not None:
            repo['next_scheduled_sync'] = format_iso8601_datetime(task.scheduled_time)
        return self.ok(repo)

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, id):
        """
        [[wiki]]
        title: Update A Repository
        description: Change an exisiting repository.
        method: PUT
        path: /repositories/<id>/
        permission: UPDATE
        success response: 200 OK
        failure response: 400 Bad Request when trying to change the id
        return: a Repo object
        example:
        {{{
        #!js
        {'arch': 'noarch',
         'checksum_type': 'sha256',
         'clone_ids': [],
         'consumer_ca': None,
         'consumer_cert': None,
         'content_types': 'yum',
         'distributionid': [],
         'errata': {},
         'feed_ca': None,
         'feed_cert': None,
         'files': [],
         'filters': [],
         'group_gz_xml_path': '',
         'group_xml_path': '',
         'groupid': [],
         'id': 'my-repo',
         'last_sync': None,
         'name': 'my-repo',
         'notes': {},
         'package_count': 0,
         'packagegroupcategories': {},
         'packagegroups': {},
         'packages': [],
         'preserve_metadata': False,
         'publish': True,
         'relative_path': 'yum/repo',
         'release': None,
         'repomd_xml_path': '/var/lib/pulp//repos/yum/repo/repodata/repomd.xml',
         'source': {'type': 'remote', 'url': 'http://example.org/yum/repo/'},
         'sync_in_progress': False,
         'sync_options': {},
         'sync_schedule': None,
         'uri_ref': '/pulp/api/repositories/my-repo/'}
        }}}
        parameters:
         * name, str, name of the repository
         * arch, str, architecture of the repository
         * feed_cert_data, object, feed key and certificate
         * consumer_cert_data, object, consumers key and certificate
         * feed, str, url of feed
         * checksum_type, str, name of checksum algorithm (sha256, sha1, md5)
         * addgrp?, list of str, list of group ids to add the repository to
         * rmgrp?, list of str, list of group ids to remove the repository from
         * addkeys?, list of str, list of keys to add to the repository
         * rmkeys?, list of str, list of keys to remove from the repository
        """
        delta = self.params()
        if delta.pop('id', id) != id:
            return self.bad_request('You cannot change a repository id')
        # we need to remove the substituted uri references
        # XXX we probably need to add the original data back as well
        for field in itertools.chain(['uri_ref'], # web services only field
                                     RepositoryDeferredFields.exposed_fields):
            if field in delta and isinstance(delta[field], basestring):
                delta.pop(field, None)
        repo = api.update(id, delta)
        return self.ok(repo)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):
        """
        [[wiki]]
        title: Delete A Repository
        description: Delete a single repository
        method: DELETE
        path: /repositories/<id>/
        permission: DELETE
        success response: 202 Accepted
        failure response: 404 Not Found if repository does not exist
                          409 Conflict if repository cannot be deleted
        return: a Task object
        example:
        {{{
        #!js
        {'args': [],
         'class_name': 'RepoApi',
         'exception': None,
         'finish_time': None,
         'id': '1a58cd4f-372f-11e1-bdbc-52540005f34c',
         'job_id': None,
         'method_name': 'delete',
         'progress': None,
         'result': None,
         'scheduled_time': '2012-01-04T23:52:04Z',
         'scheduler': 'immediate',
         'start_time': None,
         'state': 'waiting',
         'traceback': None}
        }}}
        """
        repo = api.repository(id)
        if repo is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        task = async.run_async(api.delete, args=[id])
        if task is None:
            return self.conflict('The repository, %s, cannot be deleted' % id)
        status = self._task_to_dict(task)
        return self.accepted(status)

class RepositoryNotes(JSONController):

    @auth_required(DELETE)
    def DELETE(self, id, key):
        """
        [[wiki]]
        title: Delete a Note from a Repository
        description: Delete a Note from a Repository
        method: DELETE
        path: /repositories/<id>/notes/<key>/
        permission: DELETE
        success response: 200 OK
        failure response: 404 Not Found if given repository does not exist
                          404 Not Found if given key does not exist
        return: true
        """
        repo = api.repository(id)
        if repo is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        key_value_pairs = repo['notes']
        if key not in key_value_pairs.keys():
            return self.not_found('Given key [%s] does not exist' % key)
        api.delete_note(id, key)
        return self.ok(True)

    @auth_required(UPDATE)
    def PUT(self, id, key):
        """
        [[wiki]]
        title: Update a key-value note of a Repository
        description: Change the value of an existing key in Repository Notes.
        method: PUT
        path: /repositories/<id>/notes/<key>/
        permission: UPDATE
        success response: 200 OK
        failure response: 404 Not Found if given repository does not exist
                          404 Not Found if given key does not exist
        return: true
        parameters: new value of the key
        """
        data = self.params()
        repo = api.repository(id)
        if repo is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        key_value_pairs = repo['notes']
        if key not in key_value_pairs.keys():
            return self.not_found('Given key [%s] does not exist' % key)
        api.update_note(id, key, data)
        return self.ok(True)

class RepositoryNotesCollection(JSONController):
    @auth_required(EXECUTE)
    def POST(self, id):
        """
        [[wiki]]
        title: Add a Note to the Repository
        description: Add a Note to the Repository
        method: POST
        path: /repositories/<id>/notes/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not found if given repository does not exist
                          409 Conflict if given key already exists
        return: true
        parameters:
         * key, str, key to be added
         * value, str, value of key
        """
        data = self.params()
        repo = api.repository(id)
        if repo is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        key_value_pairs = repo['notes']
        if data['key'] in key_value_pairs.keys():
            return self.conflict('Given key [%s] already exist' % data['key'])
        api.add_note(id, data['key'], data['value'])
        return self.ok(True)


class SchedulesSubCollection(JSONController):
    # placeholder for: /repositories/<id>/schedules/
    pass


class SchedulesResource(JSONController):

    schedule_types = ('sync',)

    @error_handler
    @auth_required(READ)
    def GET(self, repo_id, schedule_type):
        """
        [[wiki]]
        title: Schedule
        description: Get the repository schedule for the given type
        method: GET
        path: /repositories/<id>/schedules/<type>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found
        return: Schedule object
        example:
        {{{
        #!js
        {'href': '/pulp/api/repositories/0ad/',
         'id': '0ad',
         'options': {'skip': {}},
         'schedule': '2011-12-13T13:45:00-07:00/PT5M',
         'type': 'sync'}
        }}}
        """
        if schedule_type not in self.schedule_types:
            return self.not_found('No schedule type: %s' % schedule_type)
        repo = api.repository(repo_id, ['id', 'sync_schedule', 'sync_options'])
        if repo is None:
            return self.not_found('No repository %s' % repo_id)
        next_sync_time = None
        if repo['sync_schedule']:
            scheduled_task_list = async.find_async(method_name="_sync",
                repo_id=repo_id)
            if scheduled_task_list:
                scheduled_task = scheduled_task_list[0]
                next_sync_time = format_iso8601_datetime(
                    scheduled_task.scheduled_time)
        data = {
            'id': repo_id,
            'href': serialization.repo.v1_href(repo),
            'type': schedule_type,
            'schedule': repo['sync_schedule'],
            'options': repo['sync_options'],
            'next_sync_time': next_sync_time,
        }
        return self.ok(data)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, repo_id, schedule_type):
        """
        [[wiki]]
        title: Schedule Delete
        description: Remove a repository's schedule for the given type
        method: DELETE
        path: /repositories/<id>/schedules/<type>/
        permission: DELETE
        success response: 200 OK
        failure response: 404 Not Found
        return: (empty) Schedule object
        example:
        {{{
        #!js
        {'href': '/pulp/api/repositories/0ad/',
         'id': '0ad',
         'options': null,
         'schedule': null}
        }}}
        """
        if schedule_type not in self.schedule_types:
            return self.not_found('No schedule type: %s' % schedule_type)
        repo = api.repository(repo_id, ['id', 'sync_schedule'])
        if repo is None:
            return self.not_found('No repository %s' % repo_id)
        scheduled_sync.delete_repo_schedule(repo)
        data = {
            'id': repo_id,
            'href': serialization.repo.v1_href(repo),
            'schedule': None,
            'options': None,
        }
        return self.ok(data)

    @error_handler
    @auth_required(CREATE)
    def PUT(self, repo_id, schedule_type):
        """
        [[wiki]]
        title: Schedule Create or Replace
        description: Create or replace a schedule for a repository of the given type
        method: PUT
        path: /repositories/<id>/schedules/<type>/
        permission: CREATE
        success response: 200 OK
        parameters:
         * schedule, str, schedule for given type in iso8601 format
         * options, obj, options for the scheduled action
        return: Schedule object
        example:
        {{{
        #!js
        {'href': '/pulp/api/repositories/0ad/',
         'id': '0ad',
         'options': {'skip': {}},
         'schedule': '2011-12-13T13:45:00-07:00/PT5M',
         'type': 'sync'}
        }}}
        """
        if schedule_type not in self.schedule_types:
            return self.not_found('No schedule type: %s' % schedule_type)
        repo = api.repository(repo_id, ['id', 'sync_schedule', 'sync_options', 'content_types', 'source'])
        if repo is None:
            return self.not_found('No repository %s' % repo_id)
        data = self.params()
        new_schedule = data.get('schedule')
        new_options = data.get('options')
        scheduled_sync.update_repo_schedule(repo, new_schedule, new_options)
        updated_repo = api.repository(repo_id, ['id', 'sync_schedule', 'sync_options'])
        data = {
            'id': repo_id,
            'href': serialization.repo.v1_href(repo),
            'schedule': updated_repo['sync_schedule'],
            'options': updated_repo['sync_options'],
        }
        return self.ok(data)

    POST = PUT


class RepositoryDeferredFields(JSONController):

    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
        'packages',
        'packagegroups',
        'packagegroupcategories',
        'errata',
        'distribution',
        'files',
        'keys',
        'comps',
    )

    def packages(self, id):
        """
        [[wiki]]
        title: Repository Packages
        description: Get the packages in a repository
        method: GET
        path: /repositories/<id>/packages/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: list of Package objects
        example:
        {{{
        #!js
        [{'arch': 'x86_64',
          'buildhost': 'x86-05.phx2.fedoraproject.org',
          'checksum': {'sha256': '46d0ca0bc9f943d38bd0819b849072c5a48c4107fd6e17bb7a1f9782fa1dccfe'},
          'description': '0 A.D. (pronounced "zero ey-dee") is a free, open-source, cross-platform real-time\nstrategy (RTS) game of ancient warfare. In short, it is a historically-based\nwar/economy game that allows players to relive or rewrite the history of Western\ncivilizations, focusing on the years between 500 B.C. and 500 A.D. The project is\nhighly ambitious, involving state-of-the-art 3D graphics, detailed artwork, sound,\nand a flexible and powerful custom-built game engine.\nThe game has been in development by Wildfire Games (WFG), a group of volunteer,\nhobbyist game developers, since 2001.',
          'download_url': 'https://localhost//pulp/repos/repos/bioinfornatics/0ad/fedora-16/x86_64/0ad-0.10836-15.20111230svn10836.fc16.x86_64.rpm',
          'epoch': '0',
          'filename': '0ad-0.10836-15.20111230svn10836.fc16.x86_64.rpm',
          'group': 'Amusements/Games',
          'id': 'e8c7520d-00ee-44b9-863e-b50db7ac9252',
          'license': 'GPLv2+ and MIT',
          'name': '0ad',
          'provides': ['0ad(x86-64)',
                        '0ad',
                        'libnvtt.so()(64bit)',
                        'libnvmath.so()(64bit)',
                        'libnvimage.so()(64bit)',
                        ...],
          'release': '15.20111230svn10836.fc16',
          'repo_defined': True,
          'requires': ['libstdc++.so.6(GLIBCXX_3.4)(64bit)',
                        'librt.so.1()(64bit)',
                        'libpthread.so.0()(64bit)',
                        'libstdc++.so.6(CXXABI_1.3.1)(64bit)',
                        'libcurl.so.4()(64bit)',
                        ...],
          'size': 3592509,
          'vendor': 'Fedora Project',
          'version': '0.10836'},
        {'_id': 'e078a03a-979f-4bfe-b47e-8e86a7e9e224',
         '_ns': 'packages',
         'arch': 'x86_64',
         'buildhost': 'x86-05.phx2.fedoraproject.org',
         'checksum': {'sha256': 'bde5b50d462142a9cd8aee02b8fbc6665eda3ddfb324c0d9c072817a2babb4f8'},
         'description': 'This package provides debug information for package 0ad.\nDebug information is useful when developing applications that use this\npackage or when debugging this package.',
         'download_url': 'https://localhost//pulp/repos/repos/bioinfornatics/0ad/fedora-16/x86_64/0ad-debuginfo-0.10836-15.20111230svn10836.fc16.x86_64.rpm',
         'epoch': '0',
         'filename': '0ad-debuginfo-0.10836-15.20111230svn10836.fc16.x86_64.rpm',
         'group': 'Development/Debug',
         'id': 'e078a03a-979f-4bfe-b47e-8e86a7e9e224',
         'license': 'GPLv2+ and MIT',
         'name': '0ad-debuginfo',
         'provides': ['0ad-debuginfo(x86-64)', '0ad-debuginfo'],
         'release': '15.20111230svn10836.fc16',
         'repo_defined': True,
         'requires': [],
         'size': 41946553,
         'vendor': 'Fedora Project',
         'version': '0.10836'}]
        }}}
        filters:
         * name, str, package name
         * version, str, package version
         * release, str, package release
         * epoch, int, package epoch
         * arch, str, package architecture
         * filename, str, name of package file
         * field, str, field to include in Package objects
        """
        valid_filters = ('name', 'version', 'release', 'epoch', 'arch',
                        'filename', 'field')
        filters = self.filters(valid_filters)
        fields = filters.pop('filed', None)
        spec = mongo.filters_to_re_spec(filters) or {}
        try:
            packages = api.get_packages(id, spec, fields)
        except PulpException: # XXX this isn't specific enough!
            return self.not_found('No repository %s' % id)
        else:
            return self.ok(packages)

    def packagegroups(self, id):
        """
        [[wiki]]
        title: Repository Package Groups
        description: Get the package groups in the repositories.
        method: GET
        path: /repositories/<repository id>/packagegroups/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: Package Groups object
        example:
        {{{
        #!js
        {"pkg_group_id_1": {
            "mandatory_package_names": [],
            "description": "pkg_grp_description_1",
            "repo_defined": false,
            "default": true,
            "name": "pkg_group_name_1",
            "display_order": 1024,
            "user_visible": true,
            "translated_name": {},
            "translated_description": {},
            "conditional_package_names": {},
            "default_package_names": [],
            "id": "pkg_group_id_1",
            "langonly": null,
            "_id": "pkg_group_id_1",
            "immutable": false,
            "optional_package_names": []
          }
        }
        }}}
        filters:
         * filter_missing_packages, bool, True means to filter results to remove missing package names
         * filter_incomplete_groups, bool, True means to filter results to remove groups with missing packages
        """
        repo = api.repository(id, ['id', 'packagegroups'])
        if repo is None:
            return self.not_found('No repository %s' % id)
        valid_filters = ('filter_missing_packages', 'filter_incomplete_groups')
        filters = self.filters(valid_filters)
        filter_missing_packages = False
        if filters.has_key("filter_missing_packages") and filters["filter_missing_packages"]:
            filter_missing_packages = True
        filter_incomplete_groups = False
        if filters.has_key("filter_incomplete_groups") and filters["filter_incomplete_groups"]:
            filter_incomplete_groups = True
        return self.ok(api.packagegroups(id, filter_missing_packages, filter_incomplete_groups))

    def packagegroupcategories(self, id):
        """
        [[wiki]]
        title: Repository Package Group Categories
        description: Get the package group categories in the repository.
        method: GET
        path: /repositories/<id>/packagegroupcategories/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: list of package group category names
        example:
        {{{
        #!js
         {
          "cat_id_1": {
            "description": "cat_descrp_1",
            "repo_defined": false,
            "display_order": 99,
            "immutable": false,
            "translated_name": {},
            "packagegroupids": [],
            "translated_description": {},
            "_id": "cat_id_1",
            "id": "cat_id_1",
            "name": "cat_name_1"
          }
        }
        }}}
        filters:
         * id, str, package group category id
         * packagegroupcategories, str, package group category name
        """
        repo = api.repository(id, ['id', 'packagegroupcategories'])
        if repo is None:
            return self.not_found('No repository %s' % id)
        return self.ok(repo.get('packagegroupcategories', []))

    def errata(self, id):
        """
        [[wiki]]
        title: Repository Errata
        description: List the applicable errata for the repository.
        method: GET
        path: /repositories/<id>/errata/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: list of Errata objects
        example:
        {{{
        #!js
        [{'id': '',
          'title': '',
          'type': '',
          'severity': null},
         {'id': '',
          'title': '',
          'type': '',
          'severity': ''},
         ...]
        }}}
        filters:
         * type, str, type of errata
        """
        valid_filters = ('type', 'severity')
        types = self.filters(valid_filters).get('type', [])
        severity = self.filters(valid_filters).get('severity', [])

        if types:
            errata = api.errata(id, types=types)
        elif severity:
            errata = api.errata(id, severity=severity)
        else:
            errata = api.errata(id)

        return self.ok(errata)

    def distribution(self, id):
        """
        [[wiki]]
        title: Repository Distribution
        description: List the distributions the repository is part of.
        method: GET
        path: /repositories/<id>/distribution/
        permission: READ
        success response: 200 OK
        return: list of Distribution objects
        """
        return self.ok(api.list_distributions(id))

    def files(self, id):
        """
        [[wiki]]
        title: Repository Files
        description: List the non-package files in the repository.
        method: GET
        path: /repositories/<id>/files/
        permission: READ
        success response: 200 OK
        return: list of File objects
        """
        return self.ok(api.list_files(id))

    def keys(self, id):
        """
        [[wiki]]
        title: Repository GPG Keys
        description: List the gpg keys used by the repository.
        method: GET
        path: /repositories/<id>/keys/
        permission: READ
        success response: 200 OK
        return: list of gpg keys
        """
        keylist = api.listkeys(id)
        return self.ok(keylist)

    def comps(self, id):
        """
        [[wiki]]
        title: Repository Comps XML
        description: Get the xml content of the repository comps file
        method: GET
        path: /repositories/<id>/comps/
        permission: READ
        success response: 200 OK
        return: xml comps file
        """
        return self.ok(repo_sync.export_comps(id))

    @error_handler
    @auth_required(READ)
    def GET(self, id, field_name):
        field = getattr(self, field_name, None)
        if field is None:
            return self.internal_server_error('No implementation for %s found' % field_name)
        return field(id)


class RepositoryStatusesCollection(JSONController):
    @error_handler
    @auth_required(READ)
    def GET(self, repo_id):
        sync_status_controller = RepositorySyncStatus()
        status_methods = [getattr(sync_status_controller, st)
            for st in sync_status_controller.status_types.values()]

        statuses = []
        for status_method in status_methods:
            status = status_method(repo_id)
            if status:
                statuses.append(status)

        return self.ok(statuses)

class RepositorySyncStatus(JSONController):

    status_types = {"sync" : "_sync",
                    "clone" : "_clone"}

    def _sync(self, repo_id):
        return api.get_sync_status(repo_id)

    def _clone(self, repo_id):
        pass

    @error_handler
    @auth_required(READ)
    def GET(self, repo_id, status_type):
        status_method = getattr(self, self.status_types[status_type], None)

        if status_method:
            response = self.ok(status_method(repo_id))
        else:
            response = self.not_found(_("Invalid status type %s.") %
                status_type)

        return response

class RepositoryActions(JSONController):

    # All actions have been gathered here into one controller class for both
    # convenience and automatically generate the regular expression that will
    # map valid actions to this class. This also provides a single point for
    # querying existing tasks.
    #
    # There are two steps to implementing a new action:
    # 1. The action name must be added to the tuple of exposed_actions
    # 2. You must add a method to this class with the same name as the action
    #    that takes two positional arguments: 'self' and 'id' where id is the
    #    the repository id. Additional parameters from the body can be
    #    fetched and de-serialized via the self.params() call.

    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
        'sync',
        '_sync',
        'clone',
        'upload',
        'add_package',
        'delete_package',
        'get_package',
        'add_file',
        'remove_file',
        'add_packages_to_group',
        'delete_package_from_group',
        'delete_packagegroup',
        'create_packagegroup',
        'create_packagegroupcategory',
        'delete_packagegroupcategory',
        'add_packagegroup_to_category',
        'delete_packagegroup_from_category',
        'add_errata',
        'delete_errata',
        'get_package_by_nvrea',
        'get_package_by_filename',
        'addkeys',
        'rmkeys',
        'update_publish',
        'import_comps',
        'add_filters',
        'remove_filters',
        'add_group',
        'remove_group',
        'generate_metadata',
        'sync_history',
        'add_metadata',
        'download_metadata',
        'list_metadata',
        'remove_metadata',
        'export',
        'add_distribution',
        'remove_distribution',
    )

    def sync(self, id):
        """
        [[wiki]]
        title: Repository Sychronization
        description: Synchronize the repository's content from its source.
        method: POST
        path: /repositories/<id>/sync/
        permission: EXECUTE
        success response: 202 Accepted
        failure response: 404 Not Found if the id does not match a repository
                          406 Not Acceptable if the repository does not have a source
                          409 Conflict if a sync is already in progress for the repository
        return: a Task object
        parameters:
         * timeout?, str, timeout in <units>:<value> format (e.g. hours:2) valid units: seconds, minutes, hours, days, weeks
         * skip?, object, yum skip dict
         * limit?, int, value in KB/sec to limit download bandwidth per thread.  Only applicable for yum synchronization
         * threads?, int, number of threads to use for synchronization.  Only applicable for yum synchronization
        """
        repo = api.repository(id, fields=['source'])
        if repo['source'] is None:
            return self.not_acceptable('Repo [%s] is not setup for sync. Please add packages using upload.' % id)
        repo_params = self.params()
        timeout = repo_params.get('timeout', None)
        _log.info("sync timeout passed : %s" % timeout)

        # Check for valid timeout values
        if timeout:
            try:
                timeout = validation.timeout.iso8601_duration_to_timeout(timeout)
            except validation.timeout.UnsupportedTimeoutInterval, e:
                return self.bad_request(msg=e.args[0])
            if not timeout:
                raise PulpException("Invalid timeout value: %s, see --help" % repo_params['timeout'])
        limit = repo_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                if limit < 0:
                    return self.bad_request('Invalid value [%s].  "limit" must be non-negative"' % (limit))
            except:
                return self.bad_request('Unable to convert "limit" with value [%s] to an int' % (limit))
        threads = repo_params.get('threads', None)
        if threads:
            try:
                threads = int(threads)
                if threads < 1:
                    return self.bad_request('Invalid value [%s].  "threads" must be at least 1"' % (limit))
            except:
                return self.bad_request('Unable to convert "threads" with value [%s] to an int' % (threads))
        skip = repo_params.get('skip', {})
        task = repo_sync.sync(id, timeout, skip, max_speed=limit, threads=threads)
        if not task:
            return self.conflict('Sync already in process for repo [%s]' % id)
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    # XXX hack to make the web services unit tests work
    _sync = sync

    def generate_metadata(self, id):
        """
        [[wiki]]
        title: Repository Metadata generation
        description: spawn a repository's metadata generation. If metadata already exists, its a update otherwise a create
        method: POST
        path: /repositories/<id>/generate_metadata/
        permission: EXECUTE
        success response: 202 Accepted
        failure response: 404 Not Found if the id does not match a repository
                          406 Not Acceptable if the repository does not have a source
                          409 Conflict if a metadata is already in progress for the repository
        return: a Task object
        """
        repo = api.repository(id)
        repo_params = self.params()

        task = api.generate_metadata(id)
        if not task:
            return self.conflict('Metadata generation already in process for repo [%s]' % id)
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    def add_metadata(self, id):
        """
        [[wiki]]
        title: add a custom metadata filetype to Repository Metadata
        description: adds a metadata filetype to existing repository metadata(this runs modifyrepo underneath).
        method: POST
        path: /repositories/<id>/add_metadata/
        permission: EXECUTE
        success response: 200 Accepted
        failure response: 404 Not Found if the id does not match a repository
        return: True
	parameters:
         * filetype, str, filetype name to lookup in the metadata
         * filedata, str, file data to be stored

        """
        if api.repository(id, default_fields) is None:
           return self.not_found('A repository with the id, %s, does not exist' % id)
        metadata_params = self.params()
        if "filetype" not in metadata_params:
            return self.bad_request('No file type specified')
        if "filedata" not in metadata_params:
            return self.bad_request('No file data specified')
        return self.ok(api.add_metadata(id, metadata=metadata_params))

    def remove_metadata(self, id):
        """
        [[wiki]]
        title: remove metadata filetype from Repository Metadata
        description: remove the specified metadata filetype
                     if exists from a repository metadata; else None.
        method: POST
        path: /repositories/<id>/remove_metadata/
        permission: EXECUTE
        success response: 200 Accepted
        failure response: 404 Not Found if the id does not match a repository
        return: True
	    parameters:
         * filetype, str, filetype name to lookup in the metadata
        """
        if api.repository(id, default_fields) is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        params = self.params()
        if "filetype" not in params:
            return self.bad_request('No filetype specified')
        return self.ok(api.remove_metadata(id, filetype=params['filetype']))

    def download_metadata(self, id):
        """
        [[wiki]]
        title: download custom metadata filetype from Repository Metadata
        description: download an xml file for the filetype specified
                     if exists in a repository metadata; else None.
        method: POST
        path: /repositories/<id>/download_metadata/
        permission: EXECUTE
        success response: 200 Accepted
        failure response: 404 Not Found if the id does not match a repository
        return: True
	    parameters:
         * filetype, str, filetype name to lookup in the metadata
        """
        if api.repository(id, default_fields) is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        params = self.params()
        if "filetype" not in params:
            return self.bad_request('No filetype specified')
        return self.ok(api.get_metadata(id, filetype=params['filetype']))

    def list_metadata(self, id):
        """
        [[wiki]]
        title: list metadata filetype information from a Repository
        description: lists information about all the filetypes present in metadata
                    and their info such as size, checksum, path etc.
        method: POST
        path: /repositories/<id>/list_metadata/
        permission: EXECUTE
        success response: 200 Accepted
        failure response: 404 Not Found if the id does not match a repository
        return: dict or None
        """
        if api.repository(id, default_fields) is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        return self.ok(api.list_metadata(id))

    def sync_history(self, id):
        """
        @type id: str
        @param id: repo id
        """
        data = self.params()
        limit = data.get('limit', None)
        sort = data.get('sort', None)

        if limit:
            limit = int(limit)

        results = api.sync_history(id, limit=limit, sort=sort)
        return self.ok(results)


    def clone(self, id):
        """
        [[wiki]]
        title: Repository Clone
        description: Create a new repository by cloning an existing one.
        method: POST
        path: /repositories/<id>/clone/
        permission: EXECUTE
        success response: 202 Accepted
        failure response: 404 Not Found if the id does not match a repository
                          409 Conflict if the parameters match an existing repository
                          409 Conflict if the parent repository is currently syncing
        return: a Task object
        parameters:
         * clone_id, str, the id of the clone repository
         * clone_name, str, the namd of clone repository
         * feed, str, feed of the clone repository - parent/origin/none
         * relative_path?, str, clone repository on disk path
         * groupid?, str, repository groups that clone belongs to
         * filters?, list of objects, synchronization filters to apply to the clone
         * publish?, bool, sets the publish state on a repository; if not specified uses 'default_to_published' value from pulp.conf
        """
        repo_data = self.params()
        parent_repo = api.repository(id)
        if parent_repo is None:
            return self.not_found('A repository with the id, %s, does not exist' % id)
        if parent_repo['sync_in_progress']:
            return self.conflict('The repository %s is currently syncing, cannot create clone until it is finished' % id)
        if api.repository(repo_data['clone_id'], default_fields) is not None:
            return self.conflict('A repository with the id, %s, already exists' % repo_data['clone_id'])
        if repo_data['feed'] not in ['parent', 'origin', 'none']:
            return self.bad_request('Invalid feed, %s, see --help' % repo_data['feed'])
        if repo_data['feed'] == 'origin' and repo_data.get('filters'):
            return self.bad_request('Filters cannot be applied to clones with origin feed')
        task = repo_sync.clone(id,
                         repo_data['clone_id'],
                         repo_data['clone_name'],
                         repo_data['feed'],
                         relative_path=repo_data.get('relative_path', None),
                         groupid=repo_data.get('groupid', None),
                         filters=repo_data.get('filters', []),
                         publish=repo_data.get('publish', None))
        if not task:
            return self.conflict('Error in cloning repo [%s]' % id)
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)


    def upload(self, id):
        """
        [[wiki]]
        title: Repository Upload
        description: Upload a package to the repository.
        method: POST
        path: /repositories/<id>/upload/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * pkginfo, str, package information
         * pkgstream, binary, package data
        """
        data = self.params()
        api.upload(id,
                   data['pkginfo'],
                   data['pkgstream'])
        return self.ok(True)

    def add_package(self, id):
        """
        [[wiki]]
        title: Add A Package
        description: Associates a new package to the repository. This does not update metadata; call generate_metadata after this call.
        method: POST
        path: /repositories/<id>/add_package/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: list of errors, count of filtered packages
        parameters:
         * packageid, list of str, id of package to add
        """
        data = self.params()
        errors, filtered_count = api.add_package(id, data['packageid'])
        return self.ok((errors, filtered_count))

    def delete_package(self, id):
        """
        [[wiki]]
        title: Delete A Package
        description: Dis-associates a package from the repository. This does not update metadata; call generate_metadata after this call.
        method: POST
        path: /repositories/<id>/delete_package/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * package, Package object, package to delete
        """
        data = self.params()
        api.remove_packages(id, data['package'])
        return self.ok(True)

    def get_package(self, id):
        """
        @deprecated: use deferred fields: packages with filters instead
        """
        name = self.params()
        return self.ok(api.get_package(id, name))

    def add_packages_to_group(self, id):
        """
        [[wiki]]
        title: Add Packages To Package Group
        description: Add packages to a package group that is in the repository.
        method: POST
        path: /repositories/<id>/add_packages_to_group/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * groupid, str, package group id
         * packagenames, list of str, list of packages to add to the package group
        example response:
        {{{
        #!js
        null
        }}}
        """
        p = self.params()
        if "groupid" not in p:
            return self.bad_request('No groupid specified')
        if "packagenames" not in p:
            return self.bad_request('No package name specified')
        groupid = p["groupid"]
        pkg_names = p.get('packagenames', [])
        gtype = "default"
        requires = None
        if p.has_key("type"):
            gtype = p["type"]
        if p.has_key("requires"):
            requires = p["requires"]
        api.add_packages_to_group(id, groupid, pkg_names, gtype, requires)
        return self.ok(api.add_packages_to_group(id, groupid, pkg_names, gtype, requires))

    def delete_package_from_group(self, id):
        """
        [[wiki]]
        title: Delete A Package From A Package Group
        description: Delete a package from a package group in the repository.
        method: POST
        path: /repositories/<id>/delete_package_from_group/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * groupid, str, package group id
         * name, str, package name to remove
        example response:
        {{{
        #!js
        null
        }}}
        """
        p = self.params()
        if "groupid" not in p:
            return self.bad_request('No groupid specified')
        if "name" not in p:
            return self.bad_request('No package name specified')
        groupid = p["groupid"]
        pkg_name = p["name"]
        gtype = "default"
        if p.has_key("type"):
            gtype = p["type"]
        return self.ok(api.delete_package_from_group(id, groupid, pkg_name, gtype))

    def create_packagegroup(self, id):
        """
        [[wiki]]
        title: Create A Package Group
        description: Create a new package group in the repository.
        method: POST
        path: /repositories/<id>/create_packagegroup/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return:
        parameters:
         * groupid, str, id of the package group
         * groupname, str, name of the package group
         * description, str, package group description
        example response:
        {{{
        #!js
         {
          "mandatory_package_names": [],
          "description": "pkg_grp_description_1",
          "repo_defined": false,
          "default": true,
          "name": "pkg_grp_name_1",
          "display_order": 1024,
          "user_visible": true,
          "translated_name": {},
          "translated_description": {},
          "conditional_package_names": {},
          "default_package_names": [],
          "id": "pkg_grp_id_1",
          "langonly": null,
          "_id": "pkg_grp_id_1",
          "immutable": false,
          "optional_package_names": []
        }
        }}}
        """
        p = self.params()
        if "groupid" not in p:
            return self.bad_request('No groupid specified')
        groupid = p["groupid"]
        if "groupname" not in p:
            return self.bad_request('No groupname specified')
        groupname = p["groupname"]
        if "description" not in p:
            return self.bad_request('No description specified')
        descrp = p["description"]
        return self.ok(api.create_packagegroup(id, groupid, groupname,
                                               descrp))

    def import_comps(self, id):
        """
        [[wiki]]
        title: Import Comps
        description: Create packagegroups and categories from a comps.xml file.
        method: POST
        path: /repositories/<id>/import_comps/
        permission: EXECUTE
        success response: 201 Created
        failure response: 404 Not Found if the id does not match a repository
        return: True on success, False on failure
        parameters:
         * xml comps file body
        example response:
        {{{
        #!js
         {
          "package_count": 0,
          "distributionid": [],
          "consumer_cert": null,
          "consumer_ca": null,
          "filters": [],
          "last_sync": null,
          "id": "test_comps_import",
          "repomd_xml_path": "/var/lib/pulp//repos/test_comps_import/repodata/repomd.xml",
          "preserve_metadata": false,
          "group_xml_path": "",
          "publish": true,
          "source": null,
          "sync_in_progress": false,
          "packagegroups": {},
          "files": [],
          "relative_path": "test_comps_import",
          "arch": "noarch",
          "sync_schedule": null,
          "packages": [],
          "group_gz_xml_path": "",
          "feed_cert": null,
          "name": "test_comps_import",
          "uri_ref": "/pulp/api/repositories/test_comps_import/",
          "feed_ca": null,
          "notes": {},
          "groupid": [],
          "content_types": "yum",
          "clone_ids": [],
          "packagegroupcategories": {},
          "_ns": "repos",
          "release": null,
          "checksum_type": "sha256",
          "sync_options": {},
          "_id": "test_comps_import",
          "errata": {}
        }
        }}}
        """
        comps_data = self.params()
        return self.ok(repo_sync.import_comps(id, comps_data))

    def delete_packagegroup(self, id):
        """
        [[wiki]]
        title: Delete A Package Group
        description: Delete a package group from the repository.
        method: POST
        path: /repositories/<id>/delete_packagegroup/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * groupid, str, id of the package group
        example response:
        {{{
        #!js
        null
        }}}
        """
        p = self.params()
        if "groupid" not in p:
            return self.bad_request('No groupid specified')
        groupid = p["groupid"]
        return self.ok(api.delete_packagegroup(id, groupid))

    def create_packagegroupcategory(self, id):
        """
        [[wiki]]
        title: Create Package Group Category
        description: Create a new package group category in the repository.
        method: POST
        path: /repositories/<id>/create_packagegroupcategory/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: !PackageGroupCategory object
        parameters:
         * categoryid, str, package group category id
         * categoryname, str, package group category name
         * description, str, description of the package group category
        example response:
        {{{
        #!js
          {
          "description": "cat_descrp_1",
          "repo_defined": false,
          "display_order": 99,
          "translated_name": {},
          "packagegroupids": [],
          "translated_description": {},
          "id": "cat_id_1",
          "_id": "cat_id_1",
          "immutable": false,
          "name": "cat_name_1"
        }
        }}}
        """
        _log.info("create_packagegroupcategory invoked")
        p = self.params()
        if "categoryid" not in p:
            return self.not_found('No categoryid specified')
        categoryid = p["categoryid"]
        if "categoryname" not in p:
            return self.not_found('No categoryname specified')
        categoryname = p["categoryname"]
        if "description" not in p:
            return self.not_found('No description specified')
        descrp = p["description"]
        return self.ok(api.create_packagegroupcategory(id, categoryid, categoryname,
                                               descrp))

    def delete_packagegroupcategory(self, id):
        """
        [[wiki]]
        title: Delete Package Group Category
        description: Delete a package group category from the repository.
        method: POST
        path: /repositories/<id>/delete_packagegroupcategory/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * categoryid, str, package group category id
        example response:
        {{{
        #!js
        null
        }}}
        """
        _log.info("delete_packagegroupcategory invoked")
        p = self.params()
        if "categoryid" not in p:
            return self.bad_request('No categoryid specified')
        categoryid = p["categoryid"]
        return self.ok(api.delete_packagegroupcategory(id, categoryid))

    def add_packagegroup_to_category(self, id):
        """
        [[wiki]]
        title: Add Package Group To Category
        description: Add a package group to one of the repository's package group categories.
        method: POST
        path: /repositories/<id>/add_packagegroup_to_category/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * categoryid, str, package group category id
         * groupid, str, package group id
        example response:
        {{{
        #!js
        null
        }}}
        """
        _log.info("add_packagegroup_to_category invoked")
        p = self.params()
        if "categoryid" not in p:
            return self.bad_request("No categoryid specified")
        if "groupid" not in p:
            return self.bad_request('No groupid specified')
        groupid = p["groupid"]
        categoryid = p["categoryid"]
        return self.ok(api.add_packagegroup_to_category(id, categoryid, groupid))

    def delete_packagegroup_from_category(self, id):
        """
        [[wiki]]
        title: Delete Package Group From Category
        description: Delete a package group from one of the repository's package group categories.
        method: POST
        path: /repositories/<id>/delete_pacakgegroup_from_category/
        permission: EXECUTE
        success response: 200 OK
        failure response: 400 Bad Request if the required parameters are not present
                          404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * categoryid, str, package group category id
         * groupid, str, package group id
        example response:
        {{{
        #!js
        null
        }}}
        """
        _log.info("delete_packagegroup_from_category")
        p = self.params()
        if "categoryid" not in p:
            return self.not_found("No categoryid specified")
        if "groupid" not in p:
            return self.not_found('No groupid specified')
        groupid = p["groupid"]
        categoryid = p["categoryid"]
        return self.ok(api.delete_packagegroup_from_category(id, categoryid, groupid))

    def add_errata(self, id):
        """
        [[wiki]]
        title: Add Errata
        description: Add errata to the repository. This does not update metadata; call generate_metadata after this call.
        method: POST
        path: /repositories/<id>/add_errata/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: nil
        parameters:
         * errataid, str, errata id
        """
        data = self.params()
        for erratumid in data['errataid']:
            erratum = errataapi.erratum(erratumid)
            if erratum is None:
                return self.not_found("No Erratum with id: %s found" % erratumid)
        filtered_errata = api.add_errata(id, data['errataid'])
        return self.ok(filtered_errata)

    def delete_errata(self, id):
        """
        [[wiki]]
        title: Delete Errata
        description: Delete errata from the repository. This does not update metadata; call generate_metadata after this call.
        method: POST
        path: /repositories/<id>/delete_errata/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * errataid, str, errata id
        """
        data = self.params()
        api.delete_errata(id, data['errataid'])
        return self.ok(True)

    def add_file(self, id):
        """
        [[wiki]]
        title: Add File
        description: Add files to the repository.
        method: POST
        path: /repositories/<id>/add_file/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * fileids, list of str, list of file ids
        """
        data = self.params()
        api.add_file(id, data['fileids'])
        return self.ok(True)

    def remove_file(self, id):
        """
        [[wiki]]
        title: Remove File
        description: Remove files from the repository.
        method: POST
        path: /repositories/<id>/remove_file/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * fileids, list of str, list of file ids
        """
        data = self.params()
        api.remove_file(id, data['fileids'])
        return self.ok(True)

    def addkeys(self, id):
        """
        [[wiki]]
        title: Add Keys
        description: Add gpg keys to the repsository
        method: POST
        path: /repositories/<id>/addkeys/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * keylist, list of str binary lists, list of (key name, content) tuples
        """
        data = self.params()
        api.addkeys(id, data['keylist'])
        return self.ok(True)

    def get_package_by_nvrea(self, id):
        """
        [[wiki]]
        title: Get Package By NVREA
        description: Get packages from the repository by specifying package name, version, release, epoc, and architecture
        method: POST
        path: /repositories/<id>/get_package_by_nvrea/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: object of package file names to Package objects
        parameters:
         * nvrea, object, object fields: name, version, release, epoch, arch
        example:
        {{{
        #!js
         {'nvrea': {'name': 'pulp',
                    'version': '1.0.0',
                    'release': '2',
                    'epoch': '0',
                    'arch': 'x86_64'}
         }
        }}}
        """
        data = self.params()
        return self.ok(api.get_packages_by_nvrea(id, data['nvrea']))

    def get_package_by_filename(self, id):
        """
        [[wiki]]
        title: Get Package By File Name
        description: Get packages from the repository by specifying the file names.
        method: POST
        path: /repositories/<id>/get_package_by_filename/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: list of Package Objects
        parameters:
         * filename, list of str, list of file names
        """
        data = self.params()
        return self.ok(api.get_packages_by_filename(id, data['filename']))

    def rmkeys(self, id):
        """
        [[wiki]]
        title: Remove Keys
        description: Remove gpg keys from the repository.
        method: POST
        path: /repositories/<id>/rmkeys/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * keys list, list of str, list of key names to remove
        """
        data = self.params()
        api.rmkeys(id, data['keylist'])
        return self.ok(True)

    def add_filters(self, id):
        """
        [[wiki]]
        title: Add Filters
        description: Add filters to the repository.
        method: POST
        path: /repositories/<id>/add_filters/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * filters, list of str, list of filter ids
        """
        data = self.params()
        api.add_filters(id=id, filter_ids=data['filters'])
        return self.ok(True)

    def remove_filters(self, id):
        """
        [[wiki]]
        title: Remove Filters
        description: Remove filters from the repository.
        method: POST
        path: /repositories/<id>/remove_filters/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * filters, list of str, list of filter ids
        """
        data = self.params()
        api.remove_filters(id=id, filter_ids=data['filters'])
        return self.ok(True)

    def add_group(self, id):
        """
        [[wiki]]
        title: Add Group
        description: Add a group to the repository.
        method: POST
        path: /repositories/<id>/add_group/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * addgrp, str, group id
        """
        data = self.params()
        api.add_group(id=id, addgrp=data['addgrp'])
        return self.ok(True)

    def remove_group(self, id):
        """
        [[wiki]]
        title: Remove Group
        description: Remove a group from the repository.
        method: POST
        path: /repositories/<id>/remove_group/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: true
        parameters:
         * rmgrp, str, group id
        """
        data = self.params()
        api.remove_group(id=id, rmgrp=data['rmgrp'])
        return self.ok(True)

    def update_publish(self, id):
        """
        [[wiki]]
        title: Update Publish
        description: Update a repository's 'publish' state.
                     True means the repository is exposed through Apache.
                     False means to stop exposing from Apache.
        method: POST
        path: /repositories/<id>/update_publish/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: True on successful update, False otherwise
        parameters:
         * state, bool, puplish state
        """
        data = self.params()
        return self.ok(api.publish(id, bool(data['state'])))


    def export(self, id):
        """
        [[wiki]]
        title: Repository Content Export
        description: Export the repository's content into target directory from its source.
        method: POST
        path: /repositories/<id>/export/
        permission: EXECUTE
        success response: 202 Accepted
        failure response: 404 Not Found if the id does not match a repository
                          406 Not Acceptable if the repository does not have a source
                          409 Conflict if a export is already in progress for the repository
        return: a Task object
        parameters:
         * target_location, str, target location on the server filesystem where the content needs to be exported
         * generate_isos?, boolean, wrap the exported content into iso image files.
         * overwrite?, boolean, overwrite the content in target location if not empty
        """
        if api.repository(id, default_fields) is None:
           return self.not_found('A repository with the id, %s, does not exist' % id)
        export_params = self.params()
        target_location = export_params.get('target_location', None)
        generate_isos = export_params.get('generate_isos', False)
        overwrite = export_params.get('overwrite', False)
        # Check for valid target_location values
        try:
            exporter.validate_target_path(target_dir=target_location, overwrite=overwrite)
        except TargetExistsException:
            return self.bad_request("Target location [%s] already has content; must use overwrite to perform export." % target_location)
        except ExportException, ee:
            raise PulpException(str(ee))
        task = exporter.export(id, target_directory=target_location, generate_isos=generate_isos, overwrite=overwrite)
        if not task:
            return self.conflict('Export already in process for repo [%s]' % id)
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    def add_distribution(self, id):
        """
        [[wiki]]
        title: Add distributions to Repository
        description: Add distributions to repositories
        method: POST
        path: /repositories/<id>/add_distribution/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: True on successful add, False otherwise
        parameters:
         * distributionid, str, distribution id
        """
        data = self.params()
        api.add_distribution(id, data['distributionid'])
        return self.ok(True)

    def remove_distribution(self, id):
        """
        [[wiki]]
        title: remove distributions to Repository
        description: Remove distributions to repositories
        method: POST
        path: /repositories/<id>/remove_distribution/
        permission: EXECUTE
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a repository
        return: True on successful remove, False otherwise
        parameters:
         * distributionid, str, distribution id
        """
        data = self.params()
        api.remove_distribution(id, data['distributionid'])
        return self.ok(True)

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, id, action_name):
        """
        Action dispatcher. This method checks to see if the action is exposed,
        and if so, implemented. It then calls the corresponding method (named
        the same as the action) to handle the request.
        @type id: str
        @param id: repository id
        @type action_name: str
        @param action_name: name of the action
        @return: http response
        """
        repo = api.repository(id, fields=['id'])
        if not repo:
            return self.not_found('No repository with id %s found' % id)
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)

    @error_handler
    @auth_required(READ)
    def GET(self, id, action_name):
        """
        [[wiki]]
        title: List Actions
        description: Get a list of actions that were executed asynchronously on a repository.
        This method only works for actions that returned a 202 Accepted response.
        e.g. /repositories/my-repo/sync/
        method: GET
        path: /repositories/<id>/<action name>/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of Task objects
        """
        action_methods = {
            'sync': '_sync',
            '_sync': '_sync',
            'clone': '_clone',
            '_clone': '_clone',
            'generate_metadata' : '_generate_metadata',
            'export': '_export',
        }
        if action_name not in action_methods:
            return self.not_found('No information for %s on repository %s' %
                                 (action_name, id))
        tasks = [t for t in async.find_async(method_name=action_methods[action_name])
                 if (t.args and encode_unicode(id) in t.args) or
                 (t.kwargs and encode_unicode(id) in t.kwargs.values())]
        if not tasks:
            return self.not_found('No recent %s on repository %s found' %
                                 (action_name, id))
        task_infos = []
        for task in tasks:
            info = self._task_to_dict(task)
            task_infos.append(info)
        return self.ok(task_infos)


class Schedules(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        [[wiki]]
        title: Repository Synchronization Schedules
        description: List all repository synchronization schedules.
        method: GET
        path: /repositories/schedules/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of object that are mappings of repository id to synchronization schedule
        """
        # XXX this returns all scheduled tasks, it should only return those
        # tasks that are specified by the action_name
        schedules = api.all_schedules()
        return self.ok(schedules)


class RepositoryTaskHistory(JSONController):

    available_histories = (
        'sync',
    )

    def sync(self, id):
        return self.ok(task_history.repo_sync(id))

    @error_handler
    @auth_required(READ)
    def GET(self, id, action):
        """
        [[wiki]]
        title: Repository Action History
        description: List completed actions and their results for a repository.
        method: GET
        path: /repositories/<id>/history/<action name>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the repository does not exist or no action informaion is available
        return: list of task history objects
        """
        repo = api.repository(id, fields=['id'])
        if not repo:
            return self.not_found('No repository with id %s found' % id)
        method = getattr(self, action, None)
        if method is None:
            return self.not_found(_('No history availble for %s on %s') %
                                  (action, id))
        return method(id)

# web.py application ----------------------------------------------------------

urls = (
    '/$', 'Repositories',
    '/schedules/', 'Schedules',
    '/([^/]+)/$', 'Repository',

    '/([^/]+)/schedules/(%s)/' % '|'.join(SchedulesResource.schedule_types),
    SchedulesResource,

    '/([^/]+)/(%s)/$' % '|'.join(RepositoryDeferredFields.exposed_fields),
    'RepositoryDeferredFields',

    '/([^/]+)/(%s)/$' % '|'.join(RepositoryActions.exposed_actions),
    'RepositoryActions',

    '/([^/]+)/history/(%s)/$' % '|'.join(RepositoryTaskHistory.available_histories),
    'RepositoryTaskHistory',

    '/([^/]+)/notes/([^/]+)/$', 'RepositoryNotes',
    '/([^/]+)/notes/$', 'RepositoryNotesCollection',

    '/([^/]+)/statuses/$', 'RepositoryStatusesCollection',
    '/([^/]+)/statuses/([^/]+)/$', 'RepositorySyncStatus',
)

application = web.application(urls, globals())
