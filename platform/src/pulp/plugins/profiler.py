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


class Profiler(object):
    """
    Base class for Pulp consumer profilers. Profilers must subclass this class
    in order for Pulp to identify them during plugin discovery.  The primary
    role of a Profiler is to perform translation between Pulp's generic content
    model and consumer specific content.

    Profile Translation:
        TBD

    Unit Translation:

        An I{expansion} example.  In this case, each unit passed in has a
        aggregate of units.  The translation would be to translate (expand) each
        aggregation unit into the aggregated units:

          Each Unit In:

            {type_id:"PETS", unit_key:{"name":"mypets"}}

          Translated To:

            {type_id:"DOG", unit_key:{"name":"Rover"}}
            {type_id:"DOG", unit_key:{"name":"Cujo"}}
            {type_id:"CAT", unit_key:{"name":"Garfield"}}

        A I{meta type} example.  In this case, each unit passed in needs to be
        translated into a type_id & unit_key that is appropriate for the
        specified consumer:

          For a Linux consumer:

            Each Unit In:

              {type_id:"APP", unit_key:{"name":"myapp"}}

            Translated To:

              {type_id:"TAR", unit_key:{"name":"myapp.tar"}}

          For a Windows consumer:

            Each Unit In:

              {type_id:"APP", unit_key:{"name":"myapp"}}

            Translated To:

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
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Install options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of:
            { type_id:<str>, unit_key:<dict> }
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
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict

        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of:
            { type_id:<str>, unit_key:<dict> }
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
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.conduits.profiler.ProfilerConduit}

        @return: The translated units
        @rtype: list of:
            { type_id:<str>, unit_key:<dict> }
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
