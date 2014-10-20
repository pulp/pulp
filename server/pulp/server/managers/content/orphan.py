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

from celery import task

from pulp.plugins.types import database as content_types_db
from pulp.server import config as pulp_config, exceptions as pulp_exceptions
from pulp.server.async.tasks import Task
from pulp.server.db.model.repository import RepoContentUnit


logger = logging.getLogger(__name__)


class OrphanManager(object):

    def orphans_summary(self):
        """
        Return a summary of the orphaned units as a dictionary of
        content type -> number of orphaned units

        :return: summary of orphaned units
        :rtype: dict
        """
        summary = {}
        for content_type_id in content_types_db.all_type_ids():
            summary[content_type_id] = self.orphans_count_by_type(content_type_id)
        return summary

    def orphans_count_by_type(self, content_type_id):
        """
        Generate a count of the orphans of a given content type.

        :param content_type_id: unique id of the content type to count orphans of
        :type content_type_id: basestring
        :return: count of orphaned units of the given type
        :rtype: int
        """
        count = 0
        for unit in OrphanManager.generate_orphans_by_type(content_type_id):
            count += 1
        return count

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
            for content_unit in OrphanManager.generate_orphans_by_type(content_type_id, fields):
                yield content_unit

    def generate_all_orphans_with_unit_keys(self):
        """
        Return an generator of all orphaned content units.

        Each orphan will contain the fields specified in the content type
        definition's search indexes.

        :return: generator of orphaned content units
        :rtype: generator
        """

        for content_type_id in content_types_db.all_type_ids():
            for content_unit in OrphanManager.generate_orphans_by_type_with_unit_keys(
                    content_type_id):
                yield content_unit

    @staticmethod
    def generate_orphans_by_type(content_type_id, fields=None):
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

        fields = fields if fields is not None else ['_id']
        content_units_collection = content_types_db.type_units_collection(content_type_id)
        repo_content_units_collection = RepoContentUnit.get_collection()

        for content_unit in content_units_collection.find({}, fields=fields):

            repo_content_units_cursor = repo_content_units_collection.find(
                {'unit_id': content_unit['_id']})

            if repo_content_units_cursor.count() > 0:
                continue

            yield content_unit

    @staticmethod
    def generate_orphans_by_type_with_unit_keys(content_type_id):
        """
        Return an generator of all orphaned content units of the given content type.

        Each content unit will contain the fields specified in the content type
        definition's search indexes.

        :param content_type_id: id of the content type
        :type  content_type_id: basestring
        :return: generator of orphaned content units for the given content type
        :rtype: generator
        """
        content_type_definition = content_types_db.type_definition(content_type_id)
        if content_type_definition is None:
            raise pulp_exceptions.MissingResource(content_type_id=content_type_id)

        fields = ['_id', '_content_type_id']
        fields.extend(content_type_definition['unit_key'])

        for content_unit in OrphanManager.generate_orphans_by_type(content_type_id, fields):
            yield content_unit

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

        for content_unit in OrphanManager.generate_orphans_by_type(content_type_id):

            if content_unit['_id'] != content_unit_id:
                continue

            return content_unit

        raise pulp_exceptions.MissingResource(content_type=content_type_id,
                                              content_unit=content_unit_id)

    @staticmethod
    def delete_all_orphans():
        """
        Delete all orphaned content units.
        """

        for content_type_id in content_types_db.all_type_ids():
            OrphanManager.delete_orphans_by_type(content_type_id)

    @staticmethod
    def delete_orphans_by_id(content_unit_list):
        """
        Delete the given orphaned content units.

        Each content unit in the content unit list must be a mapping object with
        the fields `content_type_id` and `unit_id` present.

        :param content_unit_list: list of orphaned content units to delete
        :type content_unit_list: iterable of mapping objects
        """

        content_units_by_content_type = {}

        for content_unit in content_unit_list:
            if 'content_type_id' not in content_unit or 'unit_id' not in content_unit:
                raise pulp_exceptions.InvalidValue(['content_type_id', 'unit_id'])

            content_unit_id_list = content_units_by_content_type.setdefault(
                content_unit['content_type_id'], [])
            content_unit_id_list.append(content_unit['unit_id'])

        for content_type_id, content_unit_id_list in content_units_by_content_type.items():
            OrphanManager.delete_orphans_by_type(content_type_id, content_unit_id_list)


    @staticmethod
    def delete_orphans_by_type(content_type_id, content_unit_ids=None):
        """
        Delete the orphaned content units for the given content type.

        If the content_unit_ids parameter is not None, is acts as a filter of
        the specific orphaned content units that may be deleted.

        NOTE: this method deletes the content unit's bits from disk, if applicable.

        :param content_type_id: id of the content type
        :type content_type_id: basestring
        :param content_unit_ids: list of content unit ids to delete; None means delete them all
        :type content_unit_ids: iterable or None
        """

        content_units_collection = content_types_db.type_units_collection(content_type_id)

        for content_unit in OrphanManager.generate_orphans_by_type(content_type_id,
                                                                   fields=['_id', '_storage_path']):

            if content_unit_ids is not None and content_unit['_id'] not in content_unit_ids:
                continue

            content_units_collection.remove(content_unit['_id'], safe=False)

            storage_path = content_unit.get('_storage_path', None)
            if storage_path is not None:
                OrphanManager.delete_orphaned_file(storage_path)

    @staticmethod
    def delete_orphaned_file(path):
        """
        Delete an orphaned file and any parent directories that become empty.
        @param path: absolute path to the file to delete
        @type  path: str
        """
        logger.debug(_('Deleting orphaned file: %(p)s') % {'p': path})

        if not os.path.isabs(path):
            raise ValueError(_('Path: %(p)s must be absolute path') % {'p': path})

        storage_dir = pulp_config.config.get('server', 'storage_dir')

        # shared content
        if OrphanManager.is_shared(storage_dir, path):
            OrphanManager.unlink_shared(path)
            return

        OrphanManager.delete(path)

        # delete parent directories on the path as long as they fall empty
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

    @staticmethod
    def is_shared(storage_dir, path):
        """
        Determine specified path references shared storage.
        Here, the term *shared* indicates that multiple units share the
        same filesystem storage.  Shared storage is: <storage-dir>/content/shared.
        Shared storage layout:
          <storage-dir>/content/shared/*/
              |--content/
              |--links/
                   |--link1 --> ../content
                   |--link2 --> ../content
        :param storage_dir: The absolute path to the pulp content storage directory.
        :type storage_dir: str
        :param path: A unit storage path.
        :type path: str
        :return: True if references shared storage.
        """
        shared_root = os.path.join(os.path.normpath(storage_dir), 'content', 'shared')
        matched = os.path.normpath(path).startswith(shared_root) and \
            os.path.basename(os.path.dirname(path)) == 'links' and \
            os.path.islink(path)
        return matched

    @staticmethod
    def unlink_shared(path):
        """
        Unlink the specified shared storage.
        After all of the links have been removed, the link target is removed.
        :param path: The absolute path to a link.
        :type path: str
        :see: is_shared
        """
        path = os.path.normpath(path)
        ref_path = os.path.abspath(os.readlink(path))
        OrphanManager.delete(path)
        link_dir = os.path.dirname(path)
        if os.listdir(link_dir):
            # still used
            return
        if os.path.dirname(link_dir) != os.path.dirname(ref_path):
            # must be siblings
            return
        OrphanManager.delete(ref_path)

    @staticmethod
    def delete(path):
        """
        Delete the specified path.
        File and links are unlinked.  Directories are recursively deleted.
        Exceptions are logged and discarded.
        :param path: An absolute path.
        :type path: str
        """
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)
        except OSError, e:
            logger.error(_('Delete path: %(p)s failed: %(m)s'), {'p': path, 'm': str(e)})


delete_all_orphans = task(OrphanManager.delete_all_orphans, base=Task, ignore_result=True)
delete_orphans_by_id = task(OrphanManager.delete_orphans_by_id, base=Task, ignore_result=True)
delete_orphans_by_type = task(OrphanManager.delete_orphans_by_type, base=Task, ignore_result=True)
