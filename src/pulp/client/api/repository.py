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
from pulp.client.server import ServerRequestError


repository_deferred_fields = ('packages',
                              'packagegroups',
                              'packagegroupcategories')


class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def create(self, id, name, arch, feed=None, symlinks=False,
               sync_schedule=None, cert_data=None, relative_path=None,
               groupid=None, gpgkeys=None, checksum_type="sha256"):
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
                    "gpgkeys": gpgkeys,
                    "checksum_type" : checksum_type}
        return self.server.PUT(path, repodata)[1]

    def repository(self, id, fields=[]):
        path = "/repositories/%s/" % str(id)
        repo = self.server.GET(path)[1]
        if repo is None:
            return None
        for field in fields:
            repo[field] = self.server.GET('%s%s/' % (path, field))[1]
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
        return self.server.POST(path, data)[1]

    def repositories(self):
        path = "/repositories/"
        return self.server.GET(path)[1]

    def repositories_by_groupid(self, groups=[]):
        path = "/repositories/?"
        for group in groups:
            path += "groupid=%s&" % group
        return self.server.GET(path)[1]

    def update(self, repo):
        path = "/repositories/%s/" % repo['id']
        return self.server.PUT(path, repo)[1]

    def delete(self, id):
        path = "/repositories/%s/" % id
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/repositories/"
        return self.server.DELETE(path)[1]

    def sync(self, repoid, skip={}, timeout=None):
        path = "/repositories/%s/sync/" % repoid
        return self.server.POST(path, {"timeout":timeout, "skip" : skip})[1]

    def sync_list(self, repoid):
        path = '/repositories/%s/sync/' % repoid
        try:
            return self.server.GET(path)[1]
        except ServerRequestError:
            return []

    def cancel_sync(self, repoid, taskid):
        path = "/repositories/%s/sync/%s/" % (repoid, taskid)
        return self.server.DELETE(path)[1]

    def add_package(self, repoid, packageid):
        addinfo = {'repoid': repoid, 'packageid': packageid}
        path = "/repositories/%s/add_package/" % repoid
        return self.server.POST(path, addinfo)[1]

    def remove_package(self, repoid, pkgobj=[]):
        rminfo = {'repoid': repoid, 'package': pkgobj, }
        path = "/repositories/%s/delete_package/" % repoid
        return self.server.POST(path, rminfo)[1]

    def get_package(self, repoid, pkg_name):
        #path = "/repositories/%s/get_package/" % repoid
        #return self.server.POST(path, pkg_name)[1]
        path = '/repositories/%s/packages/' % repoid
        return self.server.GET(path, (('name', pkg_name),))[1]

    def find_package_by_nvrea(self, id, nvrea=[]):
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

    def packagegroups(self, repoid):
        path = "/repositories/%s/packagegroups/" % repoid
        return self.server.GET(path)[1]

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

    def errata(self, id, types=[]):
        path = "/repositories/%s/errata/" % id
        queries = [('type', t) for t in types]
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

    def add_file(self, repoid, fileids=[]):
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
    
    def import_comps(self, repoid, compsfile):
        compsobj = open(compsfile, 'r').read()
        path = "/repositories/%s/import_comps/" % repoid
        return self.server.POST(path, compsobj)[1]
    
    def export_comps(self, repoid):
        path = "/repositories/%s/comps/" % repoid
        return self.server.GET(path)[1]
