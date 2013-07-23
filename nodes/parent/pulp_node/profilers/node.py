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
from logging import getLogger

from pulp.plugins.profiler import Profiler
from pulp.server.managers import factory as managers

from pulp_node import constants
from pulp_node.profiles import build_profile, fingerprint


log = getLogger(__name__)


# --- constants -------------------------------------------------------------------------


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


class Discrepancy(Exception):

    def __init__(self, expected, reported):
        self.expected = expected
        self.reported = reported


class RepositoryCountDiscrepancy(Discrepancy):
        
    def __str__(self):
        e_cnt = len(self.expected)
        r_cnt = len(self.reported)
        msg = _('Repository count discrepancy: expected=%(e_cnt)d reported=%(r_cnt)d')
        return msg % dict(e_cnt=e_cnt, r_cnt=r_cnt)


class RepositoryDiscrepancy(Discrepancy):

    def __str__(self):
        e_id = self.expected['id']
        r_id = self.reported['id']
        msg = _('Repository discrepancy: expected_id=%(e_id)s reported_id=%(r_id)s')
        return msg % dict(e_id=e_id, r_id=r_id)


class UnitDiscrepancy(Discrepancy):

    def __str__(self):
        e_id = self.expected['id']
        r_id = self.reported['id']
        e_cnt = len(self.expected[constants.PROFILE_UNITS])
        r_cnt = len(self.reported[constants.PROFILE_UNITS])
        msg = _('Unit discrepancy: expected %(e_id)s=%(e_cnt)d, reported %(r_id)s=%(r_cnt)d')
        return msg % dict(e_id=e_id, e_cnt=e_cnt, r_id=r_id, r_cnt=r_cnt)


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
        """
        Translate the node update units.
        Returns the units for nodes that need to be updated (out-of-sync).
        :param consumer: A consumer object.
        :type consumer: pulp.plugins.model.Consumer
        :param units: A list of content units to be updated.
        :type units: list of: { type_id:<str>, unit_key:<dict> }
        :param options: Update options; based on unit type.
        :type options: dict
        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginCallConfiguration
        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.profiler.ProfilerConduit
        :return: The translated units
        :rtype: list of: { type_id:<str>, unit_key:<dict> } 
        """
        simulated = options.get('simulated', False)
        if not simulated:
            return units
        strategy = self._node_strategy(consumer.id)
        bindings = self._bindings(consumer.id)
        repo_ids = bindings.keys()
        profiles = build_profile(repo_ids), consumer.profiles.get(constants.TYPE_NODE)
        try:
            node_strategy = find_strategy(strategy)()
            repositories = node_strategy.bash_repositories(profiles)
            for expected, reported in repositories:
                repo_id = expected['id']
                strategy = bindings[repo_id]
                bind_strategy = find_strategy(strategy)()
                bind_strategy.bash_units((expected, reported))
            units = []  # no updated needed
        except Discrepancy, dx:
            discrepancy = str(dx)
            log.info(discrepancy)
        return units

    def _bindings(self, consumer_id):
        """
        Get the node bindings and specified strategy for a consumer.
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :return: A dictionary of bindings keyed by repo_id.
        :rtype: dict
        """
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
        """
        Get the node synchronization strategy for the specified consumer.
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :return: The node synchronization strategy.
        :rtype: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        notes = consumer['notes']
        return notes.get(constants.STRATEGY_NOTE_KEY, constants.DEFAULT_STRATEGY)


# --- strategies -----------------------------------------------------------------------


class Mirror(object):
    """
    Determine node synchronization status for the MIRROR strategies.
    """

    def bash_repositories(self, profiles):
        """
        Bash the repositories inventoried in the expected and reported
        profiles to determine the node synchronization status.
        :param profiles: Tuple containing the expected and reported profiles.
        :type profiles: tuple(2)
        :return: The compared repositories based on the strategy.
        :rtype: list
        :raise NotFound: When discrepancies found.
        """
        expected, reported = [p[constants.PROFILE_REPOSITORIES] for p in profiles]
        if len(reported) != len(expected):
            raise RepositoryCountDiscrepancy(expected, reported)
        repositories = zip(expected, reported)
        for r in repositories:
            expected = dict(r[0])
            reported = dict(r[1])
            expected.pop(constants.PROFILE_UNITS)
            reported.pop(constants.PROFILE_UNITS)
            if fingerprint(expected) != fingerprint(reported):
                raise RepositoryDiscrepancy(expected, reported)
        return repositories

    def bash_units(self, repositories):
        """
        Bash the content units inventoried in the expected and reported
        profiled repositories to determine the repository synchronization status.
        :param repositories: List of tuple containing the expected and reported profiled
            repository created using zip().
        :type repositories: list
        :raise NotFound: When discrepancies found.
        """
        expected, reported = [map(fingerprint, r[constants.PROFILE_UNITS]) for r in repositories]
        if expected != reported:
            raise UnitDiscrepancy(*repositories)


class Additive(object):

    def bash_repositories(self, profiles):
        """
        Bash the repositories inventoried in the expected and reported
        profiles to determine the node synchronization status.
        :param profiles: Tuple containing the expected and reported profiles.
        :type profiles: tuple(2)
        :return: The compared repositories based on the strategy.
        :rtype: list
        :raise NotFound: When discrepancies found.
        """
        expected, reported = [p[constants.PROFILE_REPOSITORIES] for p in profiles]
        reported = [r for r in reported if r['id'] in [e['id'] for e in expected]]
        if len(reported) < len(expected):
            raise RepositoryCountDiscrepancy(expected, reported)
        repositories = zip(expected, reported)
        for r in repositories:
            expected = dict(r[0])
            reported = dict(r[1])
            expected.pop(constants.PROFILE_UNITS)
            reported.pop(constants.PROFILE_UNITS)
            if fingerprint(expected) != fingerprint(reported):
                raise RepositoryDiscrepancy(expected, reported)
        return repositories

    def bash_units(self, repositories):
        """
        Bash the content units inventoried in the expected and reported
        profiled repositories to determine the repository synchronization status.
        :param repositories: List of tuple containing the expected and reported profiled
            repository created using zip().
        :type repositories: list
        :raise NotFound: When discrepancies found.
        """
        expected, reported = [map(fingerprint, r[constants.PROFILE_UNITS]) for r in repositories]
        reported = [u for u in reported if u in expected]
        if expected != reported:
            raise UnitDiscrepancy(*repositories)


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