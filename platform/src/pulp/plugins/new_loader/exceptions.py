# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt


class PluginLoaderException(Exception):
    """
    Base plugin loader exception.
    """
    pass


class PluginLoadError(PluginLoaderException):
    """
    Raised when errors are encountered while loading plugins.
    """
    pass


class ConflictingPluginError(PluginLoaderException):
    """
    Raised when 2 or more plugins try to handle the same content, distribution,
    or profile type(s).
    """
    pass


class PluginNotFound(PluginLoaderException):
    """
    Raised when a plugin cannot be located.
    """
    pass


# derivative classes used for testing
class ConflictingPluginName(ConflictingPluginError): pass
class InvalidImporter(PluginLoadError): pass
class MalformedMetadata(PluginLoadError): pass
class MissingMetadata(PluginLoadError): pass
class MissingPluginClass(PluginLoadError): pass
class MissingPluginModule(PluginLoadError): pass
class MissingPluginPackage(PluginLoadError): pass
class NamespaceCollision(PluginLoadError): pass

