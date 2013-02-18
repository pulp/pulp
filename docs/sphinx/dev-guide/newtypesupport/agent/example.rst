:orphan:

Handler Example
===============

Handler
-------

Descriptor
^^^^^^^^^^
::

 [main]
 enabled=1

 [types]
 content=rpm,puppet,tar
 bind=yum
 system=Linux

 [rpm]
 class=pulp_rpm.agent.handler.PackageHandler
 import_key=1
 permit_reboot=1

 [puppet]
 class=pulp_puppet.agent.handler.PuppetHandler

 [tar]
 class=pulp_tar.agent.handler.TarHandler
 preserve_permissions=1

 [yum]
 class=pulp_rpm.agent.handler.YumBindHandler
 ssl_verify=0

 [Linux]
 class=pulp.agent.handler.LinuxHandler
 reboot_delay=10

Implementation
^^^^^^^^^^^^^^

::

 from pulp.agent.lib.handler import ContentHandler
 from pulp.agent.lib.report import ProfileReport, ContentReport

 class PackageHandler(ContentHandler):
    """
    An RPM content handler.
    """

    def install(self, conduit, units, options):
        """
        Install RPM content units.  Each unit specifies an RPM that is to be installed.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit keys.
        :type units: list
        :param options: Unit install options.
        :type options: dict
        :return: An installation report.
        :rtype: ContentReport
        """
        report = ContentReport()

        #
        # RPMs installed here
        #

        report.set_succeeded(details)
        return report

    def update(self, conduit, units, options):
        """
        Update RPM content units.  Each unit specifies an RPM that is to be updated.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: PackageReport
        """
        report = ContentReport()

        #
        # RPMs updated here
        #

        report.set_succeeded(details)
        return report

    def uninstall(self, conduit, units, options):
        """
        Uninstall RPM content units.  Each unit specifies an RPM that is to be uninstalled.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit uninstall options.
        :type options: dict
        :return: An uninstall report.
        :rtype: ContentReport
        """
        report = ContentReport()

        #
        # RPMs uninstalled here
        #

        report.set_succeeded(details)
        return report

    def profile(self, conduit):
        """
        Get package profile.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :return: An profile report.
        :rtype: ProfileReport
        """
        report = ProfileReport()

        #
        # Assemble the report here
        #

        report.set_succeeded(details)
        return report

Installation
------------
