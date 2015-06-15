# -*- coding: utf-8 -*-
"""
This module contains imports that are needed for the Celery workers to find tasks that are outside
of this Python package.
"""
import pulp.server.db.reaper  # noqa
import pulp.server.maintenance.monthly  # noqa
import pulp.server.repository.content  # noqa
