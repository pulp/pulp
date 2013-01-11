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


PACKAGE = 'test.handlers'

#
# Handlers to be deployed for loader testing
#

# -- Mock RPM Handler --------------------------------------------------------------------

RPM = dict(
name='rpm',
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
    report.set_succeeded({}, len(units))
    return report

  def update(self, conduit, units, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(units, list))
    assert(isinstance(options, dict))
    report = HandlerReport()
    report.set_succeeded({}, len(units))
    return report

  def uninstall(self, conduit, units, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(units, list))
    assert(isinstance(options, dict))
    report = HandlerReport()
    report.set_succeeded({}, len(units))
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
    report.set_succeeded({}, 1)
    return report

  def unbind(self, conduit, repo_id, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(repo_id, str))
    assert(isinstance(options, dict))
    report = BindReport(repo_id)
    report.set_succeeded({}, 1)
    return report

  def clean(self, conduit):
    assert(isinstance(conduit, Conduit))
    report = CleanReport()
    report.set_succeeded({}, 1)
    return report

class LinuxHandler(SystemHandler):

  def reboot(self, conduit, options):
    assert(isinstance(conduit, Conduit))
    assert(isinstance(options, dict))
    report = RebootReport()
    report.set_succeeded()
    return report
""")


# -- Mock SRPM Handler -------------------------------------------------------------------
# note: loading into site-packages

SRPM = dict(
name='srpm',
descriptor="""
[main]
enabled=1

[types]
content=srpm

[srpm]
class=%s.srpm.SRpmHandler

""" % PACKAGE,
handler=
"""
from pulp.agent.lib.handler import *
from pulp.agent.lib.report import *
from pulp.agent.lib.conduit import *

class SRpmHandler(ContentHandler):

  def install(self, conduit, units, options):
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
""",
site_packages=True)

# -- Mock (section missing) Handler ------------------------------------------------------

SECTION_MISSING = dict(
name='Test-section-not-found',
descriptor="""
[main]
enabled=1

[types]
content=puppet
""",
handler="""
class A: pass
""")


# -- Mock (class not defined) Handler ----------------------------------------------------

NO_MODULE = dict(
    name='Test-class-property-missing',
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

# -- Mock (class not found) Handler ----------------------------------------------------

CLASS_NDEF = dict(
name='Test-class-not-found',
descriptor="""
[main]
enabled=1
[types]
content=something
[something]
class=Something
""")

#
# Mock Deployer
#

class MockDeployer:

    ROOT = '/tmp/pulp-test'
    CONF_D = os.path.join(ROOT, 'etc/agent/handler')
    PATH = os.path.join(ROOT, 'usr/lib/agent/handler')
    SITE_PACKAGES = os.path.join(ROOT, 'site-packages')

    def deploy(self):
        for path in (self.CONF_D, self.PATH, self.SITE_PACKAGES):
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path)
        self.build_site_packages()
        sys.path.insert(0, self.SITE_PACKAGES)
        for handler in (RPM, SRPM, SECTION_MISSING, CLASS_NDEF, NO_MODULE):
            self.__deploy(handler)
        print 'deployed'

    def clean(self):
        shutil.rmtree(self.ROOT, ignore_errors=True)

    def __deploy(self, handler):
        name = handler['name']
        descriptor = handler['descriptor']
        fn = '.'.join((name, 'conf'))
        path = os.path.join(self.CONF_D, fn)
        # deploy descriptor
        f = open(path, 'w')
        f.write(descriptor)
        f.close()
        # deploy module (if defined)
        mod = handler.get('handler')
        if not mod:
            return
        fn = '.'.join((name, 'py'))
        if handler.get('site_packages', False):
            pkgpath = os.path.join(*PACKAGE.split('.'))
            rootdir = os.path.join(self.SITE_PACKAGES, pkgpath)
        else:
            rootdir = self.PATH
        path = os.path.join(rootdir, fn)
        f = open(path, 'w')
        f.write(mod)
        f.close()

    def build_site_packages(self):
        history = [self.SITE_PACKAGES]
        for p in PACKAGE.split('.'):
            history.append(p)
            pkgdir = os.path.join(*history)
            os.makedirs(pkgdir)
            path = os.path.join(pkgdir, '__init__.py')
            f = open(path, 'w')
            f.write('# package:%s' % p)
            f.close()
