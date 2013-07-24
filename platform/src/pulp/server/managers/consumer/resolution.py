# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains content resolution classes
"""

import sys

from logging import getLogger

from pulp.server.managers import factory as managers
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.profiler import Profiler, InvalidUnitsRequested
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.server.exceptions import PulpExecutionException, PulpDataException


_LOG = getLogger(__name__)


class ContentResolutionManager(object):
    """
    The unit resolution manager provides methods for translating
    content units for installation, update and un-installation.
    """
    
    def install_units(self, consumer_id, units, options):
        """
        Translate the specified units to be installed.
        The specified units are resolved into the actual units the would be installed
        as determined by the profiler.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be resolved.
        :type units: list of: { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        :return: The resolved units.
        :rtype: list
        """
        conduit = ProfilerConduit()
        _collated = collated(units)
        options['simulated'] = True
        for type_id, units in _collated.items():
            consumer = get_consumer(consumer_id)
            profiler, cfg = get_profiler(type_id)
            units = invoke_plugin(profiler.install_units, consumer, units, options, cfg, conduit)
            _collated[type_id] = units
        return [j for i in _collated.values() for j in i]
    
    def update_units(self, consumer_id, units, options):
        """
        Translate the specified units to be updated.
        The specified units are resolved into the actual units the would be updated
        as determined by the profiler.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be resolved.
        :type units: list of: { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        :return: The resolved units.
        :rtype: list
        """
        conduit = ProfilerConduit()
        _collated = collated(units)
        options['simulated'] = True
        for type_id, units in _collated.items():
            consumer = get_consumer(consumer_id)
            profiler, cfg = get_profiler(type_id)
            units = invoke_plugin(profiler.update_units, consumer, units, options, cfg, conduit)
            _collated[type_id] = units
        return [j for i in _collated.values() for j in i]
    
    def uninstall_units(self, consumer_id, units, options):
        """
        Translate the specified units to be uninstalled.
        The specified units are resolved into the actual units the would be uninstalled
        as determined by the profiler.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be resolved.
        :type units: list of: { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        :return: The resolved units.
        :rtype: list
        """
        conduit = ProfilerConduit()
        _collated = collated(units)
        options['simulated'] = True
        for type_id, units in _collated.items():
            consumer = get_consumer(consumer_id)
            profiler, cfg = get_profiler(type_id)
            units = invoke_plugin(profiler.uninstall_units, consumer, units, options, cfg, conduit)
            _collated[type_id] = units
        return [j for i in _collated.values() for j in i]


# --- utils ------------------------------------------------------------------


def collated(units):
    """
    Collate the units by type_id.
    :param units: A list of { type_id:<str>, unit_key:<dict> }
    :return: The collated units.
    :rtype: dict
    """
    collated = {}
    for unit in units:
        type_id = unit['type_id']
        _units = collated.setdefault(type_id, [])
        _units.append(unit)
    return collated


def get_consumer(consumer_id):
    """
    Get a profiler consumer model object.
    :param id: A consumer ID.
    :type id: str
    :return: A populated profiler consumer model object.
    :rtype: L{ProfiledConsumer}
    """
    profiles = {}
    manager = managers.consumer_profile_manager()
    for p in manager.get_profiles(consumer_id):
        type_id = p['content_type']
        profile = p['profile']
        profiles[type_id] = profile
    return ProfiledConsumer(consumer_id, profiles)


def get_profiler(type_id):
    """
    Find the profiler.
    Returns the Profiler base class when not matched.
    :param type_id: The content type ID.
    :type type_id: str
    :return: (profiler, cfg)
    :rtype: tuple
    """
    try:
        plugin, cfg = plugin_api.get_profiler_by_type(type_id)
    except plugin_exceptions.PluginNotFound:
        plugin = Profiler()
        cfg = {}
    return plugin, cfg


def invoke_plugin(method, *args, **kwargs):
    """
    Invoke plugin method and resolve exceptions.
    :param method: The plugin method to be invoked.
    :param args: The parameter list
    :param kwargs: The keyword parameters.
    :return: Whatever the method returns.
    """
    try:
        return method(*args, **kwargs)
    except InvalidUnitsRequested, e:
        raise PulpDataException(e.units, e.message)
    except Exception:
        raise PulpExecutionException(), None, sys.exc_info()[2]