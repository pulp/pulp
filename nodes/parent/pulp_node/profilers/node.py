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


from gettext import gettext as _

from pulp.plugins.profiler import Profiler
from pulp.server.managers import factory as managers

from pulp_node import constants
from pulp_node.profiles import build_profile, fingerprint


# --- i18n ------------------------------------------------------------------------------


STRATEGY_UNSUPPORTED = _('Strategy "%(s)s" not supported')


# --- loading ---------------------------------------------------------------------------


def entry_point():
    """
    Entry point that pulp platform uses to load the profiler.
    :return: profiler class and its configuration.
    :rtype:  Profiler, {}
    """
    return NodeProfiler, {}


# --- exceptions ------------------------------------------------------------------------


class NotMatched(Exception):
    pass


# --- profiler -------------------------------------------------------------------------


class NodeProfiler(Profiler):

    @classmethod
    def metadata(cls):
        return {
            'id': constants.NODE_PROFILER_ID,
            'display_name': _('Pulp node profiler'),
            'types': [constants.TYPE_NODE, constants.TYPE_REPOSITORY]
        }

    def update_units(self, consumer, units, options, config, conduit):
        simulated = options.get('simulated', False)
        if not simulated:
            return units
        strategy = self._node_strategy(consumer.id)
        bindings = self._bindings(consumer.id)
        repo_ids = bindings.keys()
        profiles = build_profile(repo_ids), consumer.profiles.get(constants.TYPE_NODE)
        _strategy = find_strategy(strategy)()
        try:
            repositories = _strategy.node(profiles)
            for expected, reported in repositories:
                repo_id = expected['id']
                strategy = bindings[repo_id]
                _strategy = find_strategy(strategy)()
                _strategy.repository((expected, reported))
        except NotMatched:
            units = []
        return units

    def _bindings(self, consumer_id):
        bindings = {}
        manager = managers.consumer_bind_manager()
        for binding in manager.find_by_consumer(consumer_id):
            repo_id = binding['repo_id']
            distributor_id = binding['distributor_id']
            manager = managers.repo_distributor_manager()
            distributor = manager.get_distributor(repo_id, distributor_id)
            if distributor['distributor_type_id'] in constants.ALL_DISTRIBUTORS:
                conf = binding['binding_config']
                strategy = conf.get(constants.STRATEGY_KEYWORD, constants.DEFAULT_STRATEGY)
                bindings[repo_id] = strategy
        return bindings

    def _node_strategy(self, consumer_id):
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        notes = consumer['notes']
        return notes.get(constants.STRATEGY_NOTE_KEY, constants.DEFAULT_STRATEGY)


# --- strategies -----------------------------------------------------------------------


class Mirror(object):

    def node(self, profiles):
        expected, reported = [p[constants.PROFILE_REPOSITORIES] for p in profiles]
        if len(reported) != len(expected):
            raise NotMatched()
        repositories = zip(expected, reported)
        for r in repositories:
            expected = dict(r[0])
            reported = dict(r[1])
            expected.pop(constants.PROFILE_UNITS)
            reported.pop(constants.PROFILE_UNITS)
            if fingerprint(expected) != fingerprint(reported):
                raise NotMatched()
        return repositories

    def repository(self, repositories):
        expected, reported = [map(fingerprint, r[constants.PROFILE_UNITS]) for r in repositories]
        if expected != reported:
            raise NotMatched()


class Additive(object):

    def node(self, profiles):
        expected, reported = [p[constants.PROFILE_REPOSITORIES] for p in profiles]
        if len(reported) < len(expected):
            raise NotMatched()
        reported = [r for r in reported if r['id'] in [e['id'] for e in expected]]
        repositories = zip(expected, reported)
        for r in repositories:
            expected = dict(r[0])
            reported = dict(r[1])
            expected.pop(constants.PROFILE_UNITS)
            reported.pop(constants.PROFILE_UNITS)
            if fingerprint(expected) != fingerprint(reported):
                raise NotMatched()
        return repositories

    def repository(self, repositories):
        expected, reported = [map(fingerprint, r[constants.PROFILE_UNITS]) for r in repositories]
        reported = [u for u in reported if u in expected]
        if expected != reported:
            raise NotMatched()


# --- factory ---------------------------------------------------------------------------


STRATEGIES = {
    constants.MIRROR_STRATEGY: Mirror,
    constants.ADDITIVE_STRATEGY: Additive,
}


class StrategyUnsupported(Exception):

    def __init__(self, name):
        msg = STRATEGY_UNSUPPORTED % {'s': name}
        Exception.__init__(self, msg)


def find_strategy(name):
    try:
        return STRATEGIES[name]
    except KeyError:
        raise StrategyUnsupported(name)