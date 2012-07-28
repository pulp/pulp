# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import os
import re
from gettext import gettext as _

from pulp.server import config as pulp_config
from pulp.plugins.types import database as content_types_db
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.managers import factory as manager_factory


_LOG = logging.getLogger(__name__)


class OrphanManager(object):

    def list_all_orphans(self):
        """
        List all content units that are not associated with a repository.
        @return: list of content units
        @rtype:  list
        """

        # iterate through all types and get the orphaned units for each
        orphaned_units = []
        content_query_manager = manager_factory.content_query_manager()
        content_types = content_query_manager.list_content_types()
        for content_type in content_types:
            orphaned_units_of_type = self.list_orphans_by_type(content_type)
            orphaned_units.extend(orphaned_units_of_type)
        return orphaned_units

    def list_orphans_by_type(self, content_type):
        """
        List all content units of a given type that are not associated with a repository.
        @param content_type: content type of orphaned units
        @type  content_type: str
        @return: list of content units of the given type
        @rtype:  list
        """

        # find units of this type that are associated with one or more repositories
        associated_collection = RepoContentUnit.get_collection()
        associated_units = associated_collection.find({'unit_type_id': content_type}, fields=['unit_id'])
        associated_unit_ids = set(d['unit_id'] for d in associated_units)

        # find units that are not associated with any repositories
        units_collection = content_types_db.type_units_collection(content_type)
        spec = {'_id': {'$nin': list(associated_unit_ids)}}
        orphaned_units = units_collection.find(spec)
        return list(orphaned_units)

    def get_orphan(self, content_type, content_id):
        """
        Get a single orphaned content unit.
        @param content_type: content type of the orphan
        @type  content_type: str
        @param content_id: content id of the orphan
        @type  content_id: str
        """
        orphans = self.list_orphans_by_type(content_type)
        for orphan in orphans:
            if content_id != orphan['_id']:
                continue
            return orphan
        raise pulp_exceptions.MissingResource(content_type=content_type, content_id=content_id)

    def delete_all_orphans(self):
        """
        Delete all orphaned content units.
        """

        # iterate through the types and delete all orphans of each type
        content_query_manager = manager_factory.content_query_manager()
        content_types = content_query_manager.list_content_types()
        for content_type in content_types:
            self.delete_orphans_by_type(content_type)

    def delete_orphans_by_type(self, content_type):
        """
        Delete all orphaned content units of the given content type.
        @param content_type: content type of the orphans to delete
        @type  content_type: str
        """

        orphaned_units = self.list_orphans_by_type(content_type)
        if not orphaned_units:
            return
        collection = content_types_db.type_units_collection(content_type)
        spec = {'_id': {'$in': [o['_id'] for o in orphaned_units]}}
        collection.remove(spec, safe=True)
        orphaned_paths = [o['_storage_path'] for o in orphaned_units if o['_storage_path'] is not None]
        for path in orphaned_paths:
            self.delete_orphaned_file(path)

    def delete_orphans_by_id(self, orphans):
        """
        Delete a list of orphaned content units by their content type and unit ids.
        @param orphans: list of documents with 'content_type' and 'content_id' keys
        @type  orphans: list
        """
        # XXX this does no validation of the orphans

        # munge the orphans into something more programmatic-ly convenient
        orphans_by_id = {}
        for o in orphans:
            if 'content_type_id' not in o or 'unit_id' not in o:
                raise pulp_exceptions.InvalidValue(['content_type_id', 'unit_id'])
            id_list = orphans_by_id.setdefault(o['content_type_id'], [])
            id_list.append(o['unit_id'])

        # iterate through the types and ids
        content_query_manager = manager_factory.content_query_manager()
        for content_type, content_id_list in orphans_by_id.items():

            # build a list of the on-disk contents
            orphaned_paths = []
            for unit_id in content_id_list:
                content_unit = content_query_manager.get_content_unit_by_id(content_type, unit_id, model_fields=['_storage_path'])
                if content_unit['_storage_path'] is not None:
                    orphaned_paths.append(content_unit['_storage_path'])

            # remove the orphans from the db
            collection = content_types_db.type_units_collection(content_type)
            spec = {'_id': {'$in': content_id_list}}
            collection.remove(spec, safe=True)

            # delete the on-disk contents
            for path in orphaned_paths:
                self.delete_orphaned_file(path)

    def delete_orphaned_file(self, path):
        """
        Delete an orphaned file and any parent directories that become empty.
        @param path: absolute path to the file to delete
        @type  path: str
        """
        assert os.path.isabs(path)

        _LOG.debug(_('Deleting orphaned file: %(p)s') % {'p': path})

        if not os.path.exists(path):
            _LOG.warn(_('Cannot delete orphaned file: %(p)s, No such file') % {'p': path})
            return

        if not os.access(path, os.W_OK):
            _LOG.warn(_('Cannot delete orphaned file: %(p)s, Insufficient permissions') % {'p': path})
            return

        os.unlink(path)

        # delete parent directories on the path as long as they fall empty
        storage_dir = pulp_config.config.get('server', 'storage_dir')
        root_content_regex = re.compile(os.path.join(storage_dir, 'content', '[^/]+/?'))
        while True:
            path = os.path.dirname(path)
            if root_content_regex.match(path):
                break
            contents = os.listdir(path)
            if contents:
                break
            if not os.access(path, os.W_OK):
                break
            os.rmdir(path)

