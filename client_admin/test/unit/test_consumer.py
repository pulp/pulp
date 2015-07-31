import base_builtins
from pulp.client.commands.consumer.manage import ConsumerUnregisterCommand, ConsumerUpdateCommand
from pulp.client.commands.consumer.query import ConsumerListCommand,\
    ConsumerSearchCommand, ConsumerHistoryCommand
from pulp.client.admin import consumer


class TestStructure(base_builtins.PulpClientTests):

    def setUp(self):
        super(TestStructure, self).setUp()
        consumer.initialize(self.context)
        self.consumer_section = self.context.cli.find_section(consumer.SECTION_ROOT)

    def test_structure(self):
        self.assertTrue(self.consumer_section is not None)
        self.assertTrue(ConsumerListCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerSearchCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerHistoryCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerUpdateCommand(self.context).name in self.consumer_section.commands)
        self.assertTrue(ConsumerUnregisterCommand(self.context).name in
                        self.consumer_section.commands)
