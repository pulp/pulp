# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module contains tests for the pulp.server.db.model.consumer module.
"""

import unittest

import mock

from base import PulpServerTests
from pulp.server.db.model import consumer


class TestRepoProfileApplicability(PulpServerTests):
    """
    Test the RepoProfileApplicability Model.
    """
    def setUp(self):
        self.collection = consumer.RepoProfileApplicability.get_collection()

    def tearDown(self):
        self.collection.drop()

    def test___init___no__id(self):
        """
        Test the constructor without passing an _id.
        """
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}

        applicability = consumer.RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data)

        self.assertEqual(applicability.profile_hash, profile_hash)
        self.assertEqual(applicability.repo_id, repo_id)
        self.assertEqual(applicability.profile, profile)
        self.assertEqual(applicability.applicability, applicability_data)
        # Since we didn't set an _id, it should be None
        self.assertEqual(applicability._id, None)

    def test___init___with__id(self):
        """
        Test the constructor with an _id.
        """
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}
        _id = 'an ID'

        applicability = consumer.RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data, _id=_id)

        self.assertEqual(applicability.profile_hash, profile_hash)
        self.assertEqual(applicability.repo_id, repo_id)
        self.assertEqual(applicability.profile, profile)
        self.assertEqual(applicability.applicability, applicability_data)
        # Since we didn't set an _id, it should be None
        self.assertEqual(applicability._id, _id)

    def test_delete(self):
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}
        # Start by making a RepoProfileApplicability object
        applicability = consumer.RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data)
        # At this point, there should be nothing in the database
        self.assertEqual(self.collection.find().count(), 0)
        # Saving the model should store it in the database
        applicability.save()
        # Now, we have our one object in the DB
        self.assertEqual(self.collection.find().count(), 1)

        # Calling delete() on the object should "take care" of it, if you know what I mean
        applicability.delete()

        # Now there should be no objects
        self.assertEqual(self.collection.find().count(), 0)

    def test_save_existing(self):
        """
        Test the save() method with an existing object.
        """
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}
        # Start by making a RepoProfileApplicability object
        applicability = consumer.RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data)
        # At this point, there should be nothing in the database
        self.assertEqual(self.collection.find().count(), 0)
        # Saving the model should store it in the database
        applicability.save()
        # Now, let's alter the applicability data a bit
        applicability_data['new_type_id'] = ['package d']
        applicability.applicability = applicability_data

        # Saving the object should write the changes to the DB
        applicability.save()

        # There should be one entry in the DB
        self.assertEqual(self.collection.find().count(), 1)
        document = self.collection.find_one()
        self.assertEqual(document['profile_hash'], profile_hash)
        self.assertEqual(document['repo_id'], repo_id)
        self.assertEqual(document['profile'], profile)
        self.assertEqual(document['applicability'], applicability_data)

        # Our applicability object should still have the correct _id attribute
        self.assertEqual(applicability._id, document['_id'])

    def test_save_new(self):
        """
        Test the save() method with a new object that is not in the DB yet.
        """
        profile_hash = 'hash'
        repo_id = 'repo_id'
        profile = ['a', 'profile']
        applicability_data = {'type_id': ['package a', 'package c']}
        # Start by making a RepoProfileApplicability object
        applicability = consumer.RepoProfileApplicability(
            profile_hash=profile_hash, repo_id=repo_id, profile=profile,
            applicability=applicability_data)
        # At this point, there should be nothing in the database
        self.assertEqual(self.collection.find().count(), 0)

        # Saving the model should store it in the database
        applicability.save()

        # There should now be one entry in the DB
        self.assertEqual(self.collection.find().count(), 1)
        document = self.collection.find_one()
        self.assertEqual(document['profile_hash'], profile_hash)
        self.assertEqual(document['repo_id'], repo_id)
        self.assertEqual(document['profile'], profile)
        self.assertEqual(document['applicability'], applicability_data)

        # Our applicability object should now have the correct _id attribute
        self.assertEqual(applicability._id, document['_id'])

class TestUnitProfile(unittest.TestCase):
    """
    Test the UnitProfile class.
    """
    @mock.patch('pulp.server.db.model.consumer.Model.__init__', side_effect=consumer.Model.__init__,
                autospec=True)
    def test___init__(self, __init__):
        """
        Test the constructor.
        """
        profile = consumer.UnitProfile('consumer_id', 'content_type', 'profile')

        self.assertEqual(profile.consumer_id, 'consumer_id')
        self.assertEqual(profile.content_type, 'content_type')
        self.assertEqual(profile.profile, 'profile')
        self.assertEqual(profile.profile_hash, profile.calculate_hash(profile.profile))

        # The superclass __init__ should have been called
        __init__.assert_called_once_with(profile)

    @mock.patch('pulp.server.db.model.consumer.Model.__init__', side_effect=consumer.Model.__init__,
                autospec=True)
    def test___init___with_hash(self, __init__):
        """
        Test the constructor, passing the optional profile_hash
        """
        profile = consumer.UnitProfile('consumer_id', 'content_type', 'profile', 'profile_hash')

        self.assertEqual(profile.consumer_id, 'consumer_id')
        self.assertEqual(profile.content_type, 'content_type')
        self.assertEqual(profile.profile, 'profile')
        self.assertEqual(profile.profile_hash, 'profile_hash')

        # The superclass __init__ should have been called
        __init__.assert_called_once_with(profile)

    def test_calculate_hash_different_profiles(self):
        """
        Test that two different profiles have different hashes.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'libestr',  'epoch': 0, 'version': '0.1.5',
             'release': '1.fc18', 'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'openssh-clients', 'epoch': 0, 'version': '6.1p1',
             'release': '8.fc18', 'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'procps-ng', 'epoch': 0, 'version': '3.3.3',
             'release': '4.20120807git.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                            consumer.UnitProfile.calculate_hash(profile_2.profile))

    def test_calculate_hash_identical_profiles(self):
        """
        Test that the hashes of two identical profiles are equal.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                         consumer.UnitProfile.calculate_hash(profile_2.profile))

    def test_calculate_hash_non_ascii_identical_profiles(self):
        """
        Test that the hashes of two identical profiles that include non-ASCII characters are equal.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': u'¿Donde esta el baño?', 'epoch': 0,
             'version': '1.49', 'release': '1.fc18',   'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': u'¿Donde esta el baño?', 'epoch': 0,
             'version': '1.49', 'release': '1.fc18',   'arch': 'x86_64'}])

        self.assertEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                         consumer.UnitProfile.calculate_hash(profile_2.profile))

    def test_calculate_hash_non_ascii_non_identical_profiles(self):
        """
        Test that the hashes of two non-identical profiles that include non-ASCII characters are
        not equal.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': u'¿Donde esta el baño?', 'epoch': 0,
             'version': '1.49', 'release': '1.fc18',   'arch': 'x86_64'}])
        # profile_2 has the codepoints for the two Spanish characters above, so this test ensures
        # that this is considered to be different
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': '\u00bfDonde esta el ba\u00f1o?', 'epoch': 0,
             'version': '1.49', 'release': '1.fc18',   'arch': 'x86_64'}])

        self.assertNotEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                         consumer.UnitProfile.calculate_hash(profile_2.profile))

    def test_calculate_hash_reordered_profiles(self):
        """
        Test that the hashes of two equivalent, but differently ordered profile lists are not the same.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                            consumer.UnitProfile.calculate_hash(profile_2.profile))

    def test_calculate_hash_similar_profiles(self):
        """
        Test hashing "similar" profiles to make sure they get different results.
        """
        profile_1 = consumer.UnitProfile('consumer_1', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '1.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])
        # profile_2 is almost the same as profile_1, but it has a different release on the python-slip-dbus
        # package
        profile_2 = consumer.UnitProfile('consumer_2', 'rpm', [
            {'vendor': 'Fedora Project', 'name': 'perl-Filter', 'epoch': 0, 'version': '1.49',
             'release': '1.fc18',   'arch': 'x86_64'},
            {'vendor': 'Fedora Project', 'name': 'python-slip-dbus', 'epoch': 0, 'version': '0.4.0',
             'release': '2.fc18', 'arch': 'noarch'},
            {'vendor': 'Fedora Project', 'name': 'kmod', 'epoch': 0, 'version': '12',
             'release': '3.fc18', 'arch': 'x86_64'}])

        self.assertNotEqual(consumer.UnitProfile.calculate_hash(profile_1.profile),
                            consumer.UnitProfile.calculate_hash(profile_2.profile))
