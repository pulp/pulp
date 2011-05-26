#!/usr/bin/env python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import sys
import unittest
import logging
import os
import time

from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector


class TestDbRefs(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        connection = Connection()
        connection.drop_database("_test_dbrefs")

    def testRemoveWithRef(self):
        """
        Remove a collection object while it is referenced in a 
        separate collection.  Use of AutoReference causes the external
        reference to become None, reflecting the object was deleted.
        """
        connection = Connection()
        db = connection._test_dbrefs
        db.add_son_manipulator(NamespaceInjector())
        db.add_son_manipulator(AutoReference(db))
        db.drop_collection("books")
        db.drop_collection("groups")
        books = db.books
        groups = db.groups
        # Create book-1
        bk1 = {}
        bk1["name"] = "Test-A"
        bk1["created-time"] = time.time()
        books.save(bk1)
        # Create group-1
        grp1 = {}
        grp1["name"] = "FirstGroup"
        grp1["books"] = [bk1]
        groups.save(grp1)
        
        # lookup 'Test-A', then delete it
        b = books.find_one({"name":"Test-A"})
        books.remove(b)
        found = [f for f in books.find({"name": "Test-A"})]
        self.assertTrue(len(found) == 0)

        found = [f for f in groups.find({"name": "FirstGroup"})]
        self.assertTrue(len(found) == 1)
        self.assertTrue(found[0]["name"] == "FirstGroup")
        self.assertTrue(len(found[0]["books"]) == 1)
        self.assertTrue(found[0]["books"][0] == None)

    
    def testChangesWithRef(self):
        """
        Change a collection object while it is referenced in 
        another collection, use AutoReference Manipulator so 
        the change is reflected.
        """
        connection = Connection()
        db = connection._test_dbrefs
        #manipulators are required to keep references in sync
        db.add_son_manipulator(NamespaceInjector())
        db.add_son_manipulator(AutoReference(db))
        db.drop_collection("books")
        db.drop_collection("groups")
        books = db.books
        groups = db.groups
        # Create book-1
        bk1 = {}
        bk1["name"] = "Test-A"
        bk1["created-time"] = time.time()
        books.save(bk1)
        # Create group-1
        grp1 = {}
        grp1["name"] = "FirstGroup"
        grp1["books"] = [bk1]
        groups.save(grp1)

        #Ensure that we have only 1 instance in each books/groups
        found = [f for f in books.find({"name": "Test-A"})]
        self.assertTrue(len(found) == 1)
        bk1_id = found[0]["_id"]
        found = [f for f in groups.find({"name": "FirstGroup"})]
        self.assertTrue(len(found) == 1)
        # Verify that we saved 'Test-A' under groups
        self.assertTrue(len(found[0]["books"]) == 1)
        self.assertTrue(found[0]["books"][0]["name"] == 'Test-A')
        self.assertTrue(found[0]["books"][0]["_id"] == bk1_id)

        # lookup 'Test-A', save it (no-modifications), ensure we still have only 
        # 1 instance of 'Test-A'
        b = books.find_one({"name":"Test-A"})
        books.save(b)
        found = [f for f in books.find({"name": "Test-A"})]
        self.assertTrue(len(found) == 1)

        # lookup 'Test-A' and modify it and save it, ensure we only have
        # 1 instance of 'Test-A'
        b = books.find_one({"name":"Test-A"})
        b["newEntry"] = "newValue"
        b["modified_time"] = time.time()
        books.save(b)
        found = [f for f in books.find({"name": "Test-A"})]
        self.assertTrue(len(found) == 1)
        # Ensure _id didn't change after our modification
        self.assertTrue(found[0]["_id"] == bk1_id)


        found = [f for f in groups.find({"name": "FirstGroup"})]
        self.assertTrue(len(found) == 1)
        self.assertTrue(found[0]["name"] == "FirstGroup")
        self.assertTrue(found[0]["books"][0]["_id"] == bk1_id)
        self.assertTrue(found[0]["books"][0].has_key("newEntry"))
        self.assertTrue(found[0]["books"][0]["newEntry"] == "newValue")

    def testChangeWithRefFails(self):
        """
        Default behavior of changing a collection object while it 
        is referenced in an external collection.  The change is not 
        reflected in the external object.
        """
        connection = Connection()
        db = connection._test_dbrefs
        db.drop_collection("books")
        db.drop_collection("groups")
        books = db.books
        groups = db.groups
        # Create book-1
        bk1 = {}
        bk1["name"] = "Test-A"
        bk1["created-time"] = time.time()
        books.save(bk1)
        # Create group-1
        grp1 = {}
        grp1["name"] = "FirstGroup"
        grp1["books"] = [bk1]
        groups.save(grp1)

        # lookup 'Test-A' and modify it and save it
        b = books.find_one({"name":"Test-A"})
        b["newEntry"] = "newValue"
        b["modified_time"] = time.time()
        books.save(b)

        found = [f for f in groups.find({"name": "FirstGroup"})]
        self.assertTrue(len(found) == 1)
        self.assertTrue(found[0]["name"] == "FirstGroup")
        self.assertTrue(len(found[0]["books"]) == 1)
        self.assertFalse(found[0]["books"][0].has_key("newEntry"))




