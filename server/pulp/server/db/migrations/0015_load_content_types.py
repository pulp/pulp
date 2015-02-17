"""
This migration loads the content types into the database. Part of the process includes dropping
of search indexes and their recreation.
"""
import logging

from pulp.plugins.loader.api import load_content_types

_logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Perform the migration as described in this module's docblock.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """

    load_content_types(drop_indices=True)
