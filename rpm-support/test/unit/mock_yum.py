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

    REPOID = 'fedora'

    doPluginSetup = mock.Mock()
    registerCommand = mock.Mock()
    resolveDeps = mock.Mock()
    selectGroup = mock.Mock()
    groupRemove = mock.Mock()
    processTransaction = mock.Mock()
    close = mock.Mock()
    closeRpmDB = mock.Mock()

    def __init__(self, *args, **kwargs):
        self.conf = Config()
        self.preconf = Config()

    def install(self, pattern):
        tx = []
        state = 'i'
        version = '1.0'
        repoid = self.REPOID
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        tx.append(t)
        for pkg in self.INSTALL_DEPS:
            t = TxMember(state, repoid, pkg, 1)
            tx.append(t)
        self.tsInfo = tx

    def update(self, pattern):
        tx = []
        state = 'u'
        version = '1.0'
        repoid = self.REPOID
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        tx.append(t)
        for pkg in self.UPDATE_DEPS:
            t = TxMember(state, repoid, pkg, 1)
            tx.append(t)
        self.tsInfo = tx

    def remove(self, pattern):
        tx = []
        state = 'e'
        version = '1.0'
        repoid = self.REPOID
        pkg = Pkg(pattern, version)
        t = TxMember(state, repoid, pkg)
        tx.append(t)
        for pkg in self.REMOVE_DEPS:
            t = TxMember(state, repoid, pkg, 1)
            tx.append(t)
        self.tsInfo = tx