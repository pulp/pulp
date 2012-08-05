# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock


def install():
    import yum
    yum.YumBase = YumBase


class Pkg:

    ARCH = 'noarch'

    def __init__(self, name, version, release=1, arch=ARCH):
        self.name = name
        self.ver = version
        self.rel = str(release)
        self.arch = arch
        self.epoch = '0'

    def __str__(self):
        return self.name


class TxMember:

     def __init__(self, state, repoid, pkg, isDep=0):
         self.ts_state = state
         self.repoid = repoid
         self.isDep = isDep
         self.po = pkg


class Config(object):
    pass


class YumBase:

    UNKNOWN_PKG = '__unknown__'

    INSTALL_DEPS = [
        Pkg('dep1', '3.2'),
        Pkg('dep2', '2.5', '1'),
    ]

    UPDATE_DEPS = [
        Pkg('dep1', '3.2'),
        Pkg('dep2', '2.5', '1'),
    ]

    REMOVE_DEPS = [
        Pkg('dep1', '3.2'),
        Pkg('dep2', '2.5', '1'),
    ]

    STATES = {
        'i':INSTALL_DEPS,
        'u':UPDATE_DEPS,
        'e':REMOVE_DEPS,
    }

    REPOID = 'fedora'

    GROUPS = {
        'mygroup':[
            Pkg('zsh', '3.2'),
            Pkg('xchat', '1.3'),
            Pkg('thunderbird', '10.1.7'),
        ],
        'pulp':[
            Pkg('okaara', '0.25'),
            Pkg('gofer', '0.70', '2'),
            Pkg('mongo', '1.3.2'),
            Pkg('qpid', '0.70'),
        ],
    }

    doPluginSetup = mock.Mock()
    registerCommand = mock.Mock()
    processTransaction = mock.Mock()
    close = mock.Mock()
    closeRpmDB = mock.Mock()

    @classmethod
    def reset(cls):
        cls.doPluginSetup.reset_mock()
        cls.registerCommand.reset_mock()
        cls.processTransaction.reset_mock()
        cls.close.reset_mock()
        cls.closeRpmDB.reset_mock()

    def __init__(self, *args, **kwargs):
        self.conf = Config()
        self.preconf = Config()
        self.tsInfo = []

    def install(self, pattern):
        state = 'i'
        version = '1.0'
        repoid = self.REPOID
        self.__validpkg(pattern)
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        self.tsInfo.append(t)

    def update(self, pattern):
        state = 'u'
        version = '1.0'
        repoid = self.REPOID
        self.__validpkg(pattern)
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        self.tsInfo.append(t)

    def remove(self, pattern):
        state = 'e'
        version = '1.0'
        repoid = self.REPOID
        self.__validpkg(pattern)
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        self.tsInfo.append(t)

    def __validpkg(self, pattern):
        if pattern == self.UNKNOWN_PKG:
            raise Exception, 'package not found'

    def selectGroup(self, name):
        state = 'i'
        repoid = self.REPOID
        grp = self.GROUPS.get(name)
        if grp is None:
            raise Exception, 'Group not found'
        for pkg in grp:
            t = TxMember(state, repoid, pkg)
            self.tsInfo.append(t)

    def groupRemove(self, name):
        state = 'e'
        repoid = self.REPOID
        grp = self.GROUPS.get(name)
        if grp is None:
            raise Exception, 'Group not found'
        for pkg in grp:
            t = TxMember(state, repoid, pkg)
            self.tsInfo.append(t)

    def resolveDeps(self):
        deps = {}
        repoid = self.REPOID
        for t in self.tsInfo:
            deps[t.ts_state] = self.STATES[t.ts_state]
        for state, pkglist in deps.items():
            for pkg in pkglist:
                t = TxMember(state, repoid, pkg, 1)
                self.tsInfo.append(t)