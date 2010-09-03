#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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

# Python
import os
import sys
import unittest

from pymongo.errors import DuplicateKeyError

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp
from pulp.server import updateinfo
from pulp.server.api.errata import ErrataApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.package import PackageApi
from pulp.server.util import get_rpm_information
from pulp.client.utils import generatePakageProfile
import testutil

class TestErrata(unittest.TestCase):

    def clean(self):
        self.eapi.clean()
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()

    def setUp(self):
        self.config = testutil.load_test_config()
        self.data_path = \
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.eapi = ErrataApi()
        self.rapi = RepoApi()
        self.capi = ConsumerApi()
        self.papi = PackageApi()
        self.clean()

    def tearDown(self):
        self.clean()

    def test_parse_updateinfo_xml(self):
        # Test against expected updateinfo.xml from RHEL 5 i386
        updateinfo_path = os.path.join(self.data_path, "rhel-i386-server-5")
        updateinfo_path = os.path.join(updateinfo_path, "updateinfo.xml")
        notices = updateinfo.get_update_notices(updateinfo_path)
        self.assertTrue(len(notices) == 1504)
        expectedKeys = ['status', 'updated', 'description', 'issued',
                'pushcount', 'update_id', 'from', 'title', 'version',
                'release', 'references', 'reboot_suggested', 'type',
                'pkglist']
        for example in notices:
            for key in expectedKeys:
                self.assertTrue(key in example.keys())
            # Check 'references'
            refs = example['references']
            if len(refs) > 0:
                expectedRefKeys = ['href', 'id', 'type', 'title']
                for r in refs:
                    for key in expectedRefKeys:
                        self.assertTrue(key in r.keys())
            # Check 'pkglist'
            pkglist = example['pkglist']
            if len(pkglist) > 0:
                expectedPkgListKeys = ['src', 'name', 'sum', 'filename',
                        'epoch', 'version', 'release', 'arch']
                for p in pkglist:
                    self.assertTrue(p['name'] ==
                            "Red Hat Enterprise Linux (v. 5 for 32-bit x86)")
                    self.assertTrue(p['short'] == 'rhel-i386-server-5')
                    if len(p['packages']) > 0:
                        for pkg in p['packages']:
                            for key in expectedPkgListKeys:
                                self.assertTrue(key in pkg.keys())


    def test_get_errata(self):
        updateinfo_path = os.path.join(self.data_path, "rhel-i386-server-5")
        updateinfo_path = os.path.join(updateinfo_path, "updateinfo.xml")
        errata = updateinfo.get_errata(updateinfo_path)
        self.assertTrue(len(errata) == 1504)


    def test_create(self):
        id = 'test_create_errata_id'
        title = 'test_create_title'
        description = 'test_create_description'
        version = '1.0'
        release = '0'
        type = 'test_create_type'
        status = 'test_create_status'
        updated = 'test_create_status'
        issued = 'test_create_issued'
        pushcount = 'test_create_pushcount'
        from_str = 'test_create_from_str'
        reboot_suggested = 'test_create_reboot_suggested'
        references = ['test_create_references']
        pkglist = [{'packages':{'src':'test_src'}}]
        sample_errata = self.eapi.create(id, title, description, version, release,
                type, status=status, updated=updated, issued=issued,
                pushcount=pushcount, from_str=from_str,
                reboot_suggested=reboot_suggested, references=references,
                pkglist=pkglist)
        assert(sample_errata is not None)
        self.assertTrue(sample_errata["id"] == id)
        self.assertTrue(sample_errata["title"] == title)
        self.assertTrue(sample_errata["description"] == description)
        self.assertTrue(sample_errata["version"] == version)
        self.assertTrue(sample_errata["release"] == release)
        self.assertTrue(sample_errata["type"] == type)
        self.assertTrue(sample_errata["status"] == status)
        self.assertTrue(sample_errata["updated"] == updated)
        self.assertTrue(sample_errata["issued"] == issued)
        self.assertTrue(sample_errata["pushcount"] == pushcount)
        self.assertTrue(sample_errata["from_str"] == from_str)
        self.assertTrue(sample_errata["reboot_suggested"] == reboot_suggested)
        self.assertTrue(sample_errata["references"] == references)
        self.assertTrue(sample_errata["pkglist"] == pkglist)

    def test_duplicate(self):
        id = 'test_duplicate_id'
        sample_errata = self.eapi.create(id, None, None, None, None, None)
        assert(sample_errata is not None)
        # Should fail since we already created an exact copy of this.
        exception_caught = False
        try:
            sample_errata = self.eapi.create(id, None, None, None, None, None)
        except DuplicateKeyError:
            exception_caught = True
        self.assertTrue(exception_caught)
        # Explicit test, all that needs to be unique is id
        no_exception = True
        try:
            sample_errata = self.eapi.create("new-id", None, None, None, None, None)
        except DuplicateKeyError:
            no_exception = False
        self.assertTrue(no_exception)

    def test_clean(self):
        id = 'test_clean_id'
        sample_errata = self.eapi.create(id, None, None, None, None, None)
        self.assertTrue(sample_errata is not None)
        found = self.eapi.erratum(id)
        self.assertTrue(found is not None)
        self.eapi.clean()
        found = self.eapi.erratum(id)
        self.assertTrue(found is None)

    def test_delete(self):
        id = 'test_delete_id'
        sample_errata = self.eapi.create(id, None, None, None, None, None)
        self.assertTrue(sample_errata is not None)
        found = self.eapi.erratum(id)
        self.assertTrue(found is not None)
        self.eapi.delete(id)
        found = self.eapi.erratum(id)
        self.assertTrue(found is None)

    def test_update(self):
        id = 'test_update_id'
        title = "valueA"
        sample_errata = self.eapi.create(id, title, None, None, None, None)
        self.assertTrue(sample_errata is not None)
        found = self.eapi.erratum(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['title'] == title)
        new_title = "B"
        found['title'] = new_title
        self.eapi.update(found)
        found = self.eapi.erratum(id)
        self.assertTrue(found is not None)
        self.assertTrue(found['title'] == new_title)

    def test_erratum_lookup(self):
        id = 'test_erratatum_id'
        title = 'test_erratum_title'
        description = 'test_erratum_description'
        version = '1.0'
        release = '0'
        type = 'test_erratum_type'
        sample_errata = self.eapi.create(id, title, description, version, release,
                type)
        assert(sample_errata is not None)
        found = self.eapi.erratum(id="bad_id")
        self.assertTrue(found is None)
        found = self.eapi.erratum(id=id)
        self.assertTrue(found is not None)
        self.assertTrue(found['id'] == id)
        self.assertTrue(found['title'] == title)
        self.assertTrue(found['description'] == description)
        self.assertTrue(found['version'] == version)
        self.assertTrue(found['release'] == release)
        self.assertTrue(found['type'] == type)

    def test_errata_lookup(self):
        id_a = 'test_errata_id_a'
        id_b = 'test_errata_id_b'
        title = 'test_errata_title'
        description = 'test_errata_description'
        version = '1.0'
        release = '0'
        type_a = 'test_errata_type_a'
        type_b = 'test_errata_type_b'
        # Create 2 errata with different ids and type
        sample_errata = self.eapi.create(id_a, title, description, version, release,
                type_a)
        assert(sample_errata is not None)
        sample_errata = self.eapi.create(id_b, title, description, version, release,
                type_b)
        assert(sample_errata is not None)
        found = self.eapi.errata()
        self.assertTrue(len(found) == 2)
        found = self.eapi.errata(title=title, description=description, version=version,
                release=release)
        self.assertTrue(len(found) == 2)
        for f in found:
            self.assertTrue(f['id'] in [id_a, id_b])
            self.assertTrue(f['title'] == title)
            self.assertTrue(f['description'] == description)
            self.assertTrue(f['version'] == version)
            self.assertTrue(f['release'] == release)
            self.assertTrue(f['type'] in [type_a, type_b])
        # Nattow search to specific type, expect 1 match
        found = self.eapi.errata(title=title, description=description, version=version,
                release=release, type=type_b)
        self.assertTrue(len(found) == 1)
        # Add a type that doesn't exist, expect no matches
        found = self.eapi.errata(title=title, description=description, version=version,
                release=release, type="bad value")
        self.assertTrue(len(found) == 0)
        
    def test_repo_erratum(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)

        self.assertTrue(test_errata_1 is not None)
        self.rapi.add_erratum(repo['id'], test_errata_1['id'])

        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 1)
        
        self.rapi.delete_erratum(repo['id'], test_errata_1['id'])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 0)
        
    def test_repo_errata(self):
        repo = self.rapi.create('some-id','some name', \
            'i386', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_1 is not None)
        
        id = 'test_errata_id_2'
        title = 'test_errata_title_2'
        description = 'test_errata_description_2'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_2 = self.eapi.create(id, title, description, version, release, type)
        self.assertTrue(test_errata_2 is not None)
        self.rapi.add_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 2)

        self.rapi.delete_errata(repo['id'], [test_errata_1['id'], test_errata_2['id']])
        
        errata = self.rapi.errata('some-id', types=['test_errata_type'])
        self.assertTrue(len(errata) == 0)
        
    def test_consumer_errata(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        repo = self.rapi.create('some-id','some name', \
            'x86_64', 'yum:http://example.com')
        id = 'test_errata_id_1'
        title = 'test_errata_title_1'
        description = 'test_errata_description_1'
        version = '1.0'
        release = '0'
        type = 'test_errata_type'
        test_errata_1 = self.eapi.create(id, title, description, version, release, type)
        assert(test_errata_1 is not None)
        
        epkg = get_rpm_information(my_dir + "/data/pulp-test-package-0.3.1-1.fc11.x86_64.rpm")
        test_pkg_name = epkg["name"]
        test_epoch = epkg["epoch"]
        test_version = epkg["version"]
        test_release = epkg["release"]
        test_arch = epkg["arch"]
        test_description = "test description text"
        test_checksum_type = "sha256"
        test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
        test_filename = 'test-filename-0.3.1-1.fc11.x86_64.rpm'
        p = self.papi.create(name=test_pkg_name, epoch=test_epoch, version=test_version, 
                release=test_release, arch=test_arch, description=test_description, 
                checksum_type="sha256", checksum=test_checksum, filename=test_filename)
        print "Package! %s" % p
        # Add this package version to the repo
        self.rapi.add_package(repo["id"], p['id'])
        self.rapi.update(repo)
        test_errata_1["pkglist"] = [{"packages" : [{'src': 'http://download.fedoraproject.org/pub/fedora/linux/updates/11/x86_64/pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                                                    'name': 'pulp-test-package', 
                                                    'filename': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm', 
                                                    'epoch': '0', 'version': '0.3.1', 'release': '1.fc11', 
                                                    'arch': 'x86_64'}]}]
        self.eapi.update(test_errata_1)
        repo["errata"] = {"security" : [test_errata_1['id']]}

        cid = 'test-consumer'
        c = self.capi.create(cid, 'some consumer desc')
        self.assertTrue(c is not None)

        info1 = get_rpm_information(my_dir + \
                        "/data/pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        info2 = get_rpm_information(my_dir + \
                        "/data/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm")
        
        packages = generatePakageProfile([info1, info2])
        c['package_profile'] = packages
        self.assertTrue(c['package_profile'] is not None)
        self.capi.update(c)

        self.rapi.update(repo)
        c["repoids"] = [repo['id']]
        self.capi.update(c)

        errlist = self.capi.listerrata(c['id'], types=['security'])
        assert(len(errlist) == 1)
        
        pkguplist = self.capi.list_package_updates(c['id'])
        assert(len(pkguplist) == 1)

    def test_errata_repo_sync_rhel(self):
        datadir = os.path.join(self.data_path, "repo_rhel_sample")
        r = self.rapi.create("test_errata_repo_sync", "test_name", "x86_64",
                "local:file://%s" % datadir)
        self.rapi.sync(r['id'])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        enhancement = [u'RHEA-2009:1270', u'RHEA-2007:0637', u'RHEA-2007:0636',
                        u'RHEA-2007:0635', u'RHEA-2009:1302', u'RHEA-2009:1269',
                        u'RHEA-2008:0467', u'RHEA-2007:0643', u'RHEA-2008:0371']
        security = [u'RHSA-2008:0194', u'RHSA-2009:0003', u'RHSA-2007:0114',
                    u'RHSA-2009:1472', u'RHSA-2009:0382', u'RHSA-2008:0892',
                    u'RHSA-2007:0323']
        bugfix = ['RHBA-2008:0279', u'RHBA-2008:0291', u'RHBA-2010:0281',
                    u'RHBA-2010:0222', u'RHBA-2009:0118', u'RHBA-2010:0010',
                    u'RHBA-2008:0026', u'RHBA-2009:1514', u'RHBA-2010:0282',
                    u'RHBA-2008:0198', u'RHBA-2009:1412', u'RHBA-2010:0205',
                    u'RHBA-2008:0480', u'RHBA-2009:1299', u'RHBA-2007:0611',
                    u'RHBA-2010:0251', u'RHBA-2009:0140', u'RHBA-2009:0141',
                    u'RHBA-2009:1092', u'RHBA-2009:1328', u'RHBA-2009:0216',
                    u'RHBA-2008:0280', u'RHBA-2009:0142', u'RHBA-2010:0294',
                    u'RHBA-2008:0554', u'RHBA-2008:0433', u'RHBA-2008:0305',
                    u'RHBA-2008:0189', u'RHBA-2009:0401', u'RHBA-2010:0418',
                    u'RHBA-2009:1421', u'RHBA-2009:1424', u'RHBA-2009:1285',
                    u'RHBA-2009:0137', u'RHBA-2010:0206', u'RHBA-2007:0112']
        self.assertTrue(len(r['errata']['enhancement']) == len(enhancement))
        self.assertTrue(len(r['errata']['security']) == len(security))
        self.assertTrue(len(r['errata']['bugfix']) == len(bugfix))
        for erratum in enhancement:
            self.assertTrue(erratum in r['errata']['enhancement'])
            self.assertTrue(self.eapi.erratum(erratum) is not None)
        for erratum in security:
            self.assertTrue(erratum in r['errata']['security'])
            self.assertTrue(self.eapi.erratum(erratum) is not None)
        for erratum in bugfix:
            self.assertTrue(erratum in r['errata']['bugfix'])
            self.assertTrue(self.eapi.erratum(erratum) is not None)

    def test_errata_repo_resync(self):
        # We shall sync a repo
        # Simulate an errata is deleted and another errata is updated
        # Verify the deleted errata is not in the repo
        # The info from the updated errata is present
        repo_path = os.path.join(self.data_path, "repo_resync_a")
        r = self.rapi.create('test_errata_repo_resync',
                'test_errata_repo_resync_name', 'i386',
                'local:file://%s' % (repo_path))
        self.assertTrue(r != None)
        self.rapi.sync(r["id"])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        #LOOK UP ERRATA AND VERIFY
        enhancement = [u'RHEA-2009:1270', u'RHEA-2007:0637', u'RHEA-2007:0636',
                        u'RHEA-2007:0635', u'RHEA-2009:1302', u'RHEA-2009:1269',
                        u'RHEA-2008:0467', u'RHEA-2007:0643', u'RHEA-2008:0371']
        security = [u'RHSA-2008:0194', u'RHSA-2009:0003', u'RHSA-2007:0114',
                    u'RHSA-2009:1472', u'RHSA-2009:0382', u'RHSA-2008:0892',
                    u'RHSA-2007:0323']
        bugfix = ['RHBA-2008:0279', u'RHBA-2008:0291', u'RHBA-2010:0281',
                    u'RHBA-2010:0222', u'RHBA-2009:0118', u'RHBA-2010:0010',
                    u'RHBA-2008:0026', u'RHBA-2009:1514', u'RHBA-2010:0282',
                    u'RHBA-2008:0198', u'RHBA-2009:1412', u'RHBA-2010:0205',
                    u'RHBA-2008:0480', u'RHBA-2009:1299', u'RHBA-2007:0611',
                    u'RHBA-2010:0251', u'RHBA-2009:0140', u'RHBA-2009:0141',
                    u'RHBA-2009:1092', u'RHBA-2009:1328', u'RHBA-2009:0216',
                    u'RHBA-2008:0280', u'RHBA-2009:0142', u'RHBA-2010:0294',
                    u'RHBA-2008:0554', u'RHBA-2008:0433', u'RHBA-2008:0305',
                    u'RHBA-2008:0189', u'RHBA-2009:0401', u'RHBA-2010:0418',
                    u'RHBA-2009:1421', u'RHBA-2009:1424', u'RHBA-2009:1285',
                    u'RHBA-2009:0137', u'RHBA-2010:0206', u'RHBA-2007:0112']
        self.assertTrue(len(r['errata']['enhancement']) == len(enhancement))
        self.assertTrue(len(r['errata']['security']) == len(security))
        self.assertTrue(len(r['errata']['bugfix']) == len(bugfix))

        found = self.eapi.errata(id="RHSA-2008:0194")
        self.assertTrue(len(found) == 1)
        not_found_777777 = True
        not_found_350421 = True
        for ref in found[0]["references"]:
            if ref["id"] == "777777":
                not_found_777777 = False
            if ref["id"] == "350421":
                not_found_350421 = False
        self.assertTrue(not_found_777777)
        self.assertFalse(not_found_350421)
        # Simulate a change to 'updateinfo' from repo source
        # Changes:  removed 'RHBA-2009:1092'
        #           modified RHSA-2008:0194
        #            Original UPDATED Date = '2008-05-13 00:00:00'
        #            Changing to '2010-08-30'
        #            Adding a new bugzilla entry: 777777
        #            Removing old entry: bugzilla 350421
        #           added a new category, 'development'
        repo_path = os.path.join(self.data_path, "repo_resync_b")
        r = self.rapi.repository(r["id"])
        r["source"] = pulp.server.db.model.RepoSource("local:file://%s" % (repo_path))
        self.rapi.update(r)
        self.rapi.sync(r["id"])
        #Refresh Repo Object and Verify Changes
        r = self.rapi.repository(r["id"])
        self.assertTrue(len(r['errata']['enhancement']) == len(enhancement))
        self.assertTrue(len(r['errata']['security']) == len(security))
        # One bugfix errata was deleted, so make sure this is reflected
        self.assertTrue(len(r['errata']['bugfix']) == (len(bugfix) - 1))
        self.assertTrue("RHBA-2009:1092" not in r['errata']['bugfix'])
        # Verify updated errata info
        self.assertTrue("RHSA-2008:0194" in r['errata']['security'])
        not_found_777777 = True
        not_found_350421 = True
        found = self.eapi.errata(id="RHSA-2008:0194")
        for ref in found[0]["references"]:
            if ref["id"] == "777777":
                not_found_777777 = False
            if ref["id"] == "350421":
                not_found_350421 = False
        self.assertFalse(not_found_777777)
        self.assertTrue(not_found_350421)


    def test_errata_query_by_cve(self):
        datadir = os.path.join(self.data_path, "repo_rhel_sample")
        r = self.rapi.create("test_errata_query_by_cve", "test_name", "x86_64",
                "local:file://%s" % datadir)
        self.rapi.sync(r['id'])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        found = self.eapi.query_by_cve("CVE-2007-3919")
        self.assertTrue(len(found) == 1)
        self.assertTrue(found[0] == 'RHSA-2008:0194')

    def test_errata_query_by_bz(self):
        datadir = os.path.join(self.data_path, "repo_rhel_sample")
        r = self.rapi.create("test_errata_query_bz", "test_name", "x86_64",
                "local:file://%s" % datadir)
        self.rapi.sync(r['id'])
        # Refresh object now it's been sync'd
        r = self.rapi.repository(r['id'])
        found = self.eapi.query_by_bz("433560")
        self.assertTrue(len(found) == 1)
        self.assertTrue(found[0] == 'RHSA-2008:0194')
