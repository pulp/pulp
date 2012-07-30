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

"""
Profiler plugin to support RPM Errata functionality
"""
import gettext

from pulp.plugins.model import ApplicabilityReport
from pulp.plugins.profiler import Profiler, InvalidUnitsRequested
from pulp.plugins.conduits.mixins import UnitAssociationCriteria
from pulp_rpm.yum_plugin import util

_ = gettext.gettext
_LOG = util.getLogger(__name__)

PROFILER_TYPE_ID="rpm_errata_profiler"
ERRATA_TYPE_ID="erratum"
RPM_TYPE_ID="rpm"
RPM_UNIT_KEY = ("name", "epoch", "version", "release", "arch", "checksum", "checksumtype")

class RPMErrataProfiler(Profiler):
    def __init__(self):
        super(RPMErrataProfiler, self).__init__()

    @classmethod
    def metadata(cls):
        return { 
                'id': PROFILER_TYPE_ID,
                'display_name': "RPM Errata Profiler",
                'types': [ERRATA_TYPE_ID],
                }

    def update_profile(self, consumer, profile, config, conduit):
        raise NotImplementedError()

    def update_units(self, consumer, units, options, config, conduit):
        raise NotImplementedError()

    def uninstall_units(self, consumer, units, options, config, conduit):
        raise NotImplementedError()

    def install_units(self, consumer, units, options, config, conduit):
        """
        Translate the specified content units to be installed.
        The specified content units are intended to be installed on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Install options; based on unit type.
        @type options: dict

        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profile.ProfilerConduit}

        @return:    a list of dictionaries containing info on the 'translated units'.
                    each dictionary contains a 'name' key which refers 
                    to the rpm name associated to the errata
        @rtype [{'unit_key':{'name':name.arch}, 'type_id':'rpm'}]
        """
        return self.translate_units(units, consumer, conduit)


    # -- applicability ---------------------------------------------------------


    def unit_applicable(self, consumer, unit, config, conduit):
        """
        Determine whether the content unit is applicable to
        the specified consumer.  The definition of "applicable" is content
        type specific and up to the descision of the profiler.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param unit: A content unit: { type_id:<str>, unit_key:<dict> }
        @type unit: dict

        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profile.ProfilerConduit}

        @return: An applicability report.
        @rtype: L{pulp.plugins.model.ApplicabilityReport}
        """
        applicable = False
        applicable_rpms = self.translate(unit, consumer, conduit)
        if applicable_rpms:
            applicable = True
        return ApplicabilityReport(unit, applicable, {}, {})


    # -- Below are helper methods not part of the Profiler interface ----

    def translate_units(self, units, consumer, conduit):
        """
        Will translate passed in errata unit_keys to a list of dictionaries
        containing the associated RPM names applicable to the consumer.

        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profile.ProfilerConduit}

        @return:    a list of dictionaries containing info on the 'translated units'.
                    each dictionary contains a 'name' key which refers 
                    to the rpm name associated to the errata
        @rtype [{'unit_key':{'name':name.arch}, 'type_id':'rpm'}]
        """
        translated_units = []
        for unit in units:
            values = self.translate(unit, consumer, conduit)
            if values:
                translated_units.extend(values)
        return translated_units

    def translate(self, unit, consumer, conduit):
        """
        Translates an erratum to a list of rpm units
        The rpm units refer to the upgraded packages referenced by the erratum
        only those rpms which will upgrade an existing rpm on the consumer are returned

        @param unit: A content unit: { type_id:<str>, unit_key:<dict> }
        @type unit: dict

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profile.ProfilerConduit}

        @return:    a list of dictionaries containing info on the 'translated units'.
                    each dictionary contains a 'name' key which refers 
                    to the rpm name associated to the errata
        @rtype [{'unit_key':{'name':name.arch}, 'type_id':'rpm'}]
        """
        if unit["type_id"] != ERRATA_TYPE_ID:
            error_msg = _("unit_applicable invoked with type_id [%s], expected [%s]") % (unit["type_id"], ERRATA_TYPE_ID)
            _LOG.error(error_msg)
            raise InvalidUnitsRequested([unit], error_msg)
        errata = self.find_unit_associated_to_consumer(unit["type_id"], unit["unit_key"], consumer, conduit)
        if not errata:
            error_msg = _("Unable to find errata with unit_key [%s] in bound repos [%s] to consumer [%s]") % \
                    (unit["unit_key"], conduit.get_bindings(consumer.id), consumer.id)
            _LOG.error(error_msg)
            raise InvalidUnitsRequested([unit], error_msg)
        updated_rpms = self.get_rpms_from_errata(errata)
        _LOG.info("Errata <%s> refers to %s updated rpms of: %s" % (errata.unit_key['id'], len(updated_rpms), updated_rpms))
        applicable_rpms, upgrade_details = self.rpms_applicable_to_consumer(consumer, updated_rpms)
        if applicable_rpms:
            _LOG.info("Rpms: <%s> were found to be related to errata <%s> and applicable to consumer <%s>" % (applicable_rpms, errata, consumer.id))
        # Return as list of name.arch values
        ret_val = []
        for ar in applicable_rpms:
            pkg_name = "%s.%s" % (ar["name"], ar["arch"])
            data = {"unit_key":{"name":pkg_name}, "type_id":RPM_TYPE_ID}
            ret_val.append(data)
        _LOG.info("Translated errata <%s> to <%s>" % (errata, ret_val))
        return ret_val

    def find_unit_associated_to_consumer(self, unit_type, unit_key, consumer, conduit):
        criteria = UnitAssociationCriteria(type_ids=[unit_type], unit_filters=unit_key)
        return self.find_unit_associated_to_consumer_by_criteria(criteria, consumer, conduit)

    def find_unit_associated_to_consumer_by_criteria(self, criteria, consumer, conduit):
        # We don't know what repo the unit could belong to
        # and we don't have a means for querying all repos at once
        # so we are iterating over each repo
        bound_repo_ids = conduit.get_bindings(consumer.id)
        for repo_id in bound_repo_ids:
            result = conduit.get_units(repo_id, criteria)
            _LOG.info("Found %s items when searching in repo <%s> for <%s>" % (len(result), repo_id, criteria))
            if result:
                return result[0]
        return None

    def get_rpms_from_errata(self, errata):
        """
        @param errata
        @type errata: pulp.plugins.model.Unit

        @return list of rpms, which are each a dict of nevra info
        @rtype: [{}]
        """
        rpms = []
        if not errata.metadata.has_key("pkglist"):
            return rpms
        for pkgs in errata.metadata['pkglist']:
            for rpm in pkgs["packages"]:
                rpms.append(rpm)
        return rpms

    def rpms_applicable_to_consumer(self, consumer, errata_rpms):
        """
        @param consumer:
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param errata_rpms: 
        @type errata_rpms: list of dicts

        @return:    tuple, first entry list of dictionaries of applicable 
                    rpm entries, second entry dictionary with more info 
                    of which installed rpm will be upgraded by what rpm

                    Note:
                    This method does not take into consideration if the consumer
                    is bound to the repo containing the RPM.
        @rtype: ([{}], {})
        """
        applicable_rpms = []
        older_rpms = {}
        if not consumer.profiles.has_key(RPM_TYPE_ID):
            _LOG.warn("Consumer [%s] is missing profile information for [%s], found profiles are: %s" % \
                    (consumer.id, RPM_TYPE_ID, consumer.profiles.keys()))
            return applicable_rpms, older_rpms
        lookup = self.form_lookup_table(consumer.profiles[RPM_TYPE_ID])
        for errata_rpm in errata_rpms:
            key = "%s.%s" % (errata_rpm["name"], errata_rpm["arch"])
            if lookup.has_key(key):
                installed_rpm = lookup[key]
                is_newer = util.is_rpm_newer(errata_rpm, installed_rpm)
                _LOG.info("Found a match of rpm <%s> installed on consumer, is %s newer than %s, %s" % (key, errata_rpm, installed_rpm, is_newer))
                if is_newer:
                    applicable_rpms.append(errata_rpm)
                    older_rpms[key] = {"installed":installed_rpm, "available":errata_rpm}
            else:
                _LOG.info("rpm %s was not found in consumer profile of %s" % (key, consumer.id))
        return applicable_rpms, older_rpms

    def form_lookup_table(self, rpms):
        lookup = {}
        for r in rpms:
            # Assuming that only 1 name.arch is allowed to be installed on a machine
            # therefore we will handle only one name.arch in the lookup table
            key = "%s.%s" % (r["name"], r["arch"])
            lookup[key] = r
        return lookup

    def form_rpm_unit_key(self, rpm_dict):
        unit_key = {}
        for key in RPM_UNIT_KEY:
            unit_key[key] = rpm_dict[key]
        return unit_key

