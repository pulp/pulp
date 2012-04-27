#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import os
import urlparse
from gettext import gettext as _

from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.consumer.config import ConsumerConfig
from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from pulp.client.consumer.plugin import ConsumerPlugin
from pulp.client import constants
from pulp.client.lib import repolib
from pulp.client.lib import utils
from pulp.client.lib.repo_file import RepoFile
from pulp.client.lib.utils import print_header
from pulp.client.lib.utils import system_exit
from pulp.client.plugins.consumer import (ConsumerAction, Consumer,
    Bind, Unbind, Unregister, History)
from pulp.common import dateutils
from pulp.common.capabilities import AgentCapabilities
from pulp.common.util import encode_unicode
from rhsm.profile import get_profile

# base consumer action --------------------------------------------------------

class ConsumerClientActionMixIn(object):

    @property
    def consumerid(self):
        """
        Get the consumer ID from the identity certificate.
        @return: The consumer id.  Returns (None) when not registered.
        @rtype: str
        """
        bundle = ConsumerBundle()
        return bundle.getid()

    def check_write_perms(self, path):
        """
        Check that write permissions are present for the given path.  If parts
        of the path do not yet exist, check if it can be created.
        """
        if os.path.exists(path):
            if not os.access(path, os.W_OK):
                system_exit(os.EX_NOPERM, _("Write permission is required for %s to perform this operation." %
                    path))
            else:
                return True
        else:
            self.check_write_perms(os.path.split(path)[0])

    def check_bind_path(self):
        return self.check_write_perms(self.cfg.client.repo_file)

    def check_bundle_path(self):
        bundle = ConsumerBundle()
        return self.check_write_perms(bundle.crtpath())


# consumer actions ------------------------------------------------------------

class Register(ConsumerAction, ConsumerClientActionMixIn):

    name = "register"
    description = _('register the consumer')

    def setup_parser(self):
        # always provide --id option for register, even on registered clients
        self.parser.add_option('--id', dest='id',
                               help=_("consumer identifier eg: foo.example.com (required)"))
        self.parser.add_option("--description", dest="description",
                               help=_("consumer description eg: foo's web server"))

    def run(self):
        id = self.get_required_option('id')
        description = getattr(self.opts, 'description', id)
        if self.consumerid:
            system_exit(os.EX_DATAERR, _("A consumer [%s] already registered on this system; Please unregister existing consumer before registering." % self.consumerid))
        self.check_bundle_path()
        bundle = ConsumerBundle()
        capabilities = AgentCapabilities.default()
        consumer = self.consumer_api.create(id, description, capabilities=dict(capabilities))
        bundle.write(consumer['certificate'])
        pkginfo = get_profile("rpm").collect()
        self.consumer_api.package_profile(id, pkginfo)
        print _("Successfully registered consumer [ %s ]") % consumer['id']


class Update(ConsumerAction, ConsumerClientActionMixIn):

    name = "update"
    description = _('update consumer profile')

    def run(self):
        consumer_id = self.consumerid
        if not consumer_id:
            system_exit(os.EX_NOHOST, _("This client is not registered; cannot perform an update"))
        pkginfo = get_profile("rpm").collect()
        try:
            self.consumer_api.package_profile(consumer_id, pkginfo)
            print _("Successfully updated consumer [%s] profile") % consumer_id
        except:
            system_exit(os.EX_DATAERR, _("Error updating consumer [%s]." % consumer_id))


# consumer overridden actions ------------------------------------------------------------

class ClientUnbind(Unbind, ConsumerClientActionMixIn):

    def run(self):
        consumerid = self.consumerid
        repoid = self.get_required_option('repoid')
        self.check_bind_path()
        Unbind.run(self, consumerid, repoid)
        self.unbind_repo(repoid)
        print _("Successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, repoid)

    def unbind_repo(self, repoid):
        repoid = encode_unicode(repoid)
        mirror_list_filename = \
            repolib.mirror_list_filename(self.cfg.client.mirror_list_dir, repoid)
        repolib.unbind(
            self.cfg.client.repo_file,
            mirror_list_filename,
            self.cfg.client.gpg_keys_dir,
            self.cfg.client.cert_dir,
            repoid)


class ClientHistory(History, ConsumerClientActionMixIn):

    def run(self):
        consumerid = self.consumerid
        History.run(self, consumerid)


class ClientUnregister(Unregister, ConsumerClientActionMixIn):

    def run(self):
        consumerid = self.consumerid
        self.check_bundle_path()
        Unregister.run(self, consumerid)
        bundle = ConsumerBundle()
        self.delete_files(bundle)
        print _("Successfully unregistered consumer [%s]") % consumerid

    def delete_files(self, bundle):
        repo_file = RepoFile(self.cfg.client.repo_file)
        repo_file.delete()
        bundle.delete()


class ClientBind(Bind, ConsumerClientActionMixIn):

    def run(self):
        consumerid = self.consumerid
        repoid = self.get_required_option('repoid')
        self.check_bind_path()
        bind_data = Bind.run(self, consumerid, repoid)
        if bind_data:
            self.bind_repo(repoid, bind_data)
            print _("Successfully subscribed consumer [%s] to repo [%s]") % \
                  (consumerid, repoid)
        else:
            print _('Repo [%s] already bound to the consumer' % repoid)

    def bind_repo(self, repoid, bind_data):
        mirror_list_filename = \
            repolib.mirror_list_filename(self.cfg.client.mirror_list_dir, repoid)
        for unicode_key in ('id', '_id', 'name'):
            bind_data['repo'][unicode_key] = encode_unicode(bind_data['repo'][unicode_key])
        repolib.bind(
            self.cfg.client.repo_file,
            mirror_list_filename,
            self.cfg.client.gpg_keys_dir,
            self.cfg.client.cert_dir,
            repoid,
            bind_data['repo'],
            bind_data['host_urls'],
            bind_data['gpg_keys'],
            bind_data['cacert'],
            bind_data['clientcert'])

# consumer command ------------------------------------------------------------

class ConsumerClient(Consumer):

    actions = [ Register,
                ClientUnregister,
                ClientBind,
                ClientUnbind,
                ClientHistory,
                Update ]

# consumer plugin ------------------------------------------------------------

class ConsumerClientPlugin(ConsumerPlugin):

    name = "consumer"
    commands = [ ConsumerClient ]
