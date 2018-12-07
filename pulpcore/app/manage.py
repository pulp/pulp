#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulpcore.app.settings")

    # https://github.com/rochacbruno/dynaconf/issues/89
    from dynaconf.contrib import django_dynaconf  # noqa

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
