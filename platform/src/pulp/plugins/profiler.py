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
    in order for Pulp to identify them during plugin discovery.
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

    def update_profile(self, consumer_id, profile, config, conduit):
        """
        Notification that the consumer has reported the installed unit
        profile.  The profiler has this opportunity to translate the
        reported profile.

        @param consumer_id: The ID of the consumer reporting the profile.
        @type consumer_id: str

        @param profile: The reported profile.
        @type profile: dict

        @param config: plugin configuration
        @type config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.consuits.profile.ProfilerConduit}

        @return: The translated profile.
        @rtype: dict
        """
        return profile

    def install_units(self, consumer_id, units, options, config, conduit):
        """
        Translate the specified content units to be installed.
        The specified content units are intented to be installed on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.

        @param consumer_id: The ID of the consumer.
        @type consumer_id: str

        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Install options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.consuits.profile.ProfilerConduit}

        @return: The translated profile.
        @rtype: dict

        @return: The translated units
        @rtype: list
        """
        return units

    def update_units(self, consumer_id, units, options, config, conduit):
        """
        Translate the specified content units to be updated.
        The specified content units are intented to be updated on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.

        @param consumer_id: The ID of the consumer.
        @type consumer_id: str

        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict

        @param config: plugin configuration
        @type config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.consuits.profile.ProfilerConduit}

        @return: The translated profile.
        @rtype: dict

        @return: The translated units
        @rtype: list
        """
        return units

    def uninstall_units(self, consumer_id, units, options, config, conduit):
        """
        Translate the specified content units to be uninstalled.
        The specified content units are intented to be uninstalled on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.

        @param consumer_id: The ID of the consumer.
        @type consumer_id: str

        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }

        @param options: Update options; based on unit type.
        @type options: dict
        
        @param config: plugin configuration
        @type config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.plugins.consuits.profile.ProfilerConduit}

        @return: The translated profile.
        @rtype: dict

        @return: The translated units
        @rtype: list
        """
        return units
