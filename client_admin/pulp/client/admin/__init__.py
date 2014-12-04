import sys

from pulp.client import launcher
from pulp.client.admin.exception_handler import AdminExceptionHandler
from pulp.client.admin.config import read_config


def main():
    exit_code = launcher.main(read_config(), exception_handler_class=AdminExceptionHandler)
    sys.exit(exit_code)
