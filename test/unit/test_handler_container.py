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
#

import os
import sys
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.client.consumer.agent.container import *


Descriptor.ROOT = '/tmp/etc/agent/handler'
Container.PATH = ['/tmp/usr/lib/agent/handler',]

HANDLER_A = dict(
name='handlerA',
descriptor="""
[main]
enabled=1
types=rpm

[rpm]
class=RpmHandler
""",
handler=
"""
class RpmHandler:
  def __init__(self, cfg):
    pass
  def install(units, options):
    pass
  def update(units, options):
    pass
  def uninstall(units, options):
    pass
  def profile():
    pass
""")



class TestHandlerContainer(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)
        for path in (Descriptor.ROOT, Container.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path)


    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        for path in (Descriptor.ROOT, Container.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)

    def deploy(self, handler):
        name = handler['name']
        fn = '.'.join((name, 'conf'))
        path = os.path.join(Descriptor.ROOT, fn)
        f = open(path, 'w')
        f.write(handler['descriptor'])
        f.close()
        fn = '.'.join((name, 'py'))
        path = os.path.join(Container.PATH[0], fn)
        f = open(path, 'w')
        f.write(handler['handler'])
        f.close()

    def test_loading(self):
        self.deploy(HANDLER_A)
        container = Container()
        container.load()
        handler = container.find('rpm')
        self.assertTrue(handler is not None)