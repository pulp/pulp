# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import shutil
import tarfile
import tempfile

from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector


# Location where test databases are found
DB_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'db')

DEFAULT_SEEDS = 'localhost:27017'


class PulpTestDatabase(object):

    def __init__(self, db_name, seeds=DEFAULT_SEEDS):
        self.db_name = db_name
        self.seeds = seeds

    def load_from_file(self, filename):
        """
        Loads a database dump into a database in mongo with the name set to
        db_name. If the database does not exist it will be created.

        :param filename: full path to the gzipped database dump to load
        """

        if not os.path.exists(filename):
            raise Exception('No database export found at %s' % filename)

        # Extract the dump to a temporary location
        tmp_dir = tempfile.mkdtemp(prefix='pulp-test-database-export')
        tgz = tarfile.open(name=filename)
        tgz.extractall(path=tmp_dir)

        # Load into mongo
        cmd = '/usr/bin/mongorestore -d %s %s/pulp_database' % (self.db_name, tmp_dir)
        os.system(cmd)

        # Delete the extracted dump
        shutil.rmtree(tmp_dir)

    def delete(self):
        """
        Deletes the database from mongo.
        """
        connection = self._connection()
        connection.drop_database(self.db_name)

    def database(self):
        """
        Returns a connection to the given database.
        """
        connection = self._connection()
        database = getattr(connection, self.db_name)
        database.add_son_manipulator(NamespaceInjector())
        database.add_son_manipulator(AutoReference(database))
        return database

    def _connection(self):
        return Connection(self.seeds)
