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
from pulp.gc_client.agent.lib.report import *

#
# Handlers to be deployed for loader testing
#

RPM = dict(
name='RPM Handler',
descriptor="""
[main]
enabled=1

[types]
system=Linux
content=rpm
bind=yum

[rpm]
class=RpmHandler

[yum]
class=YumHandler

[Linux]
class=LinuxHandler
""",
handler=
"""
from pulp.gc_client.agent.lib.handler import *
from pulp.gc_client.agent.lib.report import *

class RpmHandler(ContentHandler):

  def install(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def update(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def uninstall(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def profile(self):
    return ProfileReport()

class YumHandler(BindHandler):

  def bind(self, info):
    report = BindReport()
    report.succeeded({}, 1)
    return report

  def rebind(self, info):
    report = BindReport()
    report.succeeded({}, 1)
    return report

  def unbind(self, info):
    report = BindReport()
    report.succeeded({}, 1)
    return report

  def clean(self):
    report = CleanReport()
    report.succeeded({}, 1)
    return report

class LinuxHandler(SystemHandler):

  def reboot(self, options):
    report = RebootReport()
    report.succeeded()
    return report
""")

#
# Mock Deployer
#

class MockDeployer:

    ROOT = '/tmp/etc/agent/handler'
    PATH = ['/tmp/usr/lib/agent/handler',]

    def deploy(self):
        for path in (self.ROOT, self.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path)
        for handler in (RPM,):
            self.__deploy(handler)
    
    def clean(self):
        for path in (self.ROOT, self.PATH[0]):
            shutil.rmtree(path, ignore_errors=True)
    
    def __deploy(self, handler):
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

#
# Mock Handlers
#

class RpmHandler:

  def __init__(self, cfg=None):
    pass

  def install(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def update(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def uninstall(self, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def profile(self):
    report = ProfileReport()
    return report

  def reboot(self, options={}):
    report = RebootReport()
    report.succeeded()
    return report

  def bind(self, info):
    return BindReport()

  def rebind(self, info):
    return BindReport()

  def unbind(self, info):
    return BindReport()