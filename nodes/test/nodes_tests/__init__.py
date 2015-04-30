from pulp.devel.unit.server import base as devel_base


def setup():
    """
    Set up the database connection for the tests to use.
    """
    devel_base.start_database_connection()


def teardown():
    """
    Drop the test database.
    """
    devel_base.drop_database()
