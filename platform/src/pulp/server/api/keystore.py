# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import os

from pulp.server.util import top_gpg_location as lnkdir
from pulp.server.util import top_repos_location as keydir
from pulp.common.util import encode_unicode

log = logging.getLogger(__name__)


class KeyStore:
    """
    The GPG key store.
    @ivar path: The repo relative storage path.
    @type path: str
    """

    def __init__(self, path):
        """
        @param path: The repo relative storage path.
        @type path: str
        """
        while path.startswith('/'):
            path = path[1:]
        path = encode_unicode(path)
        self.path = path
        self.mkdir()

    def add(self, keylist):
        """
        Add entries specified in the keylist.
        @param keylist: A list of (entry) tuples (<key-name>, <key-content>)
        @type keylist: [<entry>,..]
        @return: A list of added (relateive paths) files.
        @rtype: [str,..]
        """
        added = []
        for fn, content in keylist:
            path = os.path.join(keydir(), self.path, fn)
            log.info('writing @: %s', path)
            f = open(path, 'w')
            f.write(content)
            f.close()
            entry = os.path.join(self.path, fn)
            added.append(entry)
            dst = os.path.join(lnkdir(), self.path, fn)
            self.link(path, dst)
        return added

    def delete(self, keylist):
        """
        Delete the specified keys by name.
        @param keylist: A list of key names.
        @type keylist: [str,..]
        """
        for fn in keylist:
            path = os.path.join(keydir(), self.path, fn)
            self.unlink(path)
            path = os.path.join(lnkdir(), self.path, fn)
            self.unlink(path)
        return keylist

    def list(self):
        """
        List the relative paths of all linked keys.
        @return: [path,..]
        @rtype: list
        """
        keylist = []
        dir = os.path.join(lnkdir(), self.path)
        for fn in os.listdir(dir):
            path = os.path.join(dir, fn)
            entry = os.path.join(self.path, fn)
            keylist.append(entry)
        return keylist

    def relink(self):
        """
        Relink GPG key files.
        """
        linked = []
        self.clean()
        for path, content in self.keyfiles():
            fn = os.path.basename(path)
            dst = os.path.join(lnkdir(), self.path, fn)
            self.link(path, dst)
            entry = os.path.join(self.path, fn)
            linked.append(entry)
        return linked

    def clean(self, all=False):
        """
        Remove all of the links.
        @param all: Indicates the I{link} directory is to be removed.
        @type all: bool
        """
        dir = os.path.join(lnkdir(), self.path)
        for fn in os.listdir(dir):
            path = os.path.join(dir, fn)
            self.unlink(path)
        if all:
            self.unlink(dir)

    def keyfiles(self, path=None):
        """
        Get a list of GPG key files at the specified I{path}.
        @param path: An absolute path to a file containing a GPG key.
        @type path: str
        @return: A list of tuples: (key-path, key-content)
        @rtype: list
        """
        keys = []
        pattern = '----BEGIN PGP PUBLIC KEY BLOCK-----'
        if not path:
            path = os.path.join(keydir(), self.path)
        for fn in os.listdir(path):
            for ext in ('.rpm', '.gz', '.xml'):
                if fn.endswith(ext):
                    continue
            try:
                fp = os.path.join(path, fn)
                if os.path.isdir(fp):
                    continue
                f = open(fp)
                content = f.read()
                if pattern in content:
                    keys.append((fp, content))
                f.close()
            except:
                log.error(fp, exc_info=True)
        return keys

    def keys_and_contents(self):
        """
        Returns a mapping of key name to its contents.
        @return: mapping of key name (not a full path) to its contents
        @rtype: dict {keyname:keycontent}
        """
        keylist = {}
        for path in self.list():
            name = os.path.basename(path)
            path = os.path.join(lnkdir(), path)
            fp = open(path)
            content = fp.read()
            fp.close()
            keylist[name] = content
        return keylist

    def link(self, src, dst):
        """
        Link I{src} to I{dst} unless it is already
        list as needed.
        @param src: The source path.
        @type src: str
        @param dst: The destination path.
        @type dst: str
        """
        if os.path.islink(dst):
            real = os.path.realpath(dst)
            if real == src:
                return # already linked
        else:
            log.info('linking: %s --> %s', dst, src)
            os.symlink(src, dst)

    def unlink(self, path):
        """
        Sefely unlink I{path}.
        @param path: An absolute path.
        @type path: str
        """
        try:
            log.info('unlinking: %s', path)
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.unlink(path)
        except:
            log.error(path, exc_info=True)

    def mkdir(self):
        """
        Ensure the key and link directories exist.
        """
        for root in (keydir(), lnkdir()):
            path = os.path.join(root, self.path)
            if not os.path.exists(path):
                log.info('mkdir: %s', path)
                os.makedirs(path)
