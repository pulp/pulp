# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp.client.api.base import PulpAPI
from pulp.client.server.base import ServerRequestError


class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def create(self, id, name, arch, feed=None, symlinks=False,
               sync_schedule=None, cert_data=None, relative_path=None,
               groupid=None, gpgkeys=None):
        path = "/repositories/"
        repodata = {"id": id,
                    "name": name,
                    "arch": arch,
                    "feed": feed,
                    "use_symlinks": symlinks,
                    "sync_schedule": sync_schedule,
                    "cert_data": cert_data,
                    "relative_path": relative_path,
                    "groupid": groupid,
                    "gpgkeys": gpgkeys}
        return self.server.PUT(path, repodata)

    def repository(self, id, fields=[]):
        path = "/repositories/%s/" % str(id)
        repo = self.server.GET(path)
        if repo is None:
            return None
        for field in fields:
            repo[field] = self.server.GET('%s%s/' % (path, field))
        return repo

    def clone(self, repoid, clone_id, clone_name, feed='parent',
              relative_path=None, groupid=None, timeout=None):
        path = "/repositories/%s/clone/" % repoid
        data = {"clone_id": clone_id,
                "clone_name": clone_name,
                "feed": feed,
                "relative_path": relative_path,
                "groupid": groupid,
                "timeout": timeout}
        return self.server.POST(path, data)

    def repositories(self):
        path = "/repositories/"
        return self.server.GET(path)

    def repositories_by_groupid(self, groups=[]):
        path = "/repositories/?"
        for group in groups:
            path += "groupid=%s&" % group
        return self.server.GET(path)

    def update(self, repo):
        path = "/repositories/%s/" % repo['id']
        return self.server.PUT(path, repo)

    def delete(self, id):
        path = "/repositories/%s/" % id
        return self.server.DELETE(path)

    def clean(self):
        path = "/repositories/"
        return self.server.DELETE(path)

    def sync(self, repoid, skip={}, timeout=None):
        path = "/repositories/%s/sync/" % repoid
        return self.server.POST(path, {"timeout":timeout, "skip" : skip})

    def sync_list(self, repoid):
        path = '/repositories/%s/sync/' % repoid
        try:
            return self.server.GET(path)
        except ServerRequestError:
            return []

    def cancel_sync(self, repoid, taskid):
        path = "/repositories/%s/sync/%s/" % (repoid, taskid)
        return self.server.DELETE(path)

    def add_package(self, repoid, packageid):
        addinfo = {'repoid': repoid, 'packageid': packageid}
        path = "/repositories/%s/add_package/" % repoid
        return self.server.POST(path, addinfo)

    def remove_package(self, repoid, pkgobj=[]):
        rminfo = {'repoid': repoid, 'package': pkgobj, }
        path = "/repositories/%s/delete_package/" % repoid
        return self.server.POST(path, rminfo)

    def get_package(self, repoid, pkg_name):
        path = "/repositories/%s/get_package/" % repoid
        return self.server.POST(path, pkg_name)

    def find_package_by_nvrea(self, id, nvrea=[]):
        path = "/repositories/%s/get_package_by_nvrea/" % id
        return self.server.POST(path, {'nvrea' : nvrea})

    def get_package_by_filename(self, id, filename):
        path = "/repositories/%s/get_package_by_filename/" % id
        return self.server.POST(path, {'filename': filename})

    def packages(self, repoid):
        path = "/repositories/%s/packages/" % repoid
        return self.server.GET(path)

    def packagegroups(self, repoid):
        path = "/repositories/%s/packagegroups/" % repoid
        return self.server.GET(path)

    def packagegroupcategories(self, repoid):
        path = "/repositories/%s/packagegroupcategories/" % repoid
        return self.server.GET(path)

    def distribution(self, id):
        path = "/repositories/%s/distribution/" % id
        return self.server.GET(path)

    def create_packagegroup(self, repoid, groupid, groupname, description):
        path = "/repositories/%s/create_packagegroup/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "groupname": groupname,
                                       "description": description})

    def delete_packagegroup(self, repoid, groupid):
        path = "/repositories/%s/delete_packagegroup/" % repoid
        return self.server.POST(path, {"groupid":groupid})

    def add_packages_to_group(self, repoid, groupid, packagenames, gtype,
                              requires=None):
        path = "/repositories/%s/add_packages_to_group/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "packagenames": packagenames,
                                       "type": gtype,
                                       "requires": requires})

    def delete_package_from_group(self, repoid, groupid, pkgname, gtype):
        path = "/repositories/%s/delete_package_from_group/" % repoid
        return self.server.POST(path, {"groupid": groupid,
                                       "name": pkgname,
                                       "type": gtype})

    def create_packagegroupcategory(self, repoid, categoryid, categoryname,
                                    description):
        path = "/repositories/%s/create_packagegroupcategory/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "categoryname": categoryname,
                                       "description":description})

    def delete_packagegroupcategory(self, repoid, categoryid):
        path = "/repositories/%s/delete_packagegroupcategory/" % repoid
        return self.server.POST(path, {"categoryid":categoryid})

    def add_packagegroup_to_category(self, repoid, categoryid, groupid):
        path = "/repositories/%s/add_packagegroup_to_category/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "groupid": groupid})

    def delete_packagegroup_from_category(self, repoid, categoryid, groupid):
        path = "/repositories/%s/delete_packagegroup_from_category/" % repoid
        return self.server.POST(path, {"categoryid": categoryid,
                                       "groupid": groupid})

    def all_schedules(self):
        path = "/repositories/schedules/"
        return self.server.GET(path)

    def sync_status(self, status_path):
        return self.server.GET(str(status_path))

    def add_errata(self, id, errataids):
        erratainfo = {'repoid': id,
                      'errataid': errataids}
        path = "/repositories/%s/add_errata/" % id
        return self.server.POST(path, erratainfo)

    def delete_errata(self, id, errataids):
        erratainfo = {'repoid': id,
                      'errataid': errataids}
        path = "/repositories/%s/delete_errata/" % id
        return self.server.POST(path, erratainfo)

    def errata(self, id, types=[]):
        erratainfo = {'repoid': id,
                      'types': types}
        path = "/repositories/%s/list_errata/" % id
        return self.server.POST(path, erratainfo)

    def addkeys(self, id, keylist):
        params = dict(keylist=keylist)
        path = "/repositories/%s/addkeys/" % id
        return self.server.POST(path, params)

    def rmkeys(self, id, keylist):
        params = dict(keylist=keylist)
        path = "/repositories/%s/rmkeys/" % id
        return self.server.POST(path, params)

    def listkeys(self, id):
        path = "/repositories/%s/listkeys/" % id
        return self.server.POST(path, dict(x=1))

    def update_publish(self, id, state):
        path = "/repositories/%s/update_publish/" % id
        return self.server.POST(path, {"state": state})
