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
 content=rpm
 bind=yum
 system=Linux

 [rpm]
 class=pulp_rpm.agent.handler.PackageHandler

 [yum]
 class=pulp_rpm.agent.handler.YumBindHandler

 [Linux]
 class=pulp.agent.handler.LinuxHandler

Content Handler
^^^^^^^^^^^^^^^

.. code-block:: python

 from pulp.agent.lib.handler import ContentHandler
 from pulp.agent.lib.report import ProfileReport, ContentReport


 class PackageHandler(ContentHandler):
    """
    An RPM content handler.
    Install, update, and uninstall RPMs.
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
        # succeeded = <did it succeed>
        # details = <whatever you want here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

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
        # succeeded = <did it succeed>
        # details = <whatever you want here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

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
        # succeeded = <did it succeed>
        # details = <whatever you want here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

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
        # succeeded = <did it succeed>
        # details = <the package profile here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

        return report


Bind Handler
^^^^^^^^^^^^

.. code-block:: python

 from pulp.agent.lib.handler import BindHandler
 from pulp.agent.lib.report import BindReport


 class YumBindHandler(BindHandler):
    """
    A yum repository bind request handler.
    Manages the /etc/yum.repos.d/abc.repo based on bind requests.
    """

    def bind(self, conduit, binding, options):
        """
        Bind a repository.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param binding: A binding to add/update.
          A binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
        :type binding: dict
        :param options: Bind options.
        :type options: dict
        :return: A bind report.
        :rtype: BindReport
        """
        repo_id = binding['repo_id']
        report = BindReport(repo_id)

        #
        # Update a YUM .repo file here
        #
        # succeeded = <did it succeed>
        # details = <the package profile here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

        return report

    def unbind(self, conduit, repo_id, options):
        """
        Bind a repository.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param repo_id: A repository ID.
        :type repo_id: str
        :param options: Unbind options.
        :type options: dict
        :return: An unbind report.
        :rtype: BindReport
        """
        report = BindReport(repo_id)

        #
        # Update a YUM .repo file here
        #
        # succeeded = <did it succeed>
        # details = <the package profile here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

        return report

System Handler
^^^^^^^^^^^^^^^

.. code-block:: python

 from pulp.agent.lib.handler import SystemHandler
 from pulp.agent.lib.report import RebootReport


 class LinuxHandler(SystemHandler):
    """
    Linux system handler
    """

    def reboot(self, conduit, options):
        """
        Schedule a system reboot.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param options: reboot options
        :type options: dict
        """
        report = RebootReport()

        #
        # Schedule the reboot here
        #
        # succeeded = <did it succeed>
        # details = <the package profile here>
        #

        if succeeded:
            report.set_succeeded(details)
        else:
            report.set_failed(details)

        return report

Installation
------------
