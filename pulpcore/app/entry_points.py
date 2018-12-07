"""This module provides system wide command to interface with pulpcore."""
import os
import sys


def pulp_manager_entry_point():
    os.environ["DJANGO_SETTINGS_MODULE"] = "pulpcore.app.settings"
    # https://github.com/rochacbruno/dynaconf/issues/89
    from dynaconf.contrib import django_dynaconf  # noqa
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
