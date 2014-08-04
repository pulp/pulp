
from unittest import TestCase

from mock import patch

from pulp.client.consumer import main
from pulp.client.consumer.exception_handler import ConsumerExceptionHandler


class TestMain(TestCase):

    @patch('sys.exit')
    @patch('pulp.client.consumer.launcher')
    @patch('pulp.client.consumer.read_config')
    def test_main(self, fake_read, fake_launcher, fake_exit):
        exit_code = 100
        fake_launcher.main.return_value = exit_code

        # test
        main()

        # validation
        fake_read.assert_called_with()
        fake_launcher.main.assert_called_with(
            fake_read(), exception_handler_class=ConsumerExceptionHandler)
        fake_exit.assert_called_with(exit_code)
