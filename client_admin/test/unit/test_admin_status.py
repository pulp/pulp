from mock import Mock

from pulp.client.admin import admin_status
from pulp.devel.unit import base


class TestStatusCommand(base.PulpClientTests):

    def test_initialize(self):
        # test
        admin_status.initialize(self.context)

        # validation
        self.assertEqual(len(self.context.cli.root_section.commands), 1)
        self.assertTrue(isinstance(self.context.cli.root_section.commands['status'],
                        admin_status.StatusCommand))

    def test_status(self):
        # setup
        context = Mock()
        response = Mock(response_code=200, response_body=[1, 2, 3])
        context.server.server_status.get_status.return_value = response

        # test
        command = admin_status.StatusCommand(context)
        command.status()

        # validation
        context.prompt.render_title.assert_called_once_with(admin_status.StatusCommand.TITLE)
        context.server.server_status.get_status.assert_called_once_with()
        context.prompt.render_document.assert_called_once_with(response.response_body,
                                                               omit_hidden=False)
