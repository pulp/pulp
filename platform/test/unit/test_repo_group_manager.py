# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import traceback

from base import PulpServerTests

from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repository import Repo, RepoGroup
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.repo import group


class RepoGroupManagerInstantiationTests(PulpServerTests):

    def test_constructor(self):
        try:
            RepoGroup('contructor_group')
        except:
            self.fail(traceback.format_exc())

    def test_factory(self):
        try:
            managers_factory.repo_group_manager()
        except:
            self.fail(traceback.format_exc())


class RepoGroupTests(PulpServerTests):

    def setUp(self):
        super(RepoGroupTests, self).setUp()
        self.manager = group.RepoGroupManager()

    def tearDown(self):
        super(RepoGroupTests, self).tearDown()
        self.manager = None
        Repo.get_collection().remove(safe=True)
        RepoGroup.get_collection().remove(safe=True)

    def _create_repo(self, repo_id):
        manager = managers_factory.repo_manager()
        return manager.create_repo(repo_id)


class RepoGroupCUDTests(PulpServerTests):

    def test_create(self):
        pass

    def test_create_duplicate_id(self):
        pass

    def test_update_display_name(self):
        pass

    def test_update_description(self):
        pass

    def test_update_notes(self):
        pass

    def test_delete(self):
        pass


class RepoGroupMembershipTests(PulpServerTests):

    def test_add_single(self):
        pass

    def test_remove_single(self):
        pass

    def test_delete_repo(self):
        pass

    def test_associate_id_regex(self):
        pass

    def test_unassociate_id_regex(self):
        pass

