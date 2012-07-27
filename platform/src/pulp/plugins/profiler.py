# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE. You should have received a copy of GPLv2 along with this
# software; if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

class InvalidUnitsRequested(Exception):
    """
    Raised by install_units, update_units, or uninstall_units to indicate
    the user request cannot be satisified for some reason (the unit does not
    exist in Pulp, the unit would harm the consumer if installed/removed,
    etc.).

    This should be raised if any of the units specified in the request are
    invalid. Multiple units can be specified as causing this exception.

    The message must be suitable to be displayed to the user (for instance,
    i18n-ified).
    """

    def __init__(self, units, message):
        """
        :param units: list of units that cannot be used in the operation
        :type  units: list

        :param message: message suitable for display to a user describing
               why the operation was aborted
        :type  message: str
        """
        Exception.__init__(self, message)
        self.units = units
        self.message = message


class Profiler(object):
    """
    Base class for Pulp consumer profilers. Profilers must subclass this class
    in order for Pulp to identify them during plugin discovery.  The primary
    role of a Profiler is to perform translation between Pulp's generic content
    model and consumer specific content.

    Profile Translation:
        TBD

    Unit Translation:

    One example of a unit translation is to expand a unit that references
    other units into specific install requests for the aggregated units. The
    example below describes how a request for an aggregate unit ("mypets")
    would be translated into install requests for each related pet. The
    install for the aggregate unit itself does not need to be included in the
    results.

    Requested Unit:

        {type_id:"PETS", unit_key:{"name":"mypets"}}

    Translated Install Requests:

        {type_id:"DOG", unit_key:{"name":"Rover"}}
        {type_id:"DOG", unit_key:{"name":"Cujo"}}
        {type_id:"CAT", unit_key:{"name":"Garfield"}}

    Another example is using a unit as a meta type for multiple versions
    of the unit. In this example, the "myapp" meta unit is used to refer to
    the unit regardless of the destination consumer's platform. The job of
    the profiler is to understand the consumer to which the request applies
    and choose the appropriate format for the actual install request.

    Requested Unit:

        {type_id:"APP", unit_key:{"name":"myapp"}}

    For a Linux Consumer:

        {type_id:"TAR", unit_key:{"name":"myapp.tar"}}

    For a Windows consumer:

        {type_id:"ZIP", unit_key:{"name":"myapp.zip"}}
    """

    # -- plugin lifecycle ------------------------------------------------------

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this profiler. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this profiler. Must be unique
               across all profilers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the profiler.
        * types - List of all content type IDs that may be processed using this
                  profiler.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        @return: description of the profiler's capabilities
        @rtype:  dict
        """
        raise NotImplementedError()

    # -- translations ----------------------------------------------------------

    def update_profile(self, consumer, profile, config, conduit):
        """
        Notification that the consumer has reported the installed unit
        profile.  The profiler has this opportunity to translate the
        reported profile.  If a profile cannot be translated, the profiler
        should raise an appropriate exception.  See: Profile Translation
        examples in class documentation.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param profile: The reported profile.
        @type profile: list

        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated profile.
        @rtype: list
        """
        return profile

    def install_units(self, consumer, units, options, config, conduit):
        """
        Translate the specified content units to be installed.
        The specified content units are intented to be installed on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.  If any of the content units cannot be translated,
        and exception should be raised by the profiler.  The tanslation itself,
        depends on the content unit type and is completely up to the Profiler.
        Translation into an empty list is not considered an error condition and
        will be interpreted by the caller as meaning that no content needs to be
        installed.  See: Unit Translation examples in class documentation.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param units: A list of content units to be installed.
        @type units: list of: { type_id:<str>, unit_key:<dict> }

        @param options: Install options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of: { type_id:<str>, unit_key:<dict> }

        @raise InvalidUnitsRequested: if one or more of the units cannot be installed
        """
        return units

    def update_units(self, consumer, units, options, config, conduit):
        """
        Translate the specified content units to be updated.
        The specified content units are intented to be updated on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.  If any of the content units cannot be translated,
        and exception should be raised by the profiler.  The tanslation itself,
        depends on the content unit type and is completely up to the Profiler.
        Translation into an empty list is not considered an error condition and
        will be interpreted by the caller as meaning that no content needs to be
        updated.

        @see: Unit Translation examples in class documentation.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param units: A list of content units to be updated.
        @type units: list of: { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict

        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of: { type_id:<str>, unit_key:<dict> }

        @raise InvalidUnitsRequested: if one or more of the units cannot be updated
        """
        return units

    def uninstall_units(self, consumer, units, options, config, conduit):
        """
        Translate the specified content units to be uninstalled.
        The specified content units are intented to be uninstalled on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.  If any of the content units cannot be translated,
        and exception should be raised by the profiler.  The tanslation itself,
        depends on the content unit type and is completely up to the Profiler.
        Translation into an empty list is not considered an error condition and
        will be interpreted by the caller as meaning that no content needs to be
        uninstalled.

        @see: Unit Translation examples in class documentation.

        @param consumer: A consumer.
        @type consumer: L{pulp.server.plugins.model.Consumer}

        @param units: A list of content units to be uninstalled.
        @type units: list of: { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of: { type_id:<str>, unit_key:<dict> }

        @raise InvalidUnitsRequested: if one or more of the units cannot be uninstalled
        """
        return units

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
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: An applicability report.
        @rtype: L{pulp.plugins.model.ApplicabilityReport}
        """
        raise Exception, \
            'Applicability for: %s, not supported' % unit
