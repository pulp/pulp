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
# Contains mock agent content handlers.
#

import os
import shutil

#
# Handlers
#

RPM = dict(
name='RPM Handler',
descriptor="""
[main]
enabled=1
types=rpm

[rpm]
class=RpmHandler
""",
handler=
"""
from pulp.client.consumer.agent.dispatcher import HandlerReport
class RpmHandler:
  def __init__(self, cfg):
    pass
  def install(self, units, options):
    return HandlerReport()
  def update(self, units, options):
    return HandlerReport()
  def uninstall(self, units, options):
    return HandlerReport()
  def profile(self):
    {}
""")

#
# Mock
#

class MockInstaller:

    ROOT = '/tmp/etc/agent/handler'
    PATH = ['/tmp/usr/lib/agent/handler',]

    def install(self):
        for path in (self.ROOT, self.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path)
        for handler in (RPM,):
            self.deploy(handler)
    
    def clean(self):
        for path in (self.ROOT, self.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)
    
    def deploy(self, handler):
        name = handler['name']
        fn = '.'.join((name, 'conf'))
        path = os.path.join(self.ROOT, fn)
        f = open(path, 'w')
        f.write(handler['descriptor'])
        f.close()
        fn = '.'.join((name, 'py'))
        path = os.path.join(self.PATH[0], fn)
        f = open(path, 'w')
        f.write(handler['handler'])
        f.close()