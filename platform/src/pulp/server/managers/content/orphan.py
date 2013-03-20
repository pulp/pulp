# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
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
import shutil
from gettext import gettext as _

from pulp.plugins.types import database as content_types_db
from pulp.server import config as pulp_config
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import connection as db_connection
from pulp.server.db.model.repository import RepoContentUnit


_LOG = logging.getLogger(__name__)


class OrphanManager(object):

    # generator-based api ------------------------------------------------------

    def generate_all_orphans(self, fields=None):
        """
        Return an generator of all orphaned content units.

        If fields is not specified, only the `_id` field will be present.

        :param fields: list of fields to include in each content unit
        :type fields: list or None
        :return: generator of orphaned content units
        :rtype: generator
        """

        for content_type_id in content_types_db.all_type_ids():
            for content_unit in self.generate_orphans_by_type(content_type_id, fields):
                yield content_unit

    def generate_all_orphans_with_search_indexes(self):
        """
        Return an generator of all orphaned content units.

        Each orphan will contain the fields specified in the content type
        definition's search indexes.

        :return: generator of orphaned content units
        :rtype: generator
        """

        for content_type_id in content_types_db.all_type_ids():
            for content_unit in self.generate_orphans_by_type_with_search_indexes(content_type_id):
                yield content_unit

    def generate_orphans_by_type(self, content_type_id, fields=None):
        """
        Return an generator of all orphaned content units of the given content type.

        If fields is not specified, only the `_id` field will be present.

        :param content_type_id: id of the content type
        :type content_type_id: basestring
        :param fields: list of fields to include in each content unit
        :type fields: list or None
        :return: generator of orphaned content units for the given content type
        :rtype: generator
        """

        # XXX (jconnor 2013-03-19) this overrides pymongo's notion that None is
        # equivalent to all fields; but do we care?
        fields = fields if fields is not None else ['_id']
        content_units_collection = content_types_db.type_units_collection(content_type_id)
        repo_content_units_collection = RepoContentUnit.get_collection()

        for content_unit in content_units_collection.find({}, fields=fields):

            repo_content_units_cursor = repo_content_units_collection.find({'unit_id': content_unit['_id']})

            if repo_content_units_cursor.count() > 0:
                continue

            yield content_unit

    def generate_orphans_by_type_with_search_indexes(self, content_type_id):
        """
        Return an generator of all orphaned content units of the given content type.

        Each content unit will contain the fields specified in the content type
        definition's search indexes.

        :param content_type_id: id of the content type
        :type content_type_id: basestring
        :return: generator of orphaned content units for the given content type
        :rtype: generator
        """
        content_type_definition = content_types_db.type_definition(content_type_id)
        fields = ['_content_type_id']
        fields.extend(content_type_definition['search_indexes'])

        for content_unit in self.generate_orphans_by_type(content_type_id, fields):
            yield  content_unit

    def get_orphan(self, content_type_id, content_unit_id):
        """
        Look up a single orphaned content unit by content type and unit id.

        :param content_type_id: id of the content type
        :type content_type_id: basestring
        :param content_unit_id: id of the content unit
        :type content_unit_id: basestring
        :return: orphaned content unit
        :rtype: SON
        :raises MissingResource: if no orphaned content unit corresponds to the
                                 given content type and unit id
        """

        for content_unit in self.generate_orphans_by_type(content_type_id):

            if content_unit['_id'] != content_unit_id:
                continue

            return content_unit

        raise pulp_exceptions.MissingResource(content_type=content_type_id, content_unit=content_unit_id)

    def delete_all_orphans(self, flush=True):
        """
        Delete all orphaned content units.

        :param flush: flush the database updates to disk on completion
        :type flush: bool
        """

        for content_type_id in content_types_db.all_type_ids():
            self.delete_orphans_by_type(content_type_id, flush=False)

        if flush:
            db_connection.flush_database()

    def delete_orphans_by_id(self, content_unit_list, flush=True):
        """
        Delete the given orphaned content units.

        Each content unit in the content unit list must be a mapping object with
        the fields `content_type_id` and `unit_id` present.

        :param content_unit_list: list of orphaned content units to delete
        :type content_unit_list: iterable of mapping objects
        :param flush: flush the database updates to disk on completion
        :type flush: bool
        """

        content_units_by_content_type = {}

        for content_unit in content_unit_list:
            if 'content_type_id' not in content_unit or 'unit_id' not in content_unit:
                raise pulp_exceptions.InvalidValue(['content_type_id', 'unit_id'])

            content_unit_id_list = content_units_by_content_type.setdefault(content_unit['content_type_id'], [])
            content_unit_id_list.append(content_unit['unit_id'])

        for content_type_id, content_unit_id_list in content_units_by_content_type.items():
            self.delete_orphans_by_type(content_type_id, content_unit_id_list, flush=False)

        if flush:
            db_connection.flush_database()

    def delete_orphans_by_type(self, content_type_id, content_unit_ids=None, flush=True):
        """
        Delete the orphaned content units for the given content type.

        If the content_unit_ids parameter is not None, is acts as a filter of
        the specific orphaned content units that may be deleted.

        NOTE: this method deletes the content unit's bits from disk, if applicable.

        :param content_type_id: id of the content type
        :type content_type_id: basestring
        :param content_unit_ids: list of content unit ids to delete; None means delete them all
        :type content_unit_ids: iterable or None
        :param flush: flush the database updates to disk on completion
        :type flush: bool
        """

        content_units_collection = content_types_db.type_units_collection(content_type_id)

        for content_unit in self.generate_orphans_by_type(content_type_id, fields=['_storage_path']):

            if content_unit_ids is not None and content_unit['_id'] not in content_unit_ids:
                continue

            content_units_collection.remove(content_unit['_id'], safe=False)

            storage_path = content_unit.get('_storage_path', None)
            if storage_path is not None:
                self.delete_orphaned_file(storage_path)

        # this forces the database to flush any cached changes to the disk
        # in the background; for example: the unsafe deletes in the loop above
        if flush:
            db_connection.flush_database()

    # physical bits utility ----------------------------------------------------

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

        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

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

