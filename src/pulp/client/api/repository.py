# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.client.api.base import PulpAPI
from pulp.client.api.server import ServerRequestError
from pulp.common import dateutils


repository_deferred_fields = ('packages',
                              'packagegroups',
                              'packagegroupcategories')


class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def create(self, id, name, arch, feed=None,
               feed_cert_data=None, consumer_cert_data=None,
               relative_path=None, groupid=None, gpgkeys=None, checksum_type="sha256",
               preserve_metadata=False, content_types="yum", publish=True):
        path = "/repositories/"
        repodata = {"id": id,
                    "name": name,
                    "arch": arch,
                    "feed": feed,
                    "feed_cert_data": feed_cert_data,
                    "consumer_cert_data": consumer_cert_data,
                    "relative_path": relative_path,
                    "groupid": groupid,
                    "gpgkeys": gpgkeys,
                    "checksum_type" : checksum_type,
                    "preserve_metadata" : preserve_metadata,
                    "content_types" : content_types,
                    "publish" : publish,}
        return self.server.PUT(path, repodata)[1]

    def repository(self, id, fields=()):
        path = "/repositories/%s/" % str(id)
        repo = self.server.GET(path)[1]
        if repo is None:
            return None
        for field in fields:
            repo[field] = self.server.GET('%s%s/' % (path, field))[1]
        return repo

    def clone(self, repoid, clone_id, clone_name, feed='parent',
              relative_path=None, groupid=None, timeout=None, filters=(), publish=True):
        path = "/repositories/%s/clone/" % repoid
        data = {"clone_id": clone_id,
                "clone_name": clone_name,
                "feed": feed,
                "relative_path": relative_path,
                "groupid": groupid,
                "timeout": timeout,
                "filters": filters,
                "publish": publish,}
        return self.server.POST(path, data)[1]

    def repositories(self, queries):
        path = "/repositories/"
        return self.server.GET(path, queries)[1]

    def repositories_by_groupid(self, group):
        path = "/repositories/"
        queries = [('groupid', group)]
        return self.server.GET(path, queries)[1]

    def update(self, id, delta):
        path = "/repositories/%s/" % id
        return self.server.PUT(path, delta)[1]

    def get_sync_schedule(self, id):
        path = '/repositories/%s/schedules/sync/' % id
        return self.server.GET(path)[1]

    def change_sync_schedule(self, id, new_schedule):
        path = '/repositories/%s/schedules/sync/' % id
        return self.server.PUT(path, new_schedule)[1]

    def delete_sync_schedule(self, id):
        path = '/repositories/%s/schedules/sync/' % id
        return self.server.DELETE(path)[1]

    def delete(self, id):
        path = "/repositories/%s/" % id
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/repositories/"
        return self.server.DELETE(path)[1]

    def sync(self, repoid, skip={}, timeout=None, limit=None, threads=None):
        path = "/repositories/%s/sync/" % repoid
        return self.server.POST(path, {"timeout":timeout, "skip" : skip, "limit":limit, "threads":threads})[1]

    def sync_list(self, repoid):
        path = '/repositories/%s/sync/' % repoid
        try:
            return self.server.GET(path)[1]
        except ServerRequestError:
            return []

    def clone_list(self, repoid):
        path = '/repositories/%s/clone/' % repoid
        try:
            return self.server.GET(path)[1]
        except ServerRequestError:
            return []

    def latest_task(self,task_list):
        """
        Iterate of a list of tasks and return the most recently finished task.
        @param task_list: list of tasks
        @return: most recent finished task, None if no task meets the criteria
        """
        def ft(t):
            return dateutils.parse_iso8601_datetime(t['finish_time'])
        def lt(a, b):
            if ft(a) > ft(b):
                return a
            return b
        finished_tasks = [t for t in task_list if t['finish_time'] is not None]
        if finished_tasks:
            return reduce(lt, finished_tasks)
        return None

    def running_task(self, task_list):
        """
        Iterate over a list of tasks and return one that is currently running or
        about to be run. If no such task is found, return None.
        """
        for task in task_list:
            if task['state'] == 'running':
                return task
            if task['state'] == 'waiting' and task['scheduler'] == 'immediate':
                return task
        return None

    def add_package(self, repoid, packageid):
        addinfo = {'repoid': repoid, 'packageid': packageid}
        path = "/repositories/%s/add_package/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_package(self, repoid, pkgobj=()):
        rminfo = {'repoid': repoid, 'package': pkgobj, }
        path = "/repositories/%s/delete_package/" % repoid
        return self.server.POST(path, rminfo)[1]

    def get_package(self, repoid, pkg_name):
        #path = "/repositories/%s/get_package/" % repoid
        #return self.server.POST(path, pkg_name)[1]
        path = '/repositories/%s/packages/' % repoid
        return self.server.GET(path, (('name', pkg_name),))[1]

    def find_package_by_nvrea(self, id, nvrea=()):
        path = "/repositories/%s/get_package_by_nvrea/" % id
        return self.server.POST(path, {'nvrea' : nvrea})[1]
        # FIXME newer call that's using correct controller, still needs testing
        #path = '/repositories/%s/packages/' % id
        #queries = []
        #for d in nvrea:
        #    queries.extend(d.items())
        #return self.server.GET(path, tuple(queries))[1]

    def get_package_by_filename(self, id, filename):
        path = "/repositories/%s/get_package_by_filename/" % id
        return self.server.POST(path, {'filename': filename})[1]
        # FIXME newer call that's using correct controller, still needs testing
        #path = '/repositories/%s/packages/' % id
        #return self.server.GET(path, (('filename', filename),))[1]

    def packages(self, repoid):
        path = "/repositories/%s/packages/" % repoid
        return self.server.GET(path)[1]

    def packagegroups(self, repoid, filter_missing_packages=False, filter_incomplete_groups=False):
        path = "/repositories/%s/packagegroups/" % repoid
        params = {}
        if filter_missing_packages:
            params["filter_missing_packages"] = True
        if filter_incomplete_groups:
            params["filter_incomplete_groups"] = True
        return self.server.GET(path, params)[1]

    def packagegroupcategories(self, repoid):
        path = "/repositories/%s/packagegroupcategories/" % repoid
        return self.server.GET(path)[1]

    def distribution(self, id):
        path = "/repositories/%s/distribution/" % id
        return self.server.GET(path)[1]

    def create_packagegroup(self, repoid, groupid, groupname, description):
        path = "/repositories/%s/create_packagegroup/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "groupname": groupname,
                                       "description": description})[1]

    def delete_packagegroup(self, repoid, groupid):
        path = "/repositories/%s/delete_packagegroup/" % repoid
        return self.server.POST(path, {"groupid":groupid})[1]

    def add_packages_to_group(self, repoid, groupid, packagenames, gtype,
                              requires=None):
        path = "/repositories/%s/add_packages_to_group/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "packagenames": packagenames,
                                       "type": gtype,
                                       "requires": requires})[1]

    def delete_package_from_group(self, repoid, groupid, pkgname, gtype):
        path = "/repositories/%s/delete_package_from_group/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "name": pkgname,
                                       "type": gtype})[1]

    def create_packagegroupcategory(self, repoid, categoryid, categoryname,
                                    description):
        path = "/repositories/%s/create_packagegroupcategory/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "categoryname": categoryname,
                                       "description":description})[1]

    def delete_packagegroupcategory(self, repoid, categoryid):
        path = "/repositories/%s/delete_packagegroupcategory/" % repoid
        return self.server.POST(path, {"categoryid":categoryid})[1]

    def add_packagegroup_to_category(self, repoid, categoryid, groupid):
        path = "/repositories/%s/add_packagegroup_to_category/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "groupid": groupid})[1]

    def delete_packagegroup_from_category(self, repoid, categoryid, groupid):
        path = "/repositories/%s/delete_packagegroup_from_category/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "groupid": groupid})[1]

    def all_schedules(self):
        path = "/repositories/schedules/"
        return self.server.GET(path)[1]

    def add_errata(self, id, errataids):
        erratainfo = {'repoid': id,
                      'errataid': errataids}
        path = "/repositories/%s/add_errata/" % id
        return self.server.POST(path, erratainfo)[1]

    def delete_errata(self, id, errataids):
        erratainfo = {'repoid': id,
                      'errataid': errataids}
        path = "/repositories/%s/delete_errata/" % id
        return self.server.POST(path, erratainfo)[1]

    def errata(self, id, type=None):
        path = "/repositories/%s/errata/" % id
        queries = []
        if type:
            queries = [('type', type)]
        return self.server.GET(path, queries)[1]

    def addkeys(self, id, keylist):
        params = dict(keylist=keylist)
        path = "/repositories/%s/addkeys/" % id
        return self.server.POST(path, params)[1]

    def rmkeys(self, id, keylist):
        params = dict(keylist=keylist)
        path = "/repositories/%s/rmkeys/" % id
        return self.server.POST(path, params)[1]

    def listkeys(self, id):
        path = "/repositories/%s/keys/" % id
        return self.server.GET(path)[1]

    def update_publish(self, id, state):
        path = "/repositories/%s/update_publish/" % id
        return self.server.POST(path, {"state": state})[1]

    def add_file(self, repoid, fileids=()):
        addinfo = {'repoid': repoid, 'fileids': fileids}
        path = "/repositories/%s/add_file/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_file(self, repoid, fileids):
        rminfo = {'repoid': repoid, 'fileids': fileids}
        path = "/repositories/%s/remove_file/" % repoid
        return self.server.POST(path, rminfo)[1]

    def list_files(self, repoid):
        path = "/repositories/%s/files/" % repoid
        return self.server.GET(path)[1]

    def import_comps(self, repoid, compsdata):
        path = "/repositories/%s/import_comps/" % repoid
        return self.server.POST(path, compsdata)[1]

    def export_comps(self, repoid):
        path = "/repositories/%s/comps/" % repoid
        return self.server.GET(path)[1]

    def add_filters(self, repoid, filters):
        addinfo = {'filters': filters}
        path = "/repositories/%s/add_filters/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_filters(self, repoid, filters):
        rminfo = {'filters': filters}
        path = "/repositories/%s/remove_filters/" % repoid
        return self.server.POST(path, rminfo)[1]

    def add_group(self, repoid, addgrp):
        addinfo = {'addgrp': addgrp}
        path = "/repositories/%s/add_group/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_group(self, repoid, rmgrp):
        rminfo = {'rmgrp': rmgrp}
        path = "/repositories/%s/remove_group/" % repoid
        return self.server.POST(path, rminfo)[1]

    def generate_metadata(self, repoid):
        path = "/repositories/%s/generate_metadata/" % repoid
        return self.server.POST(path)[1]

    def generate_metadata_status(self, repoid):
        path = '/repositories/%s/generate_metadata/' % repoid
        return self.server.GET(path)[1]

    def sync_history(self, repoid):
        path = "/repositories/%s/history/sync/" % repoid
        return self.server.GET(path)[1]

    def add_metadata(self, repoid, filetype, filedata):
        """
        add a custom metadata filetype to existing repository yum metadata
        @param repoid: Repository id.
        @type repoid: str
        @param filetype: file type info to identify metadata with eg: primary
        @type filetype: str
        @param filedata: filetype data stream read eg: open(<file-path>, 'r').read()
        @type filedata: str
        @return: True
        """
        path = "/repositories/%s/add_metadata/" % repoid
        fileinfo = {'filetype' : filetype,
                    'filedata' : filedata}
        return self.server.POST(path, fileinfo)[1]

    def download_metadata(self, repoid, filetype):
        """
        download metadata filetype xml from existing repository yum metadata
        @param repoid: Repository id.
        @type repoid: str
        @param filetype: file type info to identify metadata with eg: primary
        @type filetype: str
        @return: xml stream if metadata found or None
        """
        path = "/repositories/%s/download_metadata/" % repoid
        fileinfo = {'filetype' : filetype}
        return self.server.POST(path, fileinfo)[1]

    def list_metadata(self, repoid):
        """
        download metadata filetype xml from existing repository yum metadata
        @param repoid: Repository id.
        @type repoid: str
        @return: filetype information
        @rtype: dict
        """
        path = "/repositories/%s/list_metadata/" % repoid
        return self.server.POST(path)[1]

    def remove_metadata(self, repoid, filetype):
        """
        remove metadata filetype xml from existing repository yum metadata
        @param repoid: Repository id.
        @type repoid: str
        @param filetype: file type info to identify metadata with eg: primary
        @type filetype: str
        @return: True
        """
        path = "/repositories/%s/remove_metadata/" % repoid
        fileinfo = {'filetype' : filetype}
        return self.server.POST(path, fileinfo)[1]

    def export(self, repoid, target_location, generate_isos=False, overwrite=False):
        path = "/repositories/%s/export/" % repoid
        params = {"target_location" : target_location,
                  "generate_isos" : generate_isos,
                  "overwrite" : overwrite, }
        return self.server.POST(path, params)[1]

    def export_list(self, repoid):
        path = '/repositories/%s/export/' % repoid
        try:
            return self.server.GET(path)[1]
        except ServerRequestError:
            return []

    def add_distribution(self, repoid, distributionid):
        addinfo = {'repoid': repoid, 'distributionid': distributionid}
        path = "/repositories/%s/add_distribution/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_distribution(self, repoid, distributionid):
        delinfo = {'repoid': repoid, 'distributionid': distributionid}
        path = "/repositories/%s/remove_distribution/" % repoid
        return self.server.POST(path, delinfo)[1]

    def add_note(self, id, key, value):
        key_value_dict = {'key' : key, 'value' : value}
        path = "/repositories/%s/notes/" % id
        return self.server.POST(path, key_value_dict)[1]

    def delete_note(self, id, key):
        path = "/repositories/%s/notes/%s/" % (id, key)
        return self.server.DELETE(path)[1]

    def update_note(self, id, key, value):
        path = "/repositories/%s/notes/%s/" % (id, key)
        return self.server.PUT(path, value)[1]

