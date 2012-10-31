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

from pulp.agent.lib.report import *
from pulp.agent.lib.conduit import Conduit

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
xxx=hello
yyy=world

[yum]
class=YumHandler

[Linux]
class=LinuxHandler
""",
handler=
"""
from pulp.agent.lib.handler import *
from pulp.agent.lib.report import *
from pulp.agent.lib.conduit import *

class RpmHandler(ContentHandler):

  def install(self, conduit, units, options):
    assert(self.cfg['xxx'] == 'hello')
    assert(self.cfg['yyy'] == 'world')
    assert(isinstance(conduit, Conduit))
    assert(isinstance(units, list))
    assert(isinstance(options, dict))
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def update(self, conduit, units, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(units, list))
    assert(isinstance(options, dict))
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def uninstall(self, conduit, units, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(units, list))
    assert(isinstance(options, dict))
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def profile(self, conduit):
    assert(isinstance(conduit, Conduit))
    return ProfileReport()

class YumHandler(BindHandler):

  def bind(self, conduit, binding, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(binding, dict))
    assert(isinstance(options, dict))
    assert('repo_id' in binding)
    assert('details' in binding)
    report = BindReport(binding['repo_id'])
    report.succeeded({}, 1)
    return report

  def unbind(self, conduit, repo_id, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(repo_id, str))
    assert(isinstance(options, dict))
    report = UnbindReport(repo_id)
    report.succeeded({}, 1)
    return report

  def clean(self, conduit):
    assert(isinstance(conduit, Conduit))
    report = CleanReport()
    report.succeeded({}, 1)
    return report

class LinuxHandler(SystemHandler):

  def reboot(self, conduit, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(options, dict))
    report = RebootReport()
    report.succeeded()
    return report
""")

SECTION_MISSING = dict(
name='Test section not found',
descriptor="""
[main]
enabled=1
[types]
content=puppet
""",
handler="""
class A: pass
""")

CLASS_NDEF = dict(
name='Test class property missing',
descriptor="""
[main]
enabled=1
[types]
content=puppet
[puppet]
foo=bar
""",
handler="""
class A: pass
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
        for handler in (RPM, SECTION_MISSING, CLASS_NDEF):
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

  def install(self, conduit, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def update(self, conduit, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def uninstall(self, conduit, units, options):
    report = HandlerReport()
    report.succeeded({}, len(units))
    return report

  def profile(self, conduit):
    report = ProfileReport()
    return report

  def reboot(self, conduit, options):
    report = RebootReport()
    report.succeeded()
    return report

  def bind(self, conduit, definitions):
    return BindReport()

  def rebind(self, conduit, definitions):
    return BindReport()

  def unbind(self, conduit, repo_id):
    return BindReport()