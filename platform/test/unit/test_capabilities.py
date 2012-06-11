#!/usr/bin/python
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

import base
from pulp.common.capabilities import *

class Robot(Capabilities):

    def __init__(self, capabilities={}):
        definitions = {
            0 : (bool, True),  # non-str key
            'on' : (bool, False),
            'age' : (int, 1),
            'songs' : ((list,tuple), ['Folsom Prision']),
        }
        Capabilities.__init__(self, definitions, capabilities)


class TestCapabilities(base.PulpServerTests):

    def test_happypath(self):
        cap = AgentCapabilities()
        cap = AgentCapabilities.default()
        # {bind:True, heartbeat:False}
        self.assertTrue(cap.bind())
        self.assertTrue(cap.heartbeat())
        # change using accessor method
        cap.bind(False)
        self.assertFalse(cap.bind())
        self.assertTrue(cap.heartbeat())
        # change/verify using []
        cap['heartbeat'] = False
        self.assertFalse(cap['bind'])
        self.assertFalse(cap['heartbeat'])
        # change using update()
        cap.update(bind=True)
        self.assertTrue(cap['bind'])
        self.assertFalse(cap['heartbeat'])
        # non-str keys
        cap = Robot()
        self.assertEqual(cap.age(), 1)
        cap.age(5)
        self.assertEqual(cap.age(), 5)
        # compound types
        cap.songs().append('Ring Of Fire')
        self.assertEqual(len(cap.songs()), 2)
        cap.songs(['Jail House Rock', 'Love Me Tender'])
        cap.songs(('All The Road Running', 'Staggerwing'))
        # __str__()
        str(cap)

    def test_failures(self):
        cap = AgentCapabilities.default()
        # unknown capability
        self.assertRaises(KeyError, AgentCapabilities, {'a':1})
        self.assertRaises(KeyError, cap.update, a=1)
        try:
            cap.xx()
        except AttributeError:
            pass
        try:
            cap.xx(True)
        except AttributeError:
            pass
        try:
            cap['xx']
        except KeyError:
            pass
        try:
            cap['xx'] = True
        except KeyError:
            pass

        # invalid value
        self.assertRaises(ValueError, AgentCapabilities, {'bind':1})
        self.assertRaises(ValueError, cap.update, bind=1)
        try:
            cap.bind(1)
        except ValueError:
            pass
        try:
            cap['bind'] = 10
        except ValueError:
            pass