# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
from gettext import gettext as _

from pulp.client import constants
from pulp.client.connection import setup_connection, ConsumerGroupConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.repolib import RepoLib

# consumer group base action --------------------------------------------------

class ConsumerGroupAction(Action):

    def __init__(self):
        super(ConsumerGroupAction, self).__init__()
        self.repolib = RepoLib()

    def setup_connections(self):
        self.cgconn = setup_connection(ConsumerGroupConnection)

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help="consumer group id")

# consumer group actions ------------------------------------------------------

class List(ConsumerGroupAction):

    description = 'list available consumer groups'

    def setup_parser(self):
        pass

    def run(self):
        groups = self.cgconn.consumergroups()
        if not len(groups):
            print _("no consumer groups available to list")
            system_exit(os.EX_OK)
        print_header("List of Available Consumer Groups")
        for group in groups:
            print constants.AVAILABLE_CONSUMER_GROUP_INFO % \
                    (group["id"], group["description"], group["consumerids"],
                     group["key_value_pairs"])


class Create(ConsumerGroupAction):

    description = 'create a consumer group'

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--description", dest="description",
                       help="description of consumer group")

    def run(self):
        id = self.get_required_option('id')
        description = getattr(self.opts, 'description', '')
        consumergroup = self.cgconn.create(id, description)
        print _(" successfully created Consumer group [ %s ] with description [ %s ]") % \
                (consumergroup['id'], consumergroup["description"])


class Delete(ConsumerGroupAction):

    description = 'delete the consumer group'

    def setup_parser(self):
        super(Delete, self).setup_parser()

    def run(self):
        id = self.get_required_option('id')
        group = self.cgconn.consumergroup(id=id)
        if not group:
            print _(" consumer group [ %s ] does not exist") % id
            system_exit(os.EX_DATAERR)
        self.cgconn.delete(id=id)
        print _(" successfully deleted consumer group [ %s ]") % id


class AddConsumer(ConsumerGroupAction):

    description = 'add a consumer to the group'

    def setup_parser(self):
        super(AddConsumer, self).setup_parser()
        self.parser.add_option("--consumerid", dest="consumerid",
                       help="consumer identifier")

    def run(self):
        consumerid = self.get_required_option('consumerid')
        groupid = self.get_required_option('id')
        self.cgconn.add_consumer(groupid, consumerid)
        print _(" Successfully added Consumer [%s] to Group [%s]") % \
                (consumerid, groupid)


class DeleteConsumer(ConsumerGroupAction):

    description = 'delete a consumer from the group'

    def setup_parser(self):
        super(DeleteConsumer, self).setup_parser()
        self.parser.add_option("--consumerid", dest="consumerid",
                               help="consumer identifier")

    def run(self):
        groupid = self.get_required_option('id')
        consumerid = self.get_required_option('consumerid')
        self.cgconn.delete_consumer(groupid, consumerid)
        print _(" successfully deleted consumer [%s] from group [%s]") % \
                (consumerid, groupid)


class Bind(ConsumerGroupAction):

    description = 'bind the consumer group to listed repos'

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository identifier")

    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cgconn.bind(groupid, self.options.repoid)
        self.repolib.update()
        print _(" successfully subscribed consumer group [%s] to repo [%s]") % \
                (groupid, repoid)


class Unbind(ConsumerGroupAction):

    description = 'unbind the consumer group from repos'

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository identifier")

    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cgconn.unbind(groupid, self.options.repoid)
        self.repolib.update()
        print _(" successfully unsubscribed consumer group [%s] from repo [%s]") % \
                (groupid, repoid)


class AddKeyValue(ConsumerGroupAction):

    description = 'add key-value information to consumergroup'

    def setup_parser(self):
        super(AddKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key", help="key identifier")
        self.parser.add_option("--value", dest="value",
                               help="value corresponding to the key")
        self.parser.add_option("--force", action="store_false", dest="force", default=True,
                               help="Force changes to consumer keys if required")

    def run(self):
        groupid = self.get_required_option('id')
        key = self.get_required_option('key')
        value = self.get_required_option('value')
        force = getattr(self.opts, 'force', True)
        if force:
            force_value = 'false'
        else:
            force_value = 'true'
        self.cgconn.add_key_value_pair(groupid, key, value, force_value)
        print _(" successfully added key-value pair %s:%s") % (key, value)


class DeleteKeyValue(ConsumerGroupAction):

    description = 'delete key-value information to consumergroup'

    def setup_parser(self):
        super(DeleteKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key", help="key identifier")

    def run(self):
        groupid = self.get_required_option('id')
        key = self.get_required_option('key')
        self.cgconn.delete_key_value_pair(groupid, key)
        print _(" successfully deleted key: %s") % key


class UpdateKeyValue(ConsumerGroupAction):

    description = ''

    def setup_parser(self):
        super(AddKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key", help="key identifier")
        self.parser.add_option("--value", dest="value",
                               help="value corresponding to the key")

    def run(self):
        groupid = self.get_required_option('id')
        key = self.get_required_option('key')
        value = self.get_required_option('value')
        self.cgconn.update_key_value_pair(groupid, key, value)
        print _(" successfully updated key-value pair %s:%s") % (key, value)

# consumer group command ------------------------------------------------------

class ConsumerGroup(Command):

    description = _('consumer group specific actions to pulp server')
